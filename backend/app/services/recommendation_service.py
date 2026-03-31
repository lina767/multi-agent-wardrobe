"""End-to-end recommendation pipeline."""

import asyncio
import json
import threading
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.agents.color_agent import ColorAgent
from app.agents.contracts import normalize_result_contract
from app.agents.context_agent import ContextAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.style_agent import StyleAgent
from app.agents.wardrobe_agent import WardrobeAgent
from app.api.schemas import (
    AgentContribution,
    EvidenceContribution,
    OutfitSuggestion,
    RecommendationRequest,
    RecommendationResponse,
    UserStylePreferences,
)
from app.domain.entities import OutfitCandidateDTO, RecommendationPipelineInput, WardrobeItemDTO
from app.domain.enums import ColorFamily, DresscodeLevel, WardrobeCategory
from app.evidence.rules import EvidenceRuleEngine
from app.db.models import FeedbackEvent, OutfitLog, WardrobeItem
from app.services.temporal_intelligence import get_current_temporal_state


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {"value": None, "error": None}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except Exception as exc:  # pragma: no cover
            result["error"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if result["error"]:
        raise result["error"]
    return result["value"]


def _item_to_dto(row: WardrobeItem) -> WardrobeItemDTO:
    return WardrobeItemDTO(
        id=row.id,
        name=row.name,
        category=WardrobeCategory(row.category),
        color_families=[ColorFamily(c) for c in (row.color_families_json or [])],
        formality=DresscodeLevel(row.formality) if row.formality else DresscodeLevel.CASUAL,
        season_tags=list(row.season_tags_json or []),
        is_available=row.is_available,
        style_tags=list(row.style_tags_json or []),
        brand=row.brand,
        size_label=row.size_label,
        material=row.material,
        quantity=row.quantity,
        purchase_price=row.purchase_price,
        notes=row.notes,
    )


def _history_snapshot(db: Session, user_id: int, limit: int = 30) -> tuple[list[str], list[dict[str, Any]]]:
    rows = (
        db.query(OutfitLog)
        .filter(OutfitLog.user_id == user_id)
        .order_by(OutfitLog.worn_at.desc())
        .limit(limit)
        .all()
    )
    feedback_rows = (
        db.query(FeedbackEvent)
        .filter(FeedbackEvent.user_id == user_id)
        .order_by(FeedbackEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    rating_by_combo: dict[tuple[int, ...], int] = {}
    for f in feedback_rows:
        try:
            ids = json.loads(f.suggestion_item_ids_json)
        except json.JSONDecodeError:
            continue
        if isinstance(ids, list):
            key = tuple(sorted(int(i) for i in ids))
            rating_by_combo[key] = int(f.rating)

    parsed_rows: list[tuple[tuple[int, ...], OutfitLog]] = []
    wanted_item_ids: set[int] = set()
    for r in rows:
        try:
            ids = json.loads(r.item_ids_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(ids, list):
            continue
        sorted_ids = tuple(sorted(int(i) for i in ids))
        parsed_rows.append((sorted_ids, r))
        wanted_item_ids.update(sorted_ids)

    item_rows = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.id.in_(wanted_item_ids))
        .all()
        if wanted_item_ids
        else []
    )
    style_tags_by_item_id = {row.id: list(row.style_tags_json or []) for row in item_rows}

    tags: list[str] = []
    history: list[dict[str, Any]] = []
    for sorted_ids, _row in parsed_rows:
        row_tags: list[str] = []
        for wid in sorted_ids:
            item_tags = style_tags_by_item_id.get(wid, [])
            tags.extend(item_tags)
            row_tags.extend(item_tags)
        history.append({"item_ids": list(sorted_ids), "style_tags": row_tags, "rating": rating_by_combo.get(sorted_ids)})
    return tags, history


def build_recommendations(
    db: Session,
    user_id: int,
    body: RecommendationRequest,
) -> RecommendationResponse:
    rows = db.query(WardrobeItem).filter(WardrobeItem.user_id == user_id).all()
    items = [_item_to_dto(r) for r in rows]

    style_prefs = body.style_preferences or UserStylePreferences()
    hist_tags, outfit_history = _history_snapshot(db, user_id)

    pipeline_base = RecommendationPipelineInput(
        context=body.context,
        style_preferences=style_prefs,
        palette_bias=body.palette_bias,
        items=items,
        outfit_history_tags=hist_tags,
        outfit_history=outfit_history,
    )
    temporal_state = get_current_temporal_state(db, user_id=user_id)
    temporal_weights = temporal_state.get("dynamic_weights", {}) if isinstance(temporal_state, dict) else {}
    temporal_factors = temporal_state.get("state_factors", []) if isinstance(temporal_state, dict) else []

    wardrobe = WardrobeAgent()
    color = ColorAgent()
    style = StyleAgent()
    context_ag = ContextAgent()
    orch = OrchestratorAgent()
    evidence_engine = EvidenceRuleEngine()

    candidates = wardrobe.build_candidates(items, max_candidates=body.max_candidates_to_rank)
    if not candidates:
        return RecommendationResponse(
            suggestions=[],
            generated_at=datetime.now(UTC),
            context_echo=body.context,
        )

    scored: list[
        tuple[
            float,
            OutfitCandidateDTO,
            list[AgentContribution],
            list[dict[str, Any]],
            list[EvidenceContribution],
            list[str],
            str,
        ]
    ] = []
    supervisor_candidates: list[dict[str, Any]] = []
    fusion_monitor: list[dict[str, Any]] = []

    for cand in candidates:
        raw_results = [
            color.evaluate(cand, pipeline_base),
            style.evaluate(cand, pipeline_base),
            wardrobe.evaluate(cand, pipeline_base),
            context_ag.evaluate(cand, pipeline_base),
        ]
        results = [
            normalize_result_contract(
                raw_results[0],
                expected_agent="color",
                contract_payload={"season": "unknown", "undertone": "unknown", "contrast": "unknown", "confidence": 0.5, "palette_hex": []},
            ),
            normalize_result_contract(raw_results[1], expected_agent="style"),
            normalize_result_contract(raw_results[2], expected_agent="wardrobe"),
            normalize_result_contract(raw_results[3], expected_agent="context", contract_payload={"weather_specialist": True}),
        ]
        total_pre, partials, reasons, trace, _conf = orch.merge(
            results,
            body.context.event_type,
            weight_overrides=temporal_weights if isinstance(temporal_weights, dict) else None,
        )
        harmony = partials.get("harmony", 0.5)
        context_fit = partials.get("context_fit", 0.5)
        if abs(harmony - context_fit) >= 0.35:
            fusion_monitor.append(
                {
                    "candidate_key": "-".join(str(i) for i in sorted(cand.item_ids)),
                    "signal": "color_context_divergence",
                    "harmony": round(harmony, 3),
                    "context_fit": round(context_fit, 3),
                }
            )

        final_score, adjustments = evidence_engine.apply(
            total_pre,
            body.context,
            cand.items,
            partials,
        )

        ev_tags = [
            EvidenceContribution(
                evidence_id=a.evidence_id,
                citation_short=a.citation_short,
                effect_on_total=a.delta,
                rationale=a.rationale,
            )
            for a in adjustments
        ]

        agent_contribs = [
            AgentContribution(
                agent=r.agent_name,
                partial_scores=r.partial_scores,
                reasons=r.reasons,
            )
            for r in results
        ]
        trace.append(
            {
                "type": "orchestrator",
                "partials_pre_evidence": partials,
                "total_pre_evidence": total_pre,
                "dynamic_weights": temporal_weights,
                "state_factors": temporal_factors,
            }
        )
        for a in adjustments:
            trace.append(
                {
                    "type": "evidence",
                    "evidence_id": a.evidence_id,
                    "effect_on_score": a.delta,
                    "rationale": a.rationale,
                }
            )

        candidate_key = "-".join(str(i) for i in sorted(cand.item_ids))
        scored.append((final_score, cand, agent_contribs, trace, ev_tags, reasons, candidate_key))
        supervisor_candidates.append(
            {
                "candidate_key": candidate_key,
                "item_ids": sorted(cand.item_ids),
                "partial_scores": partials,
                "agent_reasons": {r.agent_name: r.reasons for r in results},
                "total_pre_evidence": round(total_pre, 4),
                "evidence_adjustments": [
                    {
                        "evidence_id": a.evidence_id,
                        "delta": a.delta,
                        "rationale": a.rationale,
                    }
                    for a in adjustments
                ],
                "fallback_reason": explanation_for_rank(0, final_score, ev_tags, reasons),
            }
        )

    supervisor_context = {
        "event_type": body.context.event_type.value,
        "temperature_c": body.context.temperature_c,
        "feels_like_c": body.context.feels_like_c,
        "rain_probability": body.context.rain_probability,
        "uv_index": body.context.uv_index,
        "wind_speed_kph": body.context.wind_speed_kph,
        "forecast_summary": body.context.forecast_summary,
        "mood": body.context.mood.value,
        "notes": body.context.notes,
    }
    supervisor_out = _run_async(
        orch.supervise(
            event_type=body.context.event_type,
            context=supervisor_context,
            candidates=supervisor_candidates,
        )
    )

    by_key = {row[6]: row for row in scored}
    ranked_keys = [k for k in supervisor_out.get("final_ranking", []) if isinstance(k, str) and k in by_key]
    for key in by_key:
        if key not in ranked_keys:
            ranked_keys.append(key)
    scored = [by_key[k] for k in ranked_keys]
    top = scored[:3]
    synth_text = supervisor_out.get("synthesis_text", {})
    conflict_flags = supervisor_out.get("conflict_flags", {})
    adjusted_weights = supervisor_out.get("adjusted_weights", {})

    suggestions: list[OutfitSuggestion] = []
    for rank, row in enumerate(top, start=1):
        score, cand, contribs, trace, ev_tags, reasons, candidate_key = row
        id_to_item = {it.id: it for it in cand.items}
        ordered_ids = sorted(cand.item_ids)
        names = [id_to_item[i].name for i in ordered_ids if i in id_to_item]
        trace.append(
            {
                "type": "supervisor",
                "candidate_key": candidate_key,
                "adjusted_weights": adjusted_weights,
                "conflict_flags": conflict_flags.get(candidate_key, []),
            }
        )
        for monitor_event in fusion_monitor:
            if monitor_event["candidate_key"] == candidate_key:
                trace.append({"type": "monitoring", **monitor_event})
        suggestions.append(
            OutfitSuggestion(
                rank=rank,
                item_ids=ordered_ids,
                item_names=names,
                total_score=round(score, 4),
                agent_contributions=contribs,
                evidence_tags=ev_tags,
                explanation=explanation_for_rank(
                    rank,
                    score,
                    ev_tags,
                    reasons,
                    synthesis_text=synth_text.get(candidate_key),
                    conflicts=conflict_flags.get(candidate_key, []),
                ),
                decision_trace=trace,
            )
        )

    return RecommendationResponse(
        suggestions=suggestions,
        generated_at=datetime.now(UTC),
        context_echo=body.context,
    )


def explanation_for_rank(
    rank: int,
    score: float,
    ev: list[EvidenceContribution],
    reasons: list[str],
    synthesis_text: str | None = None,
    conflicts: list[str] | None = None,
) -> str:
    if synthesis_text:
        conflict_note = ""
        if conflicts:
            conflict_note = f" Conflicts considered: {', '.join(conflicts[:2])}."
        return f"#{rank} — total {score:.3f}. {synthesis_text}{conflict_note}"
    ev_bits = ", ".join(f"{e.evidence_id} ({e.effect_on_total:+.3f})" for e in ev[:4])
    rbits = "; ".join(reasons[:3]) if reasons else ""
    return f"#{rank} — total {score:.3f}. {rbits}. Evidence: {ev_bits}."
