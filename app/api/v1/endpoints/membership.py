from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User

router = APIRouter(prefix="/membership", tags=["🎫 會員"])


@router.get("/count")
def get_membership_count(db: Session = Depends(get_db)):
    """取得目前非管理員使用者總數（供前端顯示前 10,000 名優惠名額進度）"""
    count = db.query(User).filter(User.role != "admin").count()
    return {"count": count}