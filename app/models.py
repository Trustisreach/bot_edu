# app/models.py
from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(50))
    technology: Mapped[str | None] = mapped_column(String(100), nullable=True)
    s3_key: Mapped[str] = mapped_column(String(500))
    price: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    transaction_id: Mapped[str] = mapped_column(String(100))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    check_count: Mapped[int] = mapped_column(Integer, default=0)  # счётчик проверок
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)