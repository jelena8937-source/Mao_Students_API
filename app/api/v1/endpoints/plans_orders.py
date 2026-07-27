# 修正後的 app/api/v1/endpoints/plans_orders.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.models.user import Order, OrderStatus, ServiceType, Pet  # 引入 ServiceType 和 Pet
from app.schemas.schemas import (
    OrderCreate, OrderResponse,
    OrderStatusUpdate, MessageResponse, PetResponse, PetUpdate, PetCreate
)
from datetime import datetime, timezone
from decimal import Decimal
import random

router = APIRouter(tags=["🛍️ 方案與訂單"])

# ========== 方案 Plans (改為靜態回應，回傳固定方案內容提供前端) ==========

@router.get("/plans")
def get_plans():
    """取得所有固定方案與定價（直接呼叫免查資料庫，與 ServiceType 一致）"""
    return [
        {
            "service_type": "plan_ac",
            "name": "方案A + 方案C - 個別火化 + 免費取回留念",
            "price": Decimal("15800.00"),
            "description": "方案A基本服務費 (15,800元) + 方案C期滿自行取回 (0元)"
        },
        {
            "service_type": "plan_ad",
            "name": "方案A + 方案D - 個別火化 + 永久供養蓮花勝境",
            "price": Decimal("25700.00"),
            "description": "方案A基本服務費 (15,800元) + 方案D期滿永久供養 (9,900元)"
        },
        {
            "service_type": "plan_bc",
            "name": "方案B + 方案C - 純善業泥製作 + 免費取回留念",
            "price": Decimal("10800.00"),
            "description": "方案B善業泥製作費 (10,800元) + 方案C期滿自行取回 (0元)"
        },
        {
            "service_type": "plan_bd",
            "name": "方案B + 方案D - 純善業泥製作 + 永久供養蓮花勝境",
            "price": Decimal("20700.00"),
            "description": "方案B善業泥製作費 (10,800元) + 方案D期滿永久供養 (9,900元)"
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
    valid_plan_types = ["plan_a", "plan_b", "plan_ac", "plan_ad", "plan_bc", "plan_bd"]
    if data.service_type not in valid_plan_types:
        raise HTTPException(status_code=400, detail="此 API 僅處理方案類訂單")

    # 後端直接鎖定價格（不信任前端傳來的金額，安全防線）
    plan_prices = {
        "plan_a":  Decimal("15800.00"),
        "plan_b":  Decimal("25700.00"),
        "plan_ac": Decimal("15800.00"),
        "plan_ad": Decimal("25700.00"),
        "plan_bc": Decimal("10800.00"),
        "plan_bd": Decimal("20700.00"),
    }

    plan_descriptions = {
        "plan_a":  "方案A - 免費取回留念（舊版）",
        "plan_b":  "方案B - 永久供養在蓮花勝境（舊版）",
        "plan_ac": "方案A + 方案C - 個別火化 + 免費取回留念",
        "plan_ad": "方案A + 方案D - 個別火化 + 永久供養蓮花勝境",
        "plan_bc": "方案B + 方案C - 純善業泥製作 + 免費取回留念",
        "plan_bd": "方案B + 方案D - 純善業泥製作 + 永久供養蓮花勝境",
    }

    base_amount = plan_prices[data.service_type]

    # 自助火化折扣：僅方案A系列（plan_a/plan_ac/plan_ad）才適用
    is_plan_a_series = data.service_type in ["plan_a", "plan_ac", "plan_ad"]
    discount = Decimal("2000.00") if (data.self_cremation and is_plan_a_series) else Decimal("0.00")
    final_amount = base_amount - discount

    order = Order(
        user_id=current_user.id,
        pet_id=data.pet_id,
        booking_id=data.booking_id,
        service_type=data.service_type,
        service_description=plan_descriptions[data.service_type],
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


@router.get("/pets/my", response_model=List[PetResponse])
def get_my_pets(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """取得我的所有毛孩資料"""
    return db.query(Pet).filter(Pet.owner_id == current_user.id).all()


@router.post("/pets", response_model=PetResponse, status_code=201)
def create_my_pet(
    data: PetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """新增我的毛孩資料"""
    # 產生唯一的 pet_id (格式：PET-MTX-00000X，依據最大 ID + 1 遞增)
    from sqlalchemy import func
    max_id = db.query(func.max(Pet.id)).scalar() or 0
    next_id = max_id + 1
    while True:
        candidate_id = f"PET-MTX-{next_id:06d}"
        exists = db.query(Pet).filter(Pet.pet_id == candidate_id).first()
        if not exists:
            break
        next_id += 1

    # 建立 Pet 實例
    pet = Pet(
        owner_id=current_user.id,
        pet_id=candidate_id,
        name=data.name,
        pet_type=data.pet_type,
        breed=data.breed,
        birth_date=data.birth_date,
        age=data.age,
        memorial_date=data.memorial_date,
        status="pending",
        location=None
    )
    db.add(pet)
    db.commit()
    db.refresh(pet)
    return pet


@router.put("/pets/{pet_id}", response_model=PetResponse)
def update_my_pet(
    pet_id: int,
    data: PetUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新我的毛孩資料（僅限飼主本人）"""
    pet = db.query(Pet).filter(Pet.id == pet_id, Pet.owner_id == current_user.id).first()
    if not pet:
        raise HTTPException(status_code=404, detail="找不到該毛孩資料，或您無權編輯")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pet, field, value)

    db.commit()
    db.refresh(pet)
    return pet


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