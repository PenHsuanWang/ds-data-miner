"""Tests for DatetimeProfiler — monotonicity, gaps, frequency inference."""

from __future__ import annotations

import numpy as np
import pytest

from ds_data_miner.core.contracts import DatetimeProfile
from ds_data_miner.core.exceptions import DataQualityError
from ds_data_miner.profiling.datetime import DatetimeProfiler


class TestDatetimeProfilerBasics:
    def test_returns_datetime_profile(self, datetime_array: np.ndarray) -> None:
        profiler = DatetimeProfiler()
        result = profiler.fit(datetime_array)
        assert isinstance(result, DatetimeProfile)

    def test_monotonic_regular_array(self, datetime_array: np.ndarray) -> None:
        profiler = DatetimeProfiler()
        result = profiler.fit(datetime_array)
        assert result.is_monotonic_increasing is True
        assert result.n_samples == 1000

    def test_inferred_freq_1min(self, datetime_array: np.ndarray) -> None:
        profiler = DatetimeProfiler()
        result = profiler.fit(datetime_array)
        assert result.inferred_freq == "1min"


class TestGapDetection:
    def test_gaps_detected(self, datetime_with_gaps: np.ndarray) -> None:
        profiler = DatetimeProfiler(gap_threshold_factor=2.0)
        result = profiler.fit(datetime_with_gaps)
        assert result.gap_count == 2
        assert len(result.gap_locations) == 2

    def test_gap_locations_have_required_keys(
        self,
        datetime_with_gaps: np.ndarray,
    ) -> None:
        profiler = DatetimeProfiler()
        result = profiler.fit(datetime_with_gaps)
        for gap in result.gap_locations:
            assert "from" in gap
            assert "to" in gap
            assert "duration_seconds" in gap

    def test_no_gaps_in_regular_array(self, datetime_array: np.ndarray) -> None:
        profiler = DatetimeProfiler()
        result = profiler.fit(datetime_array)
        assert result.gap_count == 0


class TestEdgeCases:
    def test_empty_array_raises(self) -> None:
        profiler = DatetimeProfiler()
        with pytest.raises(DataQualityError, match="empty"):
            profiler.fit(np.array([], dtype="datetime64[ns]"))

    def test_all_nat_raises(self) -> None:
        profiler = DatetimeProfiler()
        data = np.array(["NaT", "NaT", "NaT"], dtype="datetime64[ns]")
        with pytest.raises(DataQualityError, match="NaT"):
            profiler.fit(data)

    def test_non_datetime_raises(self) -> None:
        profiler = DatetimeProfiler()
        with pytest.raises(TypeError, match="datetime64"):
            profiler.fit(np.array([1, 2, 3]))

    def test_nat_counted_as_missing(self) -> None:
        base = np.datetime64("2024-01-01T00:00:00")
        data = np.array(
            [
                base,
                base + np.timedelta64(1, "m"),
                np.datetime64("NaT"),
                base + np.timedelta64(3, "m"),
            ]
        )
        profiler = DatetimeProfiler()
        result = profiler.fit(data)
        assert result.missing_count == 1
        assert result.missing_ratio == pytest.approx(0.25)

    def test_non_monotonic_detected(self) -> None:
        base = np.datetime64("2024-01-01T00:00:00")
        data = np.array(
            [
                base + np.timedelta64(2, "m"),
                base,
                base + np.timedelta64(1, "m"),
            ]
        )
        profiler = DatetimeProfiler()
        result = profiler.fit(data)
        assert result.is_monotonic_increasing is False
