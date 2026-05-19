from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.user import Plan, Order, OrderStatus
from app.schemas.schemas import (
    PlanCreate, PlanResponse,
    OrderCreate, OrderResponse,
    OrderStatusUpdate, MessageResponse
)
from datetime import datetime, timezone

router = APIRouter(tags=["🛍️ 方案與訂單"])


# ========== 方案 Plans ==========

@router.get("/plans", response_model=List[PlanResponse])
def get_plans(db: Session = Depends(get_db)):
    """取得所有啟用中的方案（公開）"""
    return db.query(Plan).filter(Plan.is_active == True).all()


@router.post("/admin/plans", response_model=PlanResponse, status_code=201)
def create_plan(
    data: PlanCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """【管理員】新增方案"""
    plan = Plan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.put("/admin/plans/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: int,
    data: PlanCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """【管理員】更新方案"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="方案不存在")

    for field, value in data.model_dump().items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/admin/plans/{plan_id}", response_model=MessageResponse)
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """【管理員】停用方案（軟刪除）"""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="方案不存在")
    plan.is_active = False
    db.commit()
    return {"message": "方案已停用"}


# ========== 訂單 Orders ==========

@router.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """建立訂單"""
    plan = db.query(Plan).filter(Plan.id == data.plan_id, Plan.is_active == True).first()
    if not plan:
        raise HTTPException(status_code=404, detail="方案不存在或已停用")

    order = Order(
        user_id=current_user.id,
        plan_id=plan.id,
        amount=plan.price,
        notes=data.notes,
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
    if data.status == "paid":
        order.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)
    return order
