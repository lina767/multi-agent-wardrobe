import json

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.schemas import FeedbackCreate, FeedbackRead
from app.db.models import FeedbackEvent
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.services.temporal_intelligence import record_style_signal

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def create_feedback(
    body: FeedbackCreate,
    db: Session = Depends(get_db),
    uid: int = Depends(get_current_user_id),
) -> FeedbackRead:
    row = FeedbackEvent(
        user_id=uid,
        suggestion_item_ids_json=json.dumps(body.suggestion_item_ids),
        rating=body.rating,
        comment=body.comment,
    )
    db.add(row)
    record_style_signal(
        db,
        user_id=uid,
        signal_type="manual_feedback",
        source="feedback_api",
        weight=min(1.0, max(0.2, body.rating / 5.0)),
        payload={
            "item_ids": body.suggestion_item_ids,
            "rating": body.rating,
            "comment": body.comment,
            "reason_tags": body.reason_tags,
            "occasion": body.occasion,
        },
    )
    db.commit()
    db.refresh(row)
    return FeedbackRead.model_validate(row)


@router.get("", response_model=list[FeedbackRead])
def list_feedback(
    db: Session = Depends(get_db),
    uid: int = Depends(get_current_user_id),
) -> list[FeedbackRead]:
    rows = db.query(FeedbackEvent).filter(FeedbackEvent.user_id == uid).order_by(FeedbackEvent.id.desc()).limit(100).all()
    return [FeedbackRead.model_validate(r) for r in rows]
