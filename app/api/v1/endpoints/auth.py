from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user
)
from app.models.user import User
from app.schemas.schemas import (
    UserRegister, UserLogin, Token,
    UserResponse, UserUpdate, PasswordChange,
    RefreshRequest, MessageResponse
)

router = APIRouter(prefix="/auth", tags=["🔐 會員認證"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """註冊新會員"""
    # 檢查 Email 是否已存在
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="此 Email 已被註冊")

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        phone=data.phone,
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """會員登入，回傳 JWT Token"""
    user = db.query(User).filter(User.email == data.email).first()

    # 故意不區分「帳號不存在」或「密碼錯誤」，防止帳號列舉攻擊
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="帳號已被停用，請聯絡客服")

    token_data = {"sub": str(user.id), "role": user.role}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user=user,
    )


@router.post("/refresh", response_model=Token)
def refresh_token(data: RefreshRequest, db: Session = Depends(get_db)):
    """使用 Refresh Token 換取新的 Access Token"""
    payload = decode_token(data.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token 類型錯誤")

    user = db.query(User).filter(
        User.id == int(payload["sub"]), User.is_active == True
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="使用者不存在")

    token_data = {"sub": str(user.id), "role": user.role}
    return Token(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user=user,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """取得目前登入的使用者資料"""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新個人資料"""
    if data.name:
        current_user.name = data.name
    if data.phone is not None:
        current_user.phone = data.phone
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """修改密碼"""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="目前密碼錯誤")

    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "密碼修改成功"}
