# 毛同學後端 API

FastAPI + MySQL 後端專案

## 📁 專案結構

```
maosmain-backend/
├── main.py                         # 應用程式入口
├── requirements.txt                # Python 套件
├── .env.example                    # 環境變數範本
├── .env                            # 你的環境變數（不 commit）
└── app/
    ├── core/
    │   ├── config.py               # 設定（讀取 .env）
    │   ├── database.py             # 資料庫連線
    │   └── security.py             # JWT + 密碼加密 + 權限驗證
    ├── models/
    │   └── user.py                 # 所有資料庫 Model
    ├── schemas/
    │   └── schemas.py              # Pydantic 資料驗證
    ├── api/v1/endpoints/
    │   ├── auth.py                 # 登入/註冊/個人資料
    │   ├── bookings.py             # 預約諮詢
    │   ├── plans_orders.py         # 方案與訂單
    │   └── admin_users.py          # 管理員：使用者管理
    └── middleware/
        └── rate_limit.py           # 防暴力破解限流
```

## 🚀 快速啟動

### 1. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入你的 MySQL 密碼和其他設定
```

### 3. 建立 MySQL 資料庫

```sql
CREATE DATABASE maosmain CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. 啟動伺服器

```bash
uvicorn main:app --reload
```

伺服器啟動後會自動：
- 建立所有資料表
- 建立預設管理員帳號（見 .env）

### 5. 查看 API 文件

瀏覽器打開：http://localhost:8000/docs

---

## 🔑 API 端點總覽

### 認證
| 方法 | 路徑 | 說明 | 權限 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | 註冊 | 公開 |
| POST | `/api/v1/auth/login` | 登入 | 公開 |
| POST | `/api/v1/auth/refresh` | 刷新 Token | 公開 |
| GET  | `/api/v1/auth/me` | 取得個人資料 | 登入 |
| PUT  | `/api/v1/auth/me` | 更新個人資料 | 登入 |
| POST | `/api/v1/auth/change-password` | 修改密碼 | 登入 |

### 預約
| 方法 | 路徑 | 說明 | 權限 |
|------|------|------|------|
| POST | `/api/v1/bookings` | 建立預約 | 登入 |
| GET  | `/api/v1/bookings/my` | 我的預約 | 登入 |
| DELETE | `/api/v1/bookings/{id}` | 取消預約 | 登入 |
| GET  | `/api/v1/bookings/admin/all` | 所有預約 | 管理員 |
| PUT  | `/api/v1/bookings/admin/{id}/status` | 更新預約狀態 | 管理員 |

### 方案與訂單
| 方法 | 路徑 | 說明 | 權限 |
|------|------|------|------|
| GET  | `/api/v1/plans` | 取得方案列表 | 公開 |
| POST | `/api/v1/admin/plans` | 新增方案 | 管理員 |
| PUT  | `/api/v1/admin/plans/{id}` | 更新方案 | 管理員 |
| DELETE | `/api/v1/admin/plans/{id}` | 停用方案 | 管理員 |
| POST | `/api/v1/orders` | 建立訂單 | 登入 |
| GET  | `/api/v1/orders/my` | 我的訂單 | 登入 |
| GET  | `/api/v1/admin/orders` | 所有訂單 | 管理員 |
| PUT  | `/api/v1/admin/orders/{id}/status` | 更新訂單狀態 | 管理員 |

### 管理員：使用者管理
| 方法 | 路徑 | 說明 | 權限 |
|------|------|------|------|
| GET  | `/api/v1/admin/users` | 使用者列表 | 管理員 |
| PUT  | `/api/v1/admin/users/{id}/deactivate` | 停用帳號 | 管理員 |
| PUT  | `/api/v1/admin/users/{id}/activate` | 啟用帳號 | 管理員 |

---

## 🛡️ 已實作的安全措施

- ✅ **bcrypt** 密碼雜湊（不存明文）
- ✅ **JWT Access + Refresh Token** 雙 Token 機制
- ✅ **RBAC 角色權限**：user / admin
- ✅ **Rate Limiting**：登入每分鐘限 10 次，一般 API 限 60 次
- ✅ **帳號列舉防護**：登入錯誤不區分「帳號不存在」或「密碼錯誤」
- ✅ **Pydantic 輸入驗證**：密碼強度、Email 格式等
- ✅ **CORS 白名單**：只允許指定前端來源
- ✅ **生產環境關閉 Swagger**：`DEBUG=False` 時不暴露 API 文件

## 🔗 Vue 前端串接範例

```javascript
// utils/api.js
import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000/api/v1' })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  res => res,
  async err => {
    if (err.response?.status === 401) {
      // Token 過期，嘗試用 refresh token 換新的
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
          localStorage.setItem('access_token', data.access_token)
          err.config.headers.Authorization = `Bearer ${data.access_token}`
          return api.request(err.config)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(err)
  }
)

export default api
```
