"""Tests for CategoricalProfiler — proportions, std_error, high cardinality."""

from __future__ import annotations

import warnings

import numpy as np
import pytest

from ds_data_miner.core.contracts import CategoricalProfile
from ds_data_miner.core.exceptions import DataQualityError, HighCardinalityWarning
from ds_data_miner.profiling.categorical import CategoricalProfiler


class TestCategoricalProfilerBasics:
    def test_returns_categorical_profile(
        self,
        categorical_array: np.ndarray,
    ) -> None:
        profiler = CategoricalProfiler()
        result = profiler.fit(categorical_array)
        assert isinstance(result, CategoricalProfile)

    def test_counts_and_proportions(self) -> None:
        data = np.array(["A", "A", "B", "B", "B"])
        profiler = CategoricalProfiler()
        result = profiler.fit(data)

        stats_map = {s.category: s for s in result.stats}
        assert stats_map["A"].count == 2
        assert stats_map["A"].proportion == pytest.approx(0.4)
        assert stats_map["B"].count == 3
        assert stats_map["B"].proportion == pytest.approx(0.6)

    def test_binomial_std_error(self) -> None:
        data = np.array(["A"] * 40 + ["B"] * 60)
        profiler = CategoricalProfiler()
        result = profiler.fit(data)

        stats_map = {s.category: s for s in result.stats}
        p = 0.4
        n = 100
        expected_se = float(np.sqrt(p * (1 - p) / n))
        assert stats_map["A"].std_error == pytest.approx(expected_se, abs=1e-5)

    def test_n_unique(self, categorical_array: np.ndarray) -> None:
        profiler = CategoricalProfiler()
        result = profiler.fit(categorical_array)
        assert result.n_unique == 4  # A, B, C, D

    def test_empty_array_raises(self) -> None:
        profiler = CategoricalProfiler()
        with pytest.raises(DataQualityError, match="empty"):
            profiler.fit(np.array([]))


class TestHighCardinalityDefense:
    def test_truncation_fires_warning(
        self,
        high_cardinality_array: np.ndarray,
    ) -> None:
        profiler = CategoricalProfiler(max_cardinality=10)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = profiler.fit(high_cardinality_array)
            assert any(issubclass(x.category, HighCardinalityWarning) for x in w)

        assert result.is_high_cardinality is True
        assert result.truncated_at == 10

    def test_truncated_has_other_bucket(
        self,
        high_cardinality_array: np.ndarray,
    ) -> None:
        profiler = CategoricalProfiler(max_cardinality=10)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", HighCardinalityWarning)
            result = profiler.fit(high_cardinality_array)

        categories = [s.category for s in result.stats]
        assert "_OTHER_" in categories
        # Top-10 + _OTHER_ = 11
        assert len(result.stats) == 11

    def test_no_truncation_below_threshold(
        self,
        categorical_array: np.ndarray,
    ) -> None:
        profiler = CategoricalProfiler(max_cardinality=100)
        result = profiler.fit(categorical_array)
        assert result.is_high_cardinality is False
        assert result.truncated_at is None


class TestMissingValues:
    def test_none_counted_as_missing(self) -> None:
        data = np.array(["A", "B", None, "A", None], dtype=object)
        profiler = CategoricalProfiler()
        result = profiler.fit(data)
        assert result.missing_count == 2
        assert result.missing_ratio == pytest.approx(0.4, abs=1e-5)
        assert result.n_total == 3
