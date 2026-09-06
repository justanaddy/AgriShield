"""
alerts.py
==========
Alert listing/acknowledgement endpoints (PRD section 8 alert system).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_db import Alert
from app.schemas import AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/{field_id}", response_model=list[AlertOut])
def list_alerts(field_id: int, unacknowledged_only: bool = False, limit: int = 50,
                 db: Session = Depends(get_db)):
    query = db.query(Alert).filter(Alert.field_id == field_id)
    if unacknowledged_only:
        query = query.filter(Alert.acknowledged == 0)
    return (
        query.order_by(Alert.created_at.desc()).limit(limit).all()
    )


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = 1
    db.commit()
    db.refresh(alert)
    return alert
