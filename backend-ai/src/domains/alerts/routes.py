"""Alert rules API routes."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import AlertRule, User
from src.domains.alerts.service import AlertRulesService
from src.domains.auth.dependencies import assert_self, get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])


class CreateAlertRequest(BaseModel):
    user_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    condition_type: str = Field(
        ...,
        description="price_above | price_below | volume_spike | sentiment_change | filing_new | asymmetric_theme",
    )
    condition_config: dict = Field(default_factory=dict)
    is_active: bool = True


@router.get("/")
def list_alerts(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List alert rules for a user."""
    assert_self(user_id, current_user)
    service = AlertRulesService(db)
    return service.list_alerts(user_id)


@router.post("/", status_code=201)
def create_alert(
    request: CreateAlertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new alert rule."""
    assert_self(request.user_id, current_user)
    service = AlertRulesService(db)
    return service.create_alert(
        user_id=request.user_id,
        name=request.name,
        condition_type=request.condition_type,
        condition_config=request.condition_config,
        is_active=request.is_active,
    )


@router.delete("/{alert_id}", status_code=204)
def delete_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == alert_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert not found")
    if rule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your alert")
    service = AlertRulesService(db)
    service.delete_alert(alert_id)
