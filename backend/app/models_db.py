"""
models_db.py — SQLAlchemy table definitions.

(Named models_db.py, not models.py, to avoid confusion with the
models/ folder holding trained ML artifacts — different kind of
"model" entirely.)
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    checks = relationship("CheckHistory", back_populates="user")


class CheckHistory(Base):
    __tablename__ = "check_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # nullable: guests can check too
    url = Column(String(2048), nullable=False)
    model = Column(String(50), nullable=False)
    verdict = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="checks")