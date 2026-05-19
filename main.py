from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, SessionLocal
from app.core.security import hash_password
from app.models.user import User  # 觸發所有 model 載入
from app.models.user import Base  # 用於建立資料表

# 引入所有路由
from app.api.v1.endpoints import auth, bookings, plans_orders, admin_users
from app.middleware.rate_limit import rate_limit_middleware


# ========== 啟動時初始化 ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動：自動建立資料表 + 建立預設管理員
    Base.metadata.create_all(bind=engine)
    _create_default_admin()
    print(f"✅ 資料庫初始化完成")
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 啟動成功")
    yield
    # 關閉時（可做清理工作）
    print("👋 伺服器關閉")


def _create_default_admin():
    """若管理員不存在則自動建立"""
    db = SessionLocal()
    try:
        exists = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if not exists:
            admin = User(
                name="管理員",
                email=settings.ADMIN_EMAIL,
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)
            db.commit()
            print(f"👑 已建立預設管理員：{settings.ADMIN_EMAIL}")
    finally:
        db.close()


# ========== 建立 FastAPI App ==========

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,   # 生產環境關閉 Swagger
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


# ========== 中介軟體 Middleware ==========

# 1. CORS（允許前端跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# 2. Rate Limiting
app.middleware("http")(rate_limit_middleware)


# ========== 路由註冊 ==========

PREFIX = "/api/v1"
app.include_router(auth.router,               prefix=PREFIX)
app.include_router(bookings.router,           prefix=PREFIX)
app.include_router(plans_orders.router,       prefix=PREFIX)
app.include_router(admin_users.router,        prefix=PREFIX)


# ========== 健康檢查 ==========

@app.get("/health", tags=["系統"])
def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
