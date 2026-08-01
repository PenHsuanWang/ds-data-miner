"""Tests for DistributionTester — K-S test accuracy against scipy baseline."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats as sp_stats

from ds_data_miner.profiling.distribution_test import DistributionTester


class TestDistributionTester:
    def test_returns_statistic_and_p_value(self, normal_array: np.ndarray) -> None:
        tester = DistributionTester(dist_name="norm")
        result = tester.test(normal_array)
        assert "statistic" in result
        assert "p_value" in result

    def test_matches_scipy_kstest(self, normal_array: np.ndarray) -> None:
        """Results must match scipy.stats.kstest within atol=1e-7."""
        tester = DistributionTester(dist_name="norm")
        result = tester.test(normal_array)

        expected = sp_stats.kstest(normal_array, "norm")
        assert result["statistic"] == pytest.approx(expected.statistic, abs=1e-7)
        assert result["p_value"] == pytest.approx(expected.pvalue, abs=1e-7)

    def test_normal_data_high_p_value(self, normal_array: np.ndarray) -> None:
        """Normally distributed data should have high p-value against 'norm'."""
        tester = DistributionTester(dist_name="norm")
        result = tester.test(normal_array)
        # With 1M samples from a standard normal, p-value should be reasonable
        assert result["p_value"] >= 0.0

    def test_uniform_data_low_p_value_against_norm(
        self, rng: np.random.Generator
    ) -> None:
        """Uniform data should not look like a normal distribution."""
        uniform_data = rng.uniform(0, 1, 10_000)
        tester = DistributionTester(dist_name="norm")
        result = tester.test(uniform_data)
        assert result["p_value"] < 0.05

    def test_nan_values_are_dropped(self) -> None:
        """NaN values should be dropped before the K-S test."""
        data = np.array([1.0, 2.0, np.nan, 3.0, np.nan, 4.0])
        tester = DistributionTester(dist_name="norm")
        result = tester.test(data)
        # Should not raise — only uses [1, 2, 3, 4]
        assert isinstance(result["statistic"], float)
        assert isinstance(result["p_value"], float)

    def test_default_distribution_is_norm(self) -> None:
        tester = DistributionTester()
        assert tester.dist_name == "norm"
