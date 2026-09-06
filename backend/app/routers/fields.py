"""
fields.py
==========
CRUD for farm fields. v1 has a single fixed Belagavi field (seeded at
startup), but the API supports multiple fields for the extension officer
multi-farm overview (PRD section 8).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_db import Field
from app.schemas import FieldCreate, FieldOut

router = APIRouter(prefix="/fields", tags=["fields"])


@router.get("", response_model=list[FieldOut])
def list_fields(db: Session = Depends(get_db)):
    return db.query(Field).all()


@router.get("/{field_id}", response_model=FieldOut)
def get_field(field_id: int, db: Session = Depends(get_db)):
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


@router.post("", response_model=FieldOut, status_code=201)
def create_field(field_in: FieldCreate, db: Session = Depends(get_db)):
    field = Field(**field_in.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.delete("/{field_id}", status_code=204)
def delete_field(field_id: int, db: Session = Depends(get_db)):
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    db.delete(field)
    db.commit()
    return None
