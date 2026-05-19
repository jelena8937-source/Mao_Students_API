from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.schemas.schemas import UserResponse, MessageResponse

router = APIRouter(prefix="/admin/users", tags=["👑 管理員 - 使用者管理"])


@router.get("", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """【管理員】取得所有使用者列表"""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put("/{user_id}/deactivate", response_model=MessageResponse)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    """【管理員】停用使用者帳號"""
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="不能停用自己的帳號")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="不能停用其他管理員帳號")

    user.is_active = False
    db.commit()
    return {"message": f"使用者 {user.email} 已停用"}


@router.put("/{user_id}/activate", response_model=MessageResponse)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """【管理員】重新啟用使用者帳號"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")

    user.is_active = True
    db.commit()
    return {"message": f"使用者 {user.email} 已重新啟用"}
