import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import ContextInput, QuickRecommendationRequest, QuickRecommendationResponse, RecommendationRequest, RecommendationResponse
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.domain.enums import EventType
from app.logging_config import log_metric
from app.services.recommendation_service import build_recommendations
from app.services.weather import WeatherService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)


@router.post("", response_model=RecommendationResponse)
def post_recommendations(
    body: RecommendationRequest,
    db: Session = Depends(get_db),
    uid: int = Depends(get_current_user_id),
) -> RecommendationResponse:
    t0 = time.perf_counter()
    out = build_recommendations(db, uid, body)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    log_metric(
        logger,
        "recommendation_latency_ms",
        round(elapsed_ms, 2),
        suggestions=len(out.suggestions),
        candidates_requested=body.max_candidates_to_rank,
    )
    return out


@router.post("/quick", response_model=QuickRecommendationResponse)
async def post_quick_recommendations(
    body: QuickRecommendationRequest,
    db: Session = Depends(get_db),
    uid: int = Depends(get_current_user_id),
) -> QuickRecommendationResponse:
    weather = await WeatherService().fetch_current(body.location) if body.location else {}
    event_type = EventType.ERRAND if body.occasion.lower() in {"casual", "sport"} else EventType.MEETING
    req = RecommendationRequest(
        context=ContextInput(
            condition=weather.get("condition"),
            condition_raw=weather.get("condition_raw"),
            temperature_c=weather.get("temperature_c"),
            feels_like_c=weather.get("feels_like_c"),
            rain_probability=weather.get("rain_probability"),
            uv_index=weather.get("uv_index"),
            wind_speed_kph=weather.get("wind_speed_kph"),
            forecast_summary=weather.get("forecast_summary"),
            event_type=event_type,
            mood=body.mood,
            notes=f"quick occasion={body.occasion}",
        ),
        max_candidates_to_rank=70,
    )
    out = build_recommendations(db, uid, req)
    return QuickRecommendationResponse(
        context={"occasion": body.occasion, "weather": weather, "mood": body.mood.value},
        suggestions=[
            {
                "item_ids": suggestion.item_ids,
                "item_names": suggestion.item_names,
                "total_score": suggestion.total_score,
                "explanation": suggestion.explanation,
            }
            for suggestion in out.suggestions[: body.limit]
        ],
        scientific_note="Quick mode optimizes for low-latency top picks with minimal input.",
    )
