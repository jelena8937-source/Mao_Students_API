from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import Ritual, RitualStatus
from app.schemas.schemas import RitualResponse, RitualCreate, RitualUpdate, MessageResponse
from datetime import datetime
import random
import string

router = APIRouter(prefix="/rituals", tags=["🙏 法會"])


def generate_ritual_id(db: Session) -> str:
    """自動產生 RTL-YYYY-XXXXXX 格式的唯一法會編號"""
    year = datetime.now().year
    while True:
        suffix = ''.join(random.choices(string.digits, k=6))
        candidate = f"RTL-{year}-{suffix}"
        exists = db.query(Ritual).filter(Ritual.ritual_id == candidate).first()
        if not exists:
            return candidate


# ========== 公開端點 ==========

@router.get("", response_model=List[RitualResponse])
def list_rituals(db: Session = Depends(get_db)):
    """取得所有法會時程（公開，供 Rituals.vue 顯示）"""
    return db.query(Ritual).order_by(Ritual.ritual_date.asc()).all()


# ========== 管理員端點 ==========

@router.post("", response_model=RitualResponse, status_code=201)
def create_ritual(
    data: RitualCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """【管理員】新增法會"""
    ritual = Ritual(
        ritual_id=generate_ritual_id(db),
        title=data.title,
        ritual_date=data.ritual_date,
        weekday=data.weekday,
        start_time=data.start_time,
        end_time=data.end_time,
        location=data.location,
        capacity=data.capacity,
        registered_count=0,
        fee=data.fee,
        status=RitualStatus.upcoming,
        description=data.description,
    )
    db.add(ritual)
    db.commit()
    db.refresh(ritual)
    return ritual


@router.put("/{ritual_id}", response_model=RitualResponse)
def update_ritual(
    ritual_id: int,
    data: RitualUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """【管理員】編輯法會"""
    ritual = db.query(Ritual).filter(Ritual.id == ritual_id).first()
    if not ritual:
        raise HTTPException(status_code=404, detail="法會不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ritual, field, value)

    db.commit()
    db.refresh(ritual)
    return ritual


@router.delete("/{ritual_id}", response_model=MessageResponse)
def delete_ritual(
    ritual_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """【管理員】刪除法會"""
    ritual = db.query(Ritual).filter(Ritual.id == ritual_id).first()
    if not ritual:
        raise HTTPException(status_code=404, detail="法會不存在")
    db.delete(ritual)
    db.commit()
    return {"message": "法會已刪除"}
