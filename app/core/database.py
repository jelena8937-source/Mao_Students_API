from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # 自動偵測斷線重連
    pool_recycle=3600,        # 每小時回收連線
    pool_size=10,             # 連線池大小
    max_overflow=20,          # 最大額外連線數
    echo=settings.DEBUG,      # DEBUG 模式下印出 SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# FastAPI Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
