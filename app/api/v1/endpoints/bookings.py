from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.user import Booking, BookingStatus
from app.schemas.schemas import (
    BookingCreate, BookingResponse,
    BookingAdminResponse, BookingStatusUpdate, MessageResponse
)

router = APIRouter(prefix="/bookings", tags=["📅 預約諮詢"])


# ========== 使用者端 ==========

@router.post("", response_model=BookingResponse, status_code=201)
def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """建立預約諮詢"""
    booking = Booking(
        user_id=current_user.id,
        **data.model_dump()
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/my", response_model=List[BookingResponse])
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """取得我的所有預約"""
    return db.query(Booking).filter(
        Booking.user_id == current_user.id
    ).order_by(Booking.created_at.desc()).all()


@router.delete("/{booking_id}", response_model=MessageResponse)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """取消預約（只能取消自己的 pending 預約）"""
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.user_id == current_user.id,
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="預約不存在")
    if booking.status != BookingStatus.pending:
        raise HTTPException(status_code=400, detail="只能取消待確認的預約")

    booking.status = BookingStatus.cancelled
    db.commit()
    return {"message": "預約已取消"}


# ========== 管理員端 ==========

@router.get("/admin/all", response_model=List[BookingAdminResponse])
def admin_get_all_bookings(
    status: str = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """【管理員】取得所有預約，可依狀態篩選"""
    query = db.query(Booking)
    if status:
        query = query.filter(Booking.status == status)
    return query.order_by(Booking.created_at.desc()).all()


@router.put("/admin/{booking_id}/status", response_model=BookingAdminResponse)
def admin_update_booking_status(
    booking_id: int,
    data: BookingStatusUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """【管理員】更新預約狀態"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="預約不存在")

    valid_statuses = [s.value for s in BookingStatus]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"無效的狀態，可用值：{valid_statuses}")

    booking.status = data.status
    if data.admin_notes:
        booking.admin_notes = data.admin_notes
    db.commit()
    db.refresh(booking)
    return booking
