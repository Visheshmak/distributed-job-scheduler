import pytest
from app.models.enums import RetryStrategy
from app.services.retry_math import RetryCalculator


def test_fixed_delay_calculation():
    delay = RetryCalculator.calculate_delay_ms(
        attempt=1,
        strategy=RetryStrategy.FIXED,
        base_delay_ms=2000,
        jitter_factor=0.0
    )
    assert delay == 2000

    delay_attempt_3 = RetryCalculator.calculate_delay_ms(
        attempt=3,
        strategy=RetryStrategy.FIXED,
        base_delay_ms=2000,
        jitter_factor=0.0
    )
    assert delay_attempt_3 == 2000


def test_linear_delay_calculation():
    d1 = RetryCalculator.calculate_delay_ms(attempt=1, strategy=RetryStrategy.LINEAR, base_delay_ms=1000, jitter_factor=0.0)
    d2 = RetryCalculator.calculate_delay_ms(attempt=2, strategy=RetryStrategy.LINEAR, base_delay_ms=1000, jitter_factor=0.0)
    d3 = RetryCalculator.calculate_delay_ms(attempt=3, strategy=RetryStrategy.LINEAR, base_delay_ms=1000, jitter_factor=0.0)

    assert d1 == 1000
    assert d2 == 2000
    assert d3 == 3000


def test_exponential_delay_calculation():
    d1 = RetryCalculator.calculate_delay_ms(attempt=1, strategy=RetryStrategy.EXPONENTIAL, base_delay_ms=1000, jitter_factor=0.0)
    d2 = RetryCalculator.calculate_delay_ms(attempt=2, strategy=RetryStrategy.EXPONENTIAL, base_delay_ms=1000, jitter_factor=0.0)
    d3 = RetryCalculator.calculate_delay_ms(attempt=3, strategy=RetryStrategy.EXPONENTIAL, base_delay_ms=1000, jitter_factor=0.0)
    d4 = RetryCalculator.calculate_delay_ms(attempt=4, strategy=RetryStrategy.EXPONENTIAL, base_delay_ms=1000, jitter_factor=0.0)

    assert d1 == 1000  # 1000 * 2^0
    assert d2 == 2000  # 1000 * 2^1
    assert d3 == 4000  # 1000 * 2^2
    assert d4 == 8000  # 1000 * 2^3


def test_max_delay_cap():
    delay = RetryCalculator.calculate_delay_ms(
        attempt=10,
        strategy=RetryStrategy.EXPONENTIAL,
        base_delay_ms=1000,
        max_delay_ms=15000,
        jitter_factor=0.0
    )
    assert delay == 15000


def test_jitter_bounds():
    for _ in range(20):
        delay = RetryCalculator.calculate_delay_ms(
            attempt=2,
            strategy=RetryStrategy.EXPONENTIAL,
            base_delay_ms=1000,
            jitter_factor=0.2
        )
        # Raw is 2000, with 0.2 jitter range is [1600, 2400]
        assert 1600 <= delay <= 2400


def test_retry_exhaustion():
    assert not RetryCalculator.is_exhausted(attempt_count=1, max_retries=3)
    assert not RetryCalculator.is_exhausted(attempt_count=2, max_retries=3)
    assert RetryCalculator.is_exhausted(attempt_count=3, max_retries=3)
    assert RetryCalculator.is_exhausted(attempt_count=4, max_retries=3)
