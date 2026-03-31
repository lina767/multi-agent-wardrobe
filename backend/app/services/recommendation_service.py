"""End-to-end recommendation pipeline."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.agents.color_agent import ColorAgent
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

    tags: list[str] = []
    history: list[dict[str, Any]] = []
    for r in rows:
        try:
            ids = json.loads(r.item_ids_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(ids, list):
            continue
        row_tags: list[str] = []
        sorted_ids = tuple(sorted(int(i) for i in ids))
        for wid in sorted_ids:
            item = db.query(WardrobeItem).filter(WardrobeItem.id == int(wid)).first()
            if item:
                item_tags = list(item.style_tags_json or [])
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
        ]
    ] = []

    for cand in candidates:
        results = [
            color.evaluate(cand, pipeline_base),
            style.evaluate(cand, pipeline_base),
            wardrobe.evaluate(cand, pipeline_base),
            context_ag.evaluate(cand, pipeline_base),
        ]
        total_pre, partials, reasons, trace, _conf = orch.merge(results, body.context.event_type)

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
        trace.append({"type": "orchestrator", "partials_pre_evidence": partials, "total_pre_evidence": total_pre})
        for a in adjustments:
            trace.append(
                {
                    "type": "evidence",
                    "evidence_id": a.evidence_id,
                    "effect_on_score": a.delta,
                    "rationale": a.rationale,
                }
            )

        scored.append((final_score, cand, agent_contribs, trace, ev_tags, reasons))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:3]

    suggestions: list[OutfitSuggestion] = []
    for rank, row in enumerate(top, start=1):
        score, cand, contribs, trace, ev_tags, reasons = row
        id_to_item = {it.id: it for it in cand.items}
        ordered_ids = sorted(cand.item_ids)
        names = [id_to_item[i].name for i in ordered_ids if i in id_to_item]
        suggestions.append(
            OutfitSuggestion(
                rank=rank,
                item_ids=ordered_ids,
                item_names=names,
                total_score=round(score, 4),
                agent_contributions=contribs,
                evidence_tags=ev_tags,
                explanation=explanation_for_rank(rank, score, ev_tags, reasons),
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
) -> str:
    ev_bits = ", ".join(f"{e.evidence_id} ({e.effect_on_total:+.3f})" for e in ev[:4])
    rbits = "; ".join(reasons[:3]) if reasons else ""
    return f"#{rank} — total {score:.3f}. {rbits}. Evidence: {ev_bits}."
