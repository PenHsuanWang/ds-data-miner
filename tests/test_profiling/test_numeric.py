"""Tests for NumericProfiler — accuracy, SEM/CI, edge cases."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats as sp_stats

from ds_data_miner.core.contracts import DistributionProfile
from ds_data_miner.core.exceptions import DataQualityError
from ds_data_miner.profiling.numeric import NumericProfiler


class TestNumericProfilerBasics:
    def test_returns_distribution_profile(self, normal_array: np.ndarray) -> None:
        profiler = NumericProfiler()
        result = profiler.fit(normal_array)
        assert isinstance(result, DistributionProfile)

    def test_basic_stats_accuracy(self, normal_array: np.ndarray) -> None:
        """Stats must match NumPy/SciPy baselines within atol=1e-7."""
        profiler = NumericProfiler()
        result = profiler.fit(normal_array)

        assert result.mean == pytest.approx(float(np.mean(normal_array)), abs=1e-7)
        assert result.variance == pytest.approx(float(np.var(normal_array)), abs=1e-7)
        assert result.std == pytest.approx(float(np.std(normal_array)), abs=1e-7)
        assert result.median == pytest.approx(float(np.median(normal_array)), abs=1e-7)
        assert result.min == pytest.approx(float(np.min(normal_array)), abs=1e-7)
        assert result.max == pytest.approx(float(np.max(normal_array)), abs=1e-7)

    def test_skewness_kurtosis_match_scipy(self, normal_array: np.ndarray) -> None:
        profiler = NumericProfiler()
        result = profiler.fit(normal_array)

        expected_skew = float(sp_stats.skew(normal_array, bias=False))
        expected_kurt = float(sp_stats.kurtosis(normal_array, bias=False))

        assert result.skewness == pytest.approx(expected_skew, abs=1e-7)
        assert result.kurtosis == pytest.approx(expected_kurt, abs=1e-7)

    def test_no_raw_array_stored(self, normal_array: np.ndarray) -> None:
        """Profile must not store the raw input array."""
        profiler = NumericProfiler()
        result = profiler.fit(normal_array)
        # The histogram bins + counts are lists, not the raw array
        assert isinstance(result.histogram_bin_edges, list)
        assert isinstance(result.histogram_counts, list)
        assert len(result.histogram_counts) == len(result.histogram_bin_edges) - 1


class TestStatisticalErrors:
    def test_sem_calculation(self, normal_array: np.ndarray) -> None:
        profiler = NumericProfiler()
        result = profiler.fit(normal_array)

        std_ddof1 = float(np.std(normal_array, ddof=1))
        expected_sem = std_ddof1 / np.sqrt(len(normal_array))
        assert result.sem == pytest.approx(expected_sem, abs=1e-7)

    def test_ci_contains_mean(self, normal_array: np.ndarray) -> None:
        profiler = NumericProfiler(ci_level=0.95)
        result = profiler.fit(normal_array)
        assert result.ci_lower <= result.mean <= result.ci_upper


class TestNanHandling:
    def test_ignore_nan_true(self, normal_with_nan: np.ndarray) -> None:
        profiler = NumericProfiler(ignore_nan=True)
        result = profiler.fit(normal_with_nan)
        assert result.missing_count > 0
        assert result.missing_ratio > 0.0
        assert result.n_valid < result.n_samples

    def test_ignore_nan_false_raises(self, normal_with_nan: np.ndarray) -> None:
        profiler = NumericProfiler(ignore_nan=False)
        with pytest.raises(DataQualityError, match="NaN"):
            profiler.fit(normal_with_nan)

    def test_all_nan_raises(self) -> None:
        profiler = NumericProfiler(ignore_nan=True)
        with pytest.raises(DataQualityError, match="No valid"):
            profiler.fit(np.array([np.nan, np.nan, np.nan]))

    def test_empty_array_raises(self) -> None:
        profiler = NumericProfiler()
        with pytest.raises(DataQualityError, match="empty"):
            profiler.fit(np.array([]))


class TestInfHandling:
    def test_inf_counted(self) -> None:
        data = np.array([1.0, 2.0, np.inf, -np.inf, 3.0])
        profiler = NumericProfiler()
        result = profiler.fit(data)
        assert result.inf_count == 2
        assert result.n_valid == 3  # 1.0, 2.0, 3.0
