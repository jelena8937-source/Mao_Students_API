"""
資料庫 Models - 依據前端頁面分析設計

前端頁面對照：
- RegisterView.vue  → User model
- Account.vue       → User, Pet, Order models
- Booking.vue       → Booking model（三步驟表單）
- Admin.vue         → User, Pet, Booking, Order, Ritual models
- Rituals.vue       → Ritual, RitualRegistration models
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, Text,
    DateTime, ForeignKey, Enum, Numeric, Date, JSON  # 💡 引入 JSON 欄位支援
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


# ========================================
# Enums
# ========================================

class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class MemberType(str, enum.Enum):
    general = "general"       # 一般會員
    lifetime = "lifetime"     # 終身會員


class PetType(str, enum.Enum):
    cat = "cat"
    dog = "dog"
    rabbit = "rabbit"
    bird = "bird"
    other = "other"


class PetStatus(str, enum.Enum):
    """寵物安奉狀態（來自 Account.vue 毛孩資料頁）"""
    enshrined = "enshrined"       # 已安奉
    self_kept = "self_kept"       # 自行取回保管
    pending = "pending"           # 處理中


class ServiceType(str, enum.Enum):
    """服務類型（來自 Booking.vue serviceTypes）"""
    consultation = "consultation"   # 諮詢服務（免費）
    plan_a = "plan_a"               # 方案A - 自行取回 NT$8,800
    plan_b = "plan_b"               # 方案B - 永久供養在蓮花勝境 NT$12,800
    ritual = "ritual"               # 法會報名 NT$1,800
    membership = "membership"       # 會員申請 NT$9,800


class BookingStatus(str, enum.Enum):
    """預約狀態（來自 Admin.vue 訂單追蹤）"""
    pending = "pending"           # 待確認
    confirmed = "confirmed"       # 已確認
    processing = "processing"     # 處理中（製作中）
    completed = "completed"       # 已完成
    cancelled = "cancelled"       # 已取消


class OrderStatus(str, enum.Enum):
    """訂單狀態（來自 Admin.vue 訂單追蹤）"""
    pending = "pending"           # 待確認
    processing = "processing"     # 處理中
    completed = "completed"       # 已完成
    cancelled = "cancelled"       # 已取消


class RitualStatus(str, enum.Enum):
    """法會狀態（來自 Rituals.vue & Admin.vue）"""
    upcoming = "upcoming"         # 即將舉行
    ongoing = "ongoing"           # 進行中
    completed = "completed"       # 已結束
    cancelled = "cancelled"       # 已取消


# ========================================
# User（會員）
# 來源：RegisterView.vue + Account.vue 個人資料 + Admin.vue 會員管理
# ========================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # --- RegisterView.vue 表單欄位 ---
    name = Column(String(50), nullable=False, comment="姓名")
    email = Column(String(100), unique=True, index=True, nullable=False, comment="電子郵件")
    phone = Column(String(20), nullable=False, comment="聯絡電話")
    hashed_password = Column(String(255), nullable=False, comment="密碼（bcrypt）")

    # --- Account.vue 顯示欄位 ---
    member_id = Column(String(30), unique=True, index=True, nullable=True,
                        comment="會員編號，格式：MTX-YYYY-XXXXXX，加入後自動產生")
    member_type = Column(Enum(MemberType), default=MemberType.general,
                            comment="會員類型：一般會員 / 終身會員")
    member_since = Column(Date, nullable=True, comment="入會日期（用於卡片顯示）")

    # --- 系統欄位 ---
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False,
                    comment="角色：user / admin")
    is_active = Column(Boolean, default=True, nullable=False, comment="帳號是否啟用")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 關聯
    pets = relationship("Pet", back_populates="owner", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="user")
    orders = relationship("Order", back_populates="user")
    ritual_registrations = relationship("RitualRegistration", back_populates="user")

    def __repr__(self):
        return f"<User {self.member_id} {self.name} ({self.role})>"


# ========================================
# Pet（毛孩）
# 來源：Account.vue 毛孩資料頁 + Admin.vue 訂單欄位 + Booking.vue Step 2
# ========================================

class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="飼主")

    # --- Account.vue 毛孩資料顯示 ---
    pet_id = Column(String(30), unique=True, index=True, nullable=True,
                    comment="寵物編號，格式：PET-MTX-XXXXXX，自動產生")
    name = Column(String(50), nullable=False, comment="毛孩名字")
    pet_type = Column(Enum(PetType), nullable=False, comment="類型：貓/狗/兔/鳥/其他")
    breed = Column(String(50), nullable=True, comment="品種，如：米克斯、柴犬")

    # --- Account.vue + Booking.vue ---
    birth_date = Column(Date, nullable=True, comment="生日")
    age = Column(String(10), nullable=True, comment="年齡（文字，如：12歲）")
    memorial_date = Column(Date, nullable=True, comment="紀念日（離世日）")

    # --- Account.vue 毛孩狀態 ---
    status = Column(Enum(PetStatus), default=PetStatus.pending, comment="安奉狀態")
    location = Column(String(100), nullable=True,
                        comment="安奉或保管位置，如：新竹大佛禪寺 / 自行保管")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 關聯
    owner = relationship("User", back_populates="pets")
    orders = relationship("Order", back_populates="pet")

    def __repr__(self):
        return f"<Pet {self.pet_id} {self.name} ({self.pet_type})>"


# ========================================
# Booking（預約諮詢）
# 來源：Booking.vue 三步驟表單（完整對應）
# ========================================

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True,
                        comment="若已登入則關聯，非會員可為 null")

    # --- Step 1: 飼主資料 ---
    owner_name = Column(String(50), nullable=False, comment="姓名")
    phone = Column(String(20), nullable=False, comment="手機號碼")
    email = Column(String(100), nullable=False, comment="電子郵件")
    member_id_input = Column(String(30), nullable=True,
                                comment="飼主填寫的會員編號（MTX-XXXX-XXXXXX），非必填")

    # --- Step 2: 毛孩資料 ---
    pet_name = Column(String(50), nullable=False, comment="毛孩名字")
    pet_type = Column(Enum(PetType), nullable=False, comment="類型")
    pet_breed = Column(String(50), nullable=True, comment="品種")
    pet_age = Column(String(10), nullable=True, comment="年齡（文字）")

    # --- Step 3: 服務選擇 ---
    service_type = Column(Enum(ServiceType), nullable=False, comment="服務類型")
    self_cremation = Column(Boolean, default=False,
                            comment="已自行完成火化（-NT$2,000）")
    preferred_date = Column(Date, nullable=False, comment="希望聯繫日期")
    preferred_time = Column(String(30), nullable=True,
                            comment="希望聯繫時段，如：09:00 - 10:00")
    message = Column(Text, nullable=True, comment="備註說明")
    agreed_to_terms = Column(Boolean, default=False, comment="同意服務條款")

    # --- 費用（由後端計算，不信任前端）---
    estimated_amount = Column(Numeric(10, 2), nullable=True, comment="預估費用")

    # --- 管理員處理欄位 ---
    status = Column(Enum(BookingStatus), default=BookingStatus.pending, comment="預約狀態")
    admin_notes = Column(Text, nullable=True, comment="管理員備註（使用者不可見）")
    assigned_staff = Column(String(50), nullable=True, comment="負責人員")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 關聯
    user = relationship("User", back_populates="bookings")
    order = relationship("Order", back_populates="booking", uselist=False)

    def __repr__(self):
        return f"<Booking #{self.id} {self.pet_name} {self.service_type} {self.status}>"


# ========================================
# Order（服務訂單）
# 來源：Account.vue 服務紀錄 + Admin.vue 訂單追蹤
# ========================================

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=True,
                    comment="關聯毛孩（若已建立寵物資料）")
    
    # 💡 加上 unique=True 確保一筆預約諮詢只會對應到一張實體服務訂單，防止邏輯重複
    booking_id = Column(Integer, ForeignKey("bookings.id"), unique=True, nullable=True,
                        comment="來源預約單")

    # --- Account.vue 服務紀錄顯示 ---
    order_number = Column(String(20), unique=True, index=True, nullable=True,
                            comment="訂單編號，格式：ORD-YYYY-XXXX，自動產生")
    service_type = Column(Enum(ServiceType), nullable=False, comment="服務類型")
    service_description = Column(String(100), nullable=True,
                                    comment="服務說明，如：方案B - 永久供養在蓮花勝境")

    # --- Admin.vue 訂單追蹤欄位 ---
    amount = Column(Numeric(10, 2), nullable=False, comment="成交金額")
    self_cremation_discount = Column(Numeric(10, 2), default=0,
                                        comment="自助火化折扣（-2000）")
    status = Column(Enum(OrderStatus), default=OrderStatus.pending, comment="訂單狀態")
    progress = Column(Integer, default=0, comment="進度百分比 0-100（Admin 進度條）")

    # --- Admin.vue 訂單詳細欄位 ---
    contact_date = Column(Date, nullable=True, comment="聯繫日期")
    contact_time_slot = Column(String(30), nullable=True, comment="聯繫時段")
    note = Column(Text, nullable=True, comment="客戶備註")
    admin_note = Column(Text, nullable=True, comment="管理員備註（客戶不可見）")

    # 安奉地點（完成後填入）
    enshrine_location = Column(String(100), nullable=True, comment="安奉位置")

    paid_at = Column(DateTime(timezone=True), nullable=True, comment="付款時間")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成時間")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 關聯
    user = relationship("User", back_populates="orders")
    pet = relationship("Pet", back_populates="orders")
    booking = relationship("Booking", back_populates="order")

    def __repr__(self):
        return f"<Order {self.order_number} {self.service_type} {self.status}>"


# ========================================
# Ritual（法會）
# 來源：Rituals.vue 法會時程表 + Admin.vue 法會管理
# ========================================

class Ritual(Base):
    __tablename__ = "rituals"

    id = Column(Integer, primary_key=True, index=True)

    # --- Rituals.vue & Admin.vue 顯示欄位 ---
    ritual_id = Column(String(20), unique=True, index=True, nullable=True,
                        comment="法會編號，格式：RTL-YYYY-MM，自動產生")
    title = Column(String(100), nullable=False, comment="法會名稱，如：四月份地藏經法會")
    ritual_date = Column(Date, nullable=False, comment="法會日期")
    weekday = Column(String(10), nullable=True, comment="星期幾，如：週日")
    start_time = Column(String(10), nullable=False, comment="開始時間，如：09:00")
    end_time = Column(String(10), nullable=False, comment="結束時間，如：12:00")
    location = Column(String(100), nullable=False, comment="地點，如：新竹大佛禪寺")

    # --- Admin.vue 容量管理 ---
    capacity = Column(Integer, default=50, comment="最大人數")
    registered_count = Column(Integer, default=0, comment="已報名人數（快取，避免每次 COUNT）")

    # --- 法會資訊 ---
    description = Column(Text, nullable=True, comment="法會說明")
    fee = Column(Numeric(10, 2), default=1800, comment="報名費用")
    status = Column(Enum(RitualStatus), default=RitualStatus.upcoming, comment="法會狀態")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 關聯
    registrations = relationship("RitualRegistration", back_populates="ritual")

    def __repr__(self):
        return f"<Ritual {self.ritual_id} {self.title} {self.ritual_date}>"


# ========================================
# RitualRegistration（法會報名）
# 來源：Admin.vue 法會管理（查看報名名單）
# ========================================

class RitualRegistration(Base):
    __tablename__ = "ritual_registrations"

    id = Column(Integer, primary_key=True, index=True)
    ritual_id = Column(Integer, ForeignKey("rituals.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True,
                        comment="對應的訂單（若為付費報名）")

    will_attend = Column(Boolean, default=True,
                            comment="是否親自出席（False = 委託代參）")
    
    # 💡 升級為 JSON 欄位：未來管理後台可以極度精準地用 [1, 2] 陣列關聯多隻 Pet 的實體 ID
    # 如果前端傳字串過來，後端寫入前做個 .split(",") 轉成 list 存進去即可，長遠看彈性大非常多！
    pet_ids = Column(JSON, nullable=True, comment="本次為哪些毛孩迴向（存入寵物 ID 陣列，如 [1, 3]）")
    notes = Column(Text, nullable=True, comment="備註")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 關聯
    ritual = relationship("Ritual", back_populates="registrations")
    user = relationship("User", back_populates="ritual_registrations")

    def __repr__(self):
        return f"<RitualRegistration ritual={self.ritual_id} user={self.user_id}>"