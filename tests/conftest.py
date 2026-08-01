"""
Shared test fixtures for ds-data-miner.
"""

from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture()
def rng() -> np.random.Generator:
    """Seeded random number generator for reproducible tests."""
    return np.random.default_rng(seed=42)


@pytest.fixture()
def normal_array(rng: np.random.Generator) -> np.ndarray:
    """1M-element normally-distributed float64 array."""
    return rng.standard_normal(1_000_000)


@pytest.fixture()
def normal_with_nan(normal_array: np.ndarray) -> np.ndarray:
    """Normal array with 1% NaN values injected."""
    arr = normal_array.copy()
    n_nan = len(arr) // 100
    arr[:n_nan] = np.nan
    return arr


@pytest.fixture()
def categorical_array() -> np.ndarray:
    """Simple categorical array with 4 categories."""
    return np.array(["A", "B", "C", "A", "B", "A", "C", "D", "A", "B"])


@pytest.fixture()
def high_cardinality_array() -> np.ndarray:
    """Categorical array with 500 unique UUIDs."""
    return np.array([f"uuid-{i:04d}" for i in range(500)])


@pytest.fixture()
def datetime_array() -> np.ndarray:
    """Regular 1-minute interval datetime64 array."""
    base = np.datetime64("2024-01-01T00:00:00")
    return base + np.arange(1000) * np.timedelta64(1, "m")


@pytest.fixture()
def datetime_with_gaps() -> np.ndarray:
    """Datetime array with 2 intentional gaps."""
    base = np.datetime64("2024-01-01T00:00:00")
    part1 = base + np.arange(100) * np.timedelta64(1, "m")
    # 10-hour gap
    part2 = (
        part1[-1] + np.timedelta64(10, "h") + np.arange(100) * np.timedelta64(1, "m")
    )
    # 2-day gap
    part3 = part2[-1] + np.timedelta64(2, "D") + np.arange(100) * np.timedelta64(1, "m")
    return np.concatenate([part1, part2, part3])
