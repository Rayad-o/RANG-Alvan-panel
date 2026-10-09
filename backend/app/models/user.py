import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    # پنل مدیریتی (داشبورد)
    admin = "admin"
    manager = "manager"
    staff = "staff"
    # پنل خریدار
    buyer = "buyer"
    # پنل کارگران
    accountant = "accountant"    # حسابدار
    dept_head = "dept_head"      # رییس بخش
    dept_staff = "dept_staff"    # کارکن بخش


# نقش‌هایی که به داشبورد مدیریتی (فروش، مالی، کنترل و ریسک) دسترسی دارند
INTERNAL_ROLES = (UserRole.admin.value, UserRole.manager.value, UserRole.staff.value)
# نقش‌هایی که حتماً باید به یک بخش تعلق داشته باشند
DEPARTMENT_ROLES = (UserRole.dept_head.value, UserRole.dept_staff.value)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    # native_enum=False: به‌جای نوع enum دیتابیس از VARCHAR استفاده می‌شود تا افزودن نقش جدید نیاز به migration نداشته باشد
    role = Column(Enum(UserRole, native_enum=False, length=30), default=UserRole.staff, nullable=False)
    # نام بخش برای رییس/کارکن بخش (از فهرست بخش‌ها)
    department = Column(String(100), nullable=True)
