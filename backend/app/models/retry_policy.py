from sqlalchemy import String, Integer, BigInteger, Float, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.models.enums import RetryStrategy


class RetryPolicy(BaseModel):
    __tablename__ = "retry_policies"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    strategy: Mapped[RetryStrategy] = mapped_column(
        Enum(RetryStrategy, name="retry_strategy_enum", native_enum=False),
        default=RetryStrategy.EXPONENTIAL,
        nullable=False
    )
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    base_delay_ms: Mapped[int] = mapped_column(BigInteger, default=1000, nullable=False)
    max_delay_ms: Mapped[int] = mapped_column(BigInteger, default=60000, nullable=False)
    jitter_factor: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
