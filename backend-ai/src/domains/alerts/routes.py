"""Alert rules API routes."""

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import AlertRule

router = APIRouter(prefix="/alerts", tags=["alerts"])


class CreateAlertRequest(BaseModel):
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    condition_type: str = Field(..., description="price_above | price_below | volume_spike | sentiment_change | filing_new")
    condition_config: dict = Field(default_factory=dict)
    is_active: bool = True


@router.get("/")
def list_alerts(user_id: UUID, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """List alert rules for a user."""
    alerts = (
        db.query(AlertRule)
        .filter(AlertRule.user_id == user_id)
        .order_by(AlertRule.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(a.id),
            "user_id": str(a.user_id),
            "name": a.name,
            "condition_type": a.condition_type,
            "condition_config": a.condition_config or {},
            "is_active": a.is_active,
            "last_triggered_at": a.last_triggered_at.isoformat() if a.last_triggered_at else None,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.post("/", status_code=201)
def create_alert(request: CreateAlertRequest, db: Session = Depends(get_db)):
    """Create a new alert rule."""
    alert = AlertRule(
        user_id=request.user_id,
        name=request.name,
        condition_type=request.condition_type,
        condition_config=request.condition_config,
        is_active=request.is_active,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {
        "id": str(alert.id),
        "name": alert.name,
        "condition_type": alert.condition_type,
        "is_active": alert.is_active,
        "created_at": alert.created_at.isoformat(),
    }


@router.delete("/{alert_id}", status_code=204)
def delete_alert(alert_id: UUID, db: Session = Depends(get_db)):
    """Delete an alert rule."""
    alert = db.query(AlertRule).filter(AlertRule.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()
