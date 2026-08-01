"""
Distribution tester — standalone statistical hypothesis testing utility.

This is **not** a profiler; it does not inherit from :class:`BaseProfiler`.
It is a lightweight helper that wraps ``scipy.stats`` tests and returns
structured results suitable for embedding into a :class:`DistributionProfile`.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy import stats as sp_stats


class DistributionTester:
    """Test whether data follows a specified distribution.

    :param dist_name: Name of the distribution to test against.
        Must be a valid ``scipy.stats`` continuous distribution name
        (e.g. ``"norm"``, ``"expon"``, ``"uniform"``).
    """

    def __init__(self, dist_name: str = "norm") -> None:
        self.dist_name = dist_name

    def test(self, data: NDArray[Any]) -> dict[str, float]:
        """Run a Kolmogorov-Smirnov test against the target distribution.

        :param data: 1-D numeric array (NaN/Inf values are dropped).
        :return: ``{"statistic": float, "p_value": float}``.
        """
        clean = data[np.isfinite(data)]
        result = sp_stats.kstest(clean, self.dist_name)
        return {
            "statistic": float(result.statistic),
            "p_value": float(result.pvalue),
        }
