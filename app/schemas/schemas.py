"""
Pydantic Schemas - 依據前端頁面分析設計

每個 Schema 都標註對應的前端頁面與用途
"""

from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import re


# ========================================
# User Schemas
# 來源：RegisterView.vue + LoginView.vue + Account.vue
# ========================================

class UserRegister(BaseModel):
    """RegisterView.vue 註冊表單"""
    name: str
    email: EmailStr
    phone: str
    password: str
    # confirm_password 只在前端驗證，後端不需要儲存

    @field_validator("name")
    @classmethod
    def name_valid(cls, v):
        if len(v.strip()) < 2:
            raise ValueError("姓名至少 2 個字元")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v):
        cleaned = re.sub(r"[-\s]", "", v)
        if not re.match(r"^09\d{8}$", cleaned):
            raise ValueError("請輸入有效的台灣手機號碼（09XXXXXXXX）")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("密碼至少 8 個字元")
        if not re.search(r"[A-Z]", v):
            raise ValueError("密碼需包含至少一個大寫字母")
        if not re.search(r"[0-9]", v):
            raise ValueError("密碼需包含至少一個數字")
        return v


class UserLogin(BaseModel):
    """LoginView.vue 登入表單"""
    email: EmailStr
    password: str
    # remember: bool = False  # 前端 UI 用，後端用 token 有效期控制


