"""Tests for core data contracts — serialization, immutability, round-trip."""

from __future__ import annotations

import json

import numpy as np
import pytest
from pydantic import ValidationError

from ds_data_miner.core.contracts import (
    CategoricalProfile,
    CategoryStats,
    DatasetReport,
    DatetimeProfile,
    DistributionProfile,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_distribution_profile(**overrides: object) -> DistributionProfile:
    defaults = dict(
        mean=0.0,
        variance=1.0,
        std=1.0,
        skewness=0.0,
        kurtosis=0.0,
        median=0.0,
        min=-3.0,
        max=3.0,
        q25=-0.67,
        q75=0.67,
        sem=0.01,
        ci_lower=-0.02,
        ci_upper=0.02,
        histogram_bin_edges=[0.0, 1.0, 2.0],
        histogram_counts=[5, 10],
        n_samples=100,
        n_valid=100,
        missing_count=0,
        missing_ratio=0.0,
        inf_count=0,
    )
    defaults.update(overrides)
    return DistributionProfile(**defaults)


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_distribution_profile_is_frozen(self) -> None:
        profile = _make_distribution_profile()
        with pytest.raises(ValidationError):
            profile.mean = 999.0  # type: ignore[misc]

    def test_category_stats_is_frozen(self) -> None:
        stats = CategoryStats(
            category="A",
            count=10,
            proportion=0.5,
            std_error=0.05,
        )
        with pytest.raises(ValidationError):
            stats.count = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# JSON Serialization
# ---------------------------------------------------------------------------


class TestJsonSerialization:
    def test_distribution_profile_to_json(self) -> None:
        profile = _make_distribution_profile()
        json_str = profile.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["mean"] == 0.0
        assert parsed["n_samples"] == 100

    def test_nan_serialized_as_null(self) -> None:
        """NaN must become JSON null, not the string 'NaN'."""
        profile = _make_distribution_profile(mean=float("nan"))
        json_str = profile.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["mean"] is None

    def test_inf_serialized_as_null(self) -> None:
        """Inf must become JSON null."""
        profile = _make_distribution_profile(variance=float("inf"))
        json_str = profile.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["variance"] is None

    def test_negative_inf_serialized_as_null(self) -> None:
        profile = _make_distribution_profile(min=float("-inf"))
        json_str = profile.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["min"] is None

    def test_numpy_types_convert_to_native(self) -> None:
        """np.float64 / np.int64 must serialize as native JSON numbers."""
        profile = _make_distribution_profile(
            mean=np.float64(1.5),
            n_samples=np.int64(200),
        )
        json_str = profile.model_dump_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed["mean"], float)
        assert isinstance(parsed["n_samples"], int)


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_distribution_profile_round_trip(self) -> None:
        original = _make_distribution_profile()
        json_str = original.model_dump_json()
        restored = DistributionProfile.model_validate_json(json_str)
        assert restored == original

    def test_categorical_profile_round_trip(self) -> None:
        original = CategoricalProfile(
            stats=[
                CategoryStats(category="A", count=10, proportion=0.5, std_error=0.05),
                CategoryStats(category="B", count=10, proportion=0.5, std_error=0.05),
            ],
            n_total=20,
            n_unique=2,
            missing_count=0,
            missing_ratio=0.0,
            is_high_cardinality=False,
        )
        json_str = original.model_dump_json()
        restored = CategoricalProfile.model_validate_json(json_str)
        assert restored == original

    def test_datetime_profile_round_trip(self) -> None:
        original = DatetimeProfile(
            start="2024-01-01T00:00:00",
            end="2024-01-02T00:00:00",
            duration_seconds=86400.0,
            is_monotonic_increasing=True,
            gap_count=0,
            gap_locations=[],
            inferred_freq="1min",
            n_samples=1440,
            missing_count=0,
            missing_ratio=0.0,
        )
        json_str = original.model_dump_json()
        restored = DatetimeProfile.model_validate_json(json_str)
        assert restored == original

    def test_dataset_report_round_trip(self) -> None:
        report = DatasetReport(
            dataset_name="test",
            created_at="2024-01-01T00:00:00Z",
            ds_data_miner_version="0.1.0",
            total_rows=100,
            total_columns=1,
            duplicate_row_count=0,
            duplicate_row_ratio=0.0,
            columns={
                "col1": _make_distribution_profile(),
            },
        )
        json_str = report.model_dump_json()
        restored = DatasetReport.model_validate_json(json_str)
        assert restored.dataset_name == "test"
        assert "col1" in restored.columns
