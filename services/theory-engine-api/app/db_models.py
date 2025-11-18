"""SQLAlchemy models for dock108 theory engine persistence."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class UserTier(str, Enum):
    """User subscription tier levels."""

    free = "free"
    silver = "silver"
    gold = "gold"
    unlimited = "unlimited"


class CustomerAccount(Base):
    """User/customer account table."""

    __tablename__ = "customer_accounts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tier: Mapped[UserTier] = mapped_column(String(20), default=UserTier.free, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    theories: Mapped[list[Theory]] = relationship("Theory", back_populates="user", cascade="all, delete-orphan")


class Theory(Base):
    """Stored theory submissions."""

    __tablename__ = "theories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("customer_accounts.id"), nullable=True, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user: Mapped[CustomerAccount | None] = relationship("CustomerAccount", back_populates="theories")
    evaluations: Mapped[list[Evaluation]] = relationship("Evaluation", back_populates="theory", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_theories_domain_created", "domain", "created_at"),)


class Evaluation(Base):
    """Evaluation results for a theory."""

    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    theory_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("theories.id"), nullable=False, index=True)
    verdict: Mapped[str] = mapped_column(String(200), nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    long_term_outcome_example: Mapped[str] = mapped_column(Text, nullable=False)
    guardrail_flags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    used_models: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    theory: Mapped[Theory] = relationship("Theory", back_populates="evaluations")

    __table_args__ = (Index("idx_evaluations_theory_created", "theory_id", "created_at"),)


class ContextType(str, Enum):
    """Types of external context cached."""

    youtube = "youtube"
    odds = "odds"
    crypto_price = "crypto_price"
    stock_price = "stock_price"
    play_by_play = "play_by_play"


class ExternalContextCache(Base):
    """Cache layer for external API responses (YouTube, odds, prices, etc.)."""

    __tablename__ = "external_context_cache"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    context_type: Mapped[ContextType] = mapped_column(String(50), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256 of query params
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("idx_context_type_hash", "context_type", "key_hash", unique=True),
        Index("idx_context_expires", "expires_at"),
    )