class UserResponse(BaseModel):
    """
    使用者資料回應
    對應 Account.vue 個人資料頁 + Admin.vue 會員列表
    """
    id: int
    name: str
    email: str
    phone: str
    member_id: Optional[str]        # 會員編號 MTX-YYYY-XXXXXX
    member_type: str                 # 一般會員 / 終身會員
    member_since: Optional[date]     # Account.vue 卡片 "Since"
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Account.vue 個人資料編輯"""
    name: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v):
        if v is None:
            return v
        cleaned = re.sub(r"[-\s]", "", v)
        if not re.match(r"^09\d{8}$", cleaned):
            raise ValueError("請輸入有效的台灣手機號碼")
        return v


class PasswordChange(BaseModel):
    """Account.vue 修改密碼"""
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("密碼至少 8 個字元")
        if not re.search(r"[A-Z]", v):
            raise ValueError("密碼需包含至少一個大寫字母")
        if not re.search(r"[0-9]", v):
            raise ValueError("密碼需包含至少一個數字")
        return v


# ========================================
# Token Schemas
# ========================================

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("密碼至少需要 8 個字元")
        if not re.search(r"[A-Z]", v):
            raise ValueError("密碼至少需要 1 個大寫英文")
        if not re.search(r"[0-9]", v):
            raise ValueError("密碼至少需要 1 個數字")
        return v


# ========================================
# Pet Schemas
# 來源：Account.vue 毛孩資料 + Booking.vue Step 2 + Admin.vue
# ========================================

class PetCreate(BaseModel):
    """建立毛孩資料（Account.vue 新增毛孩）"""
    name: str
    pet_type: str                    # cat / dog / rabbit / bird / other
    breed: Optional[str] = None      # 品種
    birth_date: Optional[date] = None
    age: Optional[str] = None        # 文字年齡，如：12歲
    memorial_date: Optional[date] = None  # 紀念日（離世日）


class PetResponse(BaseModel):
    """
    毛孩資料回應
    對應 Account.vue 毛孩資料頁完整顯示
    """
    id: int
    pet_id: Optional[str]            # PET-MTX-XXXXXX
    name: str
    pet_type: str
    breed: Optional[str]
    birth_date: Optional[date]       # Account.vue "生日"
    age: Optional[str]
    memorial_date: Optional[date]    # Account.vue "紀念日"
    status: str                      # 已安奉 / 自行取回 / 處理中
    location: Optional[str]          # Account.vue "安奉位置"
    created_at: datetime

    model_config = {"from_attributes": True}


class PetUpdate(BaseModel):
    """更新毛孩資料"""
    name: Optional[str] = None
    breed: Optional[str] = None
    birth_date: Optional[date] = None
    age: Optional[str] = None
    memorial_date: Optional[date] = None
    status: Optional[str] = None
    location: Optional[str] = None


# ========================================
# Booking Schemas
# 來源：Booking.vue 三步驟表單（完整對應）
# ========================================

class BookingCreate(BaseModel):
    """
    Booking.vue 預約表單送出
    三個 Step 的所有欄位合併
    """
    # Step 1: 飼主資料
    owner_name: str
    phone: str
    email: EmailStr
    member_id_input: Optional[str] = None  # 會員編號（可選）

    # Step 2: 毛孩資料
    pet_name: str
    pet_type: str                           # cat / dog / rabbit / bird / other
    pet_breed: Optional[str] = None
    pet_age: Optional[str] = None

    # Step 3: 服務選擇
    service_type: str                       # consultation / plan_a / plan_b / ritual / membership
    self_cremation: bool = False            # 已自行火化，享折扣
    preferred_date: date                    # 希望聯繫日期
    preferred_time: Optional[str] = None   # 希望聯繫時段
    message: Optional[str] = None          # 備註說明
    agreed_to_terms: bool                  # 同意服務條款（必須為 True）
    estimated_amount: Optional[float] = None

    @field_validator("agreed_to_terms")
    @classmethod
    def must_agree(cls, v):
        if not v:
            raise ValueError("請閱讀並同意服務條款")
        return v

    @field_validator("service_type")
    @classmethod
    def valid_service(cls, v):
        valid = ["consultation", "plan_a", "plan_b", "ritual", "membership"]
        if v not in valid:
            raise ValueError(f"無效的服務類型，可用值：{valid}")
        return v

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, v):
        cleaned = re.sub(r"[-\s]", "", v)
        if not re.match(r"^09\d{8}$", cleaned):
            raise ValueError("請輸入有效的台灣手機號碼")
        return v


class BookingResponse(BaseModel):
    """預約回應（使用者視角）"""
    id: int
    owner_name: str
    phone: str
    email: str
    pet_name: str
    pet_type: str
    pet_breed: Optional[str]
    pet_age: Optional[str]
    service_type: str
    self_cremation: bool
    preferred_date: date
    preferred_time: Optional[str]
    message: Optional[str]
    estimated_amount: Optional[Decimal]   # 後端計算的預估費用
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingAdminResponse(BookingResponse):
    """
    預約回應（管理員視角）
    Admin.vue 訂單追蹤額外顯示欄位
    """
    member_id_input: Optional[str]
    admin_notes: Optional[str]
    assigned_staff: Optional[str]


class BookingStatusUpdate(BaseModel):
    """Admin.vue 更新預約狀態"""
    status: str
    admin_notes: Optional[str] = None
    assigned_staff: Optional[str] = None


# ========================================
# Order Schemas
# 來源：Account.vue 服務紀錄 + Admin.vue 訂單追蹤
# ========================================
class OrderCreate(BaseModel):
    """建立訂單時傳入的參數"""
    service_type: str        # plan_a / plan_b
    pet_id: Optional[int] = None
    booking_id: Optional[int] = None
    self_cremation: bool = False
    notes: Optional[str] = None
    
class OrderResponse(BaseModel):
    """
    訂單回應（使用者視角）
    對應 Account.vue 服務紀錄 列表
    """
    id: int
    order_number: Optional[str]          # ORD-YYYY-XXXX
    service_type: str
    service_description: Optional[str]   # 如：方案B - 永久供養在蓮花勝境
    amount: Decimal
    status: str                          # Account.vue statusText
    progress: int                        # 0-100，Admin.vue 進度條
    enshrine_location: Optional[str]     # Account.vue "安奉位置"
    paid_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    # 關聯資料（展開顯示）
    pet: Optional[PetResponse] = None

    model_config = {"from_attributes": True}


class OrderAdminResponse(OrderResponse):
    """
    訂單回應（管理員視角）
    Admin.vue 訂單追蹤完整欄位
    """
    contact_date: Optional[date]         # Admin.vue contactDate
    contact_time_slot: Optional[str]     # Admin.vue contactTime
    note: Optional[str]                  # Admin.vue note（客戶備註）
    admin_note: Optional[str]            # Admin.vue 管理員備註
    self_cremation_discount: Decimal     # 折扣金額

    # 會員資訊
    user: Optional[UserResponse] = None


class OrderStatusUpdate(BaseModel):
    """Admin.vue 更新訂單狀態"""
    status: str
    progress: Optional[int] = None      # 0-100
    admin_note: Optional[str] = None
    enshrine_location: Optional[str] = None


# ========================================
# Ritual Schemas
# 來源：Rituals.vue + Admin.vue 法會管理
# ========================================

class RitualResponse(BaseModel):
    """
    法會回應
    對應 Rituals.vue 法會時程表 + Admin.vue 法會管理
    """
    id: int
    ritual_id: Optional[str]            # RTL-YYYY-MM
    title: str                          # 四月份地藏經法會
    ritual_date: date
    weekday: Optional[str]              # 週日
    start_time: str                     # 09:00
    end_time: str                       # 12:00
    location: str                       # 新竹大佛禪寺
    capacity: int                       # 50
    registered_count: int               # 已報名人數
    fee: Decimal                        # 1800
    status: str
    description: Optional[str]

    model_config = {"from_attributes": True}


class RitualCreate(BaseModel):
    """Admin.vue 新增法會"""
    title: str
    ritual_date: date
    weekday: Optional[str] = None
    start_time: str
    end_time: str
    location: str
    capacity: int = 50
    fee: Decimal = Decimal("1800")
    description: Optional[str] = None


class RitualUpdate(BaseModel):
    """Admin.vue 編輯法會"""
    title: Optional[str] = None
    ritual_date: Optional[date] = None
    weekday: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    capacity: Optional[int] = None
    fee: Optional[Decimal] = None
    status: Optional[str] = None
    description: Optional[str] = None


class RitualRegistrationCreate(BaseModel):
    """
    法會報名
    對應 Rituals.vue CTA「報名法會」→ Booking.vue service_type=ritual
    """
    ritual_id: int
    will_attend: bool = True            # 親自出席 or 委託代參
    pet_names: Optional[str] = None     # 為哪些毛孩迴向（逗號分隔）
    notes: Optional[str] = None


class RitualRegistrationResponse(BaseModel):
    """法會報名回應"""
    id: int
    ritual_id: int
    will_attend: bool
    pet_names: Optional[str]
    notes: Optional[str]
    created_at: datetime

    ritual: Optional[RitualResponse] = None

    model_config = {"from_attributes": True}


# ========================================
# Common
# ========================================

class MessageResponse(BaseModel):
    message: str


class PaginatedResponse(BaseModel):
    """分頁回應（Admin.vue 會員列表有分頁）"""
    total: int
    page: int
    per_page: int
    items: list
