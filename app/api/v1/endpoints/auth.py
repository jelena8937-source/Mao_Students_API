from datetime import datetime, timedelta, timezone, date
from secrets import token_urlsafe
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.config import settings
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
    RefreshRequest, MessageResponse,
    ForgotPasswordRequest, ResetPasswordRequest
)

router = APIRouter(prefix="/auth", tags=["🔐 會員認證"])

_password_reset_tokens: dict[str, dict] = {}


def generate_member_id(db: Session) -> str:
    current_year = date.today().year
    start_of_year = datetime(current_year, 1, 1, 0, 0, 0)
    end_of_year = datetime(current_year, 12, 31, 23, 59, 59)
    
    count = db.query(User).filter(
        User.created_at >= start_of_year,
        User.created_at <= end_of_year
    ).count()
    
    seq = count + 1
    return f"MTX-{current_year}-{seq:05d}"


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """註冊新會員"""
    # 檢查 Email 是否已存在
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="此 Email 已被註冊")

    new_member_id = generate_member_id(db)

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        phone=data.phone,
        role="user",
        member_id=new_member_id,
        member_since=date.today(),
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


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        return {"message": "如果 Email 存在，我們已建立重設密碼連結。"}

    token = token_urlsafe(32)
    _password_reset_tokens[token] = {
        "user_id": user.id,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30),
    }

    response = {"message": "已建立重設密碼連結，請於 30 分鐘內完成。"}
    if settings.DEBUG:
        response["reset_url"] = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    return response


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_data = _password_reset_tokens.get(data.token)
    if not token_data:
        raise HTTPException(status_code=400, detail="重設連結無效或已過期")

    if datetime.now(timezone.utc) > token_data["expires_at"]:
        _password_reset_tokens.pop(data.token, None)
        raise HTTPException(status_code=400, detail="重設連結已過期")

    user = db.query(User).filter(User.id == token_data["user_id"], User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=400, detail="帳號不存在或已停用")

    user.hashed_password = hash_password(data.new_password)
    db.commit()
    _password_reset_tokens.pop(data.token, None)
    return {"message": "密碼已更新，請重新登入。"}


@router.get("/google/login")
def google_login():
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="尚未設定 Google 登入金鑰")

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    return {"url": f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"}


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=503, detail="尚未設定 Google 登入金鑰")

    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_response.status_code >= 400:
            raise HTTPException(status_code=401, detail="Google 授權失敗")

        google_access_token = token_response.json().get("access_token")
        profile_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"},
        )
        if profile_response.status_code >= 400:
            raise HTTPException(status_code=401, detail="無法取得 Google 使用者資料")

    profile = profile_response.json()
    email = profile.get("email")
    name = profile.get("name") or (email.split("@")[0] if email else "Google User")

    if not email:
        raise HTTPException(status_code=401, detail="Google 帳號未提供 Email")

    user = db.query(User).filter(User.email == email).first()
    is_new_google = False
    if not user:
        is_new_google = True
        new_member_id = generate_member_id(db)
        user = User(
            name=name,
            email=email,
            phone="0900000000",
            hashed_password=hash_password(token_urlsafe(32)),
            role="user",
            is_active=True,
            member_id=new_member_id,
            member_since=date.today(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="帳號已停用")

    token_data = {"sub": str(user.id), "role": user.role}
    query = urlencode({
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "member_id": user.member_id or "",
        "member_type": user.member_type or "general",
        "is_new_google": "true" if is_new_google or user.phone == "0900000000" else "false",
    })
    return RedirectResponse(f"{settings.FRONTEND_URL}/auth/google/callback?{query}")


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
