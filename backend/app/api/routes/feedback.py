import json

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.schemas import FeedbackCreate, FeedbackRead
from app.bootstrap import get_default_user_id
from app.db.models import FeedbackEvent
from app.db.session import get_db

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def create_feedback(body: FeedbackCreate, db: Session = Depends(get_db)) -> FeedbackRead:
    uid = get_default_user_id(db)
    row = FeedbackEvent(
        user_id=uid,
        suggestion_item_ids_json=json.dumps(body.suggestion_item_ids),
        rating=body.rating,
        comment=body.comment,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return FeedbackRead.model_validate(row)


@router.get("", response_model=list[FeedbackRead])
def list_feedback(db: Session = Depends(get_db)) -> list[FeedbackRead]:
    uid = get_default_user_id(db)
    rows = db.query(FeedbackEvent).filter(FeedbackEvent.user_id == uid).order_by(FeedbackEvent.id.desc()).limit(100).all()
    return [FeedbackRead.model_validate(r) for r in rows]
