from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 1. 優先初始化日誌系統
from app.utils.logger_config import setup_logger
setup_logger()

# 2. 引入核心配置與資料庫元件
from app.core.config import settings
from app.core.database import engine, SessionLocal
from app.core.security import hash_password  # 💡 請確保安全模組中的函式名稱正確
from app.models.user import User  # 觸發所有 model 載入
from app.models.user import Base  # 用於建立資料表

# 3. 引入所有路由端點
from app.api.v1.endpoints import auth, bookings, plans_orders, admin_users, membership
from app.middleware.rate_limit import rate_limit_middleware


# ========== 啟動與關閉生命週期控制 (lifespan) ==========

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 【啟動時執行】自動建立資料表 + 建立預設管理員
    print("🐾 正在同步資料庫結構...")
    Base.metadata.create_all(bind=engine)
    
    _create_default_admin()
    
    print(f"✅ 資料庫初始化完成")
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 成功於本地啟動！")
    yield
    # 【關閉時執行】
    print("👋 毛同學伺服器安全關閉")


def _create_default_admin():
    """若管理員不存在則自動建立（採用 Email 唯一值安全防禦邏輯）"""
    db = SessionLocal()
    try:
        # 💡 核心改版：用 Email 作為絕對防重複依據
        admin = db.query(User).filter(User.email == settings.ADMIN_EMAIL).first()
        if not admin:
            print("🐾 偵測到系統中無管理員帳號，正在建立預設管理員...")
            new_admin = User(
                name="管理員",
                email=settings.ADMIN_EMAIL,
                phone="0900000000",  # 💡 補上符合格式的預設手機號碼，防止 NULL 崩潰
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
                member_type="general",
                is_active=True
            )
            db.add(new_admin)
            db.commit()
            print(f"👑 預設管理員帳號建立成功！帳號: {settings.ADMIN_EMAIL}")
        else:
            print("🐾 預設管理員帳號已存在，跳過初始化建立。")
    except Exception as e:
        db.rollback()
        print(f"❌ 建立預設管理員時發生錯誤: {e}")
    finally:
        db.close()


# ========== 建立 FastAPI 實例 ==========

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,   # 生產環境下自動關閉 Swagger
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


# ========== 中介軟體 Middleware ==========

# 1. CORS（解析 ALLOWED_ORIGINS 字串為 List，全面允許 Vue 前端跨域）
origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# 2. 頻率限制 Rate Limiting
app.middleware("http")(rate_limit_middleware)


# ========== 路由註冊 ==========

PREFIX = "/api/v1"
app.include_router(auth.router,         prefix=PREFIX)
app.include_router(bookings.router,     prefix=PREFIX)
app.include_router(plans_orders.router, prefix=PREFIX)
app.include_router(admin_users.router,  prefix=PREFIX)
app.include_router(membership.router,   prefix=PREFIX)

# ========== 系統健康檢查 ==========

@app.get("/health", tags=["系統"])
def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}