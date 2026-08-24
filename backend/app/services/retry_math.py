import random
from typing import Optional
from app.models.enums import RetryStrategy
from app.models.retry_policy import RetryPolicy


class RetryCalculator:
    """Calculates backoff delays for failed jobs and evaluates exhaustion."""

    @staticmethod
    def calculate_delay_ms(
        attempt: int,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        base_delay_ms: int = 1000,
        max_delay_ms: int = 60000,
        jitter_factor: float = 0.2,
    ) -> int:
        """
        Calculates retry delay in milliseconds based on attempt number and strategy.
        Attempt is 1-indexed (1st retry attempt, 2nd, etc.)
        """
        if attempt <= 0:
            attempt = 1

        if strategy == RetryStrategy.FIXED:
            delay = float(base_delay_ms)
        elif strategy == RetryStrategy.LINEAR:
            delay = float(base_delay_ms * attempt)
        elif strategy == RetryStrategy.EXPONENTIAL:
            multiplier = 2 ** (attempt - 1)
            delay = float(base_delay_ms * multiplier)
        else:
            delay = float(base_delay_ms)

        # Cap at max_delay_ms
        delay = min(delay, float(max_delay_ms))

        # Apply Jitter (Full / Decorrelated / Proportional)
        if jitter_factor > 0.0:
            # Full Jitter formula: uniformly distributed between [delay * (1 - jitter), delay * (1 + jitter)]
            # or randomized between [0, delay] for full jitter.
            min_bound = max(0.0, delay * (1.0 - jitter_factor))
            max_bound = min(float(max_delay_ms), delay * (1.0 + jitter_factor))
            delay = random.uniform(min_bound, max_bound)

        return int(max(0, delay))

    @classmethod
    def calculate_for_policy(cls, attempt: int, policy: Optional[RetryPolicy]) -> int:
        if not policy:
            return cls.calculate_delay_ms(
                attempt=attempt,
                strategy=RetryStrategy.EXPONENTIAL,
                base_delay_ms=2000,
                max_delay_ms=60000,
                jitter_factor=0.2
            )
        return cls.calculate_delay_ms(
            attempt=attempt,
            strategy=policy.strategy,
            base_delay_ms=policy.base_delay_ms,
            max_delay_ms=policy.max_delay_ms,
            jitter_factor=policy.jitter_factor
        )

    @staticmethod
    def is_exhausted(attempt_count: int, max_retries: int) -> bool:
        """Returns True if attempt count has reached or exceeded max configured retries."""
        return attempt_count >= max_retries
