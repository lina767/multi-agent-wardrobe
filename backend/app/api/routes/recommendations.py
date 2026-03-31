import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import RecommendationRequest, RecommendationResponse
from app.bootstrap import get_default_user_id
from app.db.session import get_db
from app.logging_config import log_metric
from app.services.recommendation_service import build_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)


@router.post("", response_model=RecommendationResponse)
def post_recommendations(
    body: RecommendationRequest,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    uid = get_default_user_id(db)
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
