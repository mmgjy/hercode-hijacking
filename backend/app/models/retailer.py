from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._common import created_at_column, pk_column


class Retailer(Base):
    __tablename__ = "retailers"

    id: Mapped[str] = pk_column()
    key: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String)
    domain: Mapped[str | None] = mapped_column(String)
    market: Mapped[str | None] = mapped_column(String)
    adapter_key: Mapped[str | None] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created_at_column()
