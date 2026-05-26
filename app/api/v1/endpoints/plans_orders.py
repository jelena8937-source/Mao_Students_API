# 修正後的 app/api/v1/endpoints/plans_orders.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.user import Order, OrderStatus, ServiceType  # 引入 ServiceType
from app.schemas.schemas import (
    OrderCreate, OrderResponse,
    OrderStatusUpdate, MessageResponse
)
from datetime import datetime, timezone
from decimal import Decimal

router = APIRouter(tags=["🛍️ 方案與訂單"])

# ========== 方案 Plans (改為靜態回應，回傳固定方案內容提供前端) ==========

@router.get("/plans")
def get_plans():
    """取得所有固定方案與定價（直接呼叫免查資料庫，與 ServiceType 一致）"""
    return [
        {
            "service_type": "plan_a",
            "name": "方案A - 自行取回",
            "price": Decimal("8800.00"),
            "description": "自行完成火化並取回保管"
        },
        {
            "service_type": "plan_b",
            "name": "方案B - 永久供養在蓮花勝境",
            "price": Decimal("12800.00"),
            "description": "永久供養於尊貴的蓮花勝境淨土"
        }
    ]


# ========== 訂單 Orders ==========

@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """建立訂單 (依據傳入的 service_type 自動計算金額)"""
    # 驗證傳入的是否為有效方案
    if data.service_type not in ["plan_a", "plan_b"]:
        raise HTTPException(status_code=400, detail="此 API 僅處理方案A與方案B之訂單")

    # 後端直接鎖定價格（不信任前端傳來的金額，安全防線）
    plan_prices = {
        "plan_a": Decimal("8800.00"),
        "plan_b": Decimal("12800.00")
    }
    
    base_amount = plan_prices[data.service_type]
    
    # 計算折扣 (如果勾選自行火化扣 2000)
    discount = Decimal("2000.00") if data.self_cremation else Decimal("0.00")
    final_amount = base_amount - discount

    order = Order(
        user_id=current_user.id,
        pet_id=data.pet_id,
        booking_id=data.booking_id,
        service_type=data.service_type,
        service_description="方案A - 自行取回" if data.service_type == "plan_a" else "方案B - 永久供養在蓮花勝境",
        amount=final_amount,
        self_cremation_discount=discount,
        note=data.notes,
        status=OrderStatus.pending,
        progress=0
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("/orders/my", response_model=List[OrderResponse])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """取得我的所有訂單"""
    return db.query(Order).filter(
        Order.user_id == current_user.id
    ).order_by(Order.created_at.desc()).all()


@router.get("/admin/orders", response_model=List[OrderResponse])
def admin_get_all_orders(
    status: str = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """【管理員】取得所有訂單"""
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    return query.order_by(Order.created_at.desc()).all()


@router.put("/admin/orders/{order_id}/status", response_model=OrderResponse)
def admin_update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """【管理員】更新訂單狀態"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="訂單不存在")

    valid_statuses = [s.value for s in OrderStatus]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"無效的狀態，可用值：{valid_statuses}")

    order.status = data.status
    if data.progress is not None:
        order.progress = data.progress
    if data.admin_note:
        order.admin_note = data.admin_note
    if data.enshrine_location:
        order.enshrine_location = data.enshrine_location

    if data.status == "completed":
        order.completed_at = datetime.now(timezone.utc)
    elif data.status == "processing" and order.paid_at is None:
        order.paid_at = datetime.now(timezone.utc) # 進入處理中代表已付款

    db.commit()
    db.refresh(order)
    return order