from datetime import datetime
from sqlalchemy import (
    BigInteger, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)


class Channel(Base):
    """Majburiy obuna talab qilinadigan kanallar."""
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    invite_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PortfolioItem(Base):
    """Korxona ilgari qilgan ishlar - faqat ko'z-ko'z qilish uchun, narxsiz."""
    __tablename__ = "portfolio_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_file_id: Mapped[str] = mapped_column(String(255))
    style_tags: Mapped[str | None] = mapped_column(String(255), nullable=True)  # "zamonaviy, minimal"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MaterialOption(Base):
    """Admin belgilaydigan xomashyo/rang/zapchast narxlari."""
    __tablename__ = "material_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(32))  # "material" | "color" | "part"
    name: Mapped[str] = mapped_column(String(255))
    extra_price: Mapped[int] = mapped_column(Integer, default=0)  # qo'shimcha narx (so'm)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    portfolio_item_id: Mapped[int | None] = mapped_column(ForeignKey("portfolio_items.id"), nullable=True)

    width_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    depth_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)

    selected_option_ids: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    ai_estimated_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agreed_price: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # new -> reviewing -> confirmed -> in_production -> ready -> delivered -> cancelled
    status: Mapped[str] = mapped_column(String(24), default="new")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship()
    portfolio_item: Mapped["PortfolioItem"] = relationship()
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")


class Setting(Base):
    """Admin sozlaydigan umumiy parametrlar (masalan: 1 m² uchun bazaviy narx)."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    amount: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    order: Mapped["Order"] = relationship(back_populates="payments")
