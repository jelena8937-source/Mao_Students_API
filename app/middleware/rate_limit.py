from fastapi import Request, HTTPException
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

# 簡易記憶體式 Rate Limiter（生產環境建議改用 Redis）
_request_counts: dict = defaultdict(list)
_lock = asyncio.Lock()


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate Limiting 中介軟體
    - 一般 API：每分鐘 60 次
    - 登入/註冊：每分鐘 10 次（防暴力破解）
    """
    # CORS 預檢請求 (OPTIONS) 直接放行，不進行頻率限制
    if request.method == "OPTIONS":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    now = datetime.utcnow()

    # 敏感路徑用更嚴格的限制
    sensitive_paths = ["/api/v1/auth/login", "/api/v1/auth/register"]
    is_sensitive = any(path.startswith(p) for p in sensitive_paths)

    limit = 10 if is_sensitive else 60
    window = timedelta(minutes=1)
    key = f"{client_ip}:{path if is_sensitive else 'general'}"

    async with _lock:
        # 清除過期的請求記錄
        _request_counts[key] = [
            t for t in _request_counts[key] if now - t < window
        ]

        if len(_request_counts[key]) >= limit:
            raise HTTPException(
                status_code=429,
                detail=f"請求過於頻繁，請稍後再試（每分鐘限制 {limit} 次）"
            )

        _request_counts[key].append(now)

    response = await call_next(request)
    return response
