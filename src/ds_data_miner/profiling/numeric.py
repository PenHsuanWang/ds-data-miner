"""
Numeric column profiler — full-scan statistical feature extraction.

Computes basic statistics, statistical errors (SEM, CI), and a pre-computed
histogram representation.  All operations are vectorised via NumPy / SciPy.
"""

from __future__ import annotations

import numpy as np
from scipy import stats as sp_stats

from ds_data_miner.core.contracts import DistributionProfile
from ds_data_miner.core.exceptions import DataQualityError
from ds_data_miner.profiling.base import BaseProfiler


class NumericProfiler(BaseProfiler):
    """Profile numeric (int / float) columns via full-scan vectorised ops.

    :param ignore_nan: If ``True``, NaN values are silently skipped.
        If ``False``, raises :class:`DataQualityError` on any NaN.
    :param ci_level: Confidence level for the interval (default 0.95).
    :param n_bins: Number of histogram bins, or ``"auto"`` for NumPy's
        automatic selection.
    """

    def __init__(
        self,
        ignore_nan: bool = True,
        ci_level: float = 0.95,
        n_bins: int | str = "auto",
    ) -> None:
        self.ignore_nan = ignore_nan
        self.ci_level = ci_level
        self.n_bins = n_bins

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, data: np.ndarray) -> DistributionProfile:
        """Full-scan profile of a 1-D numeric array.

        :param data: 1-D NumPy array of numeric dtype.
        :return: Frozen :class:`DistributionProfile`.
        :raises TypeError: If *data* is not numeric.
        :raises DataQualityError: If data is entirely NaN or
            contains NaN with ``ignore_nan=False``.
        """
        data = np.asarray(data, dtype=np.float64).ravel()
        n_samples = len(data)

        if n_samples == 0:
            raise DataQualityError("Cannot profile an empty array.")

        # --- Quality metrics ---
        nan_mask = np.isnan(data)
        inf_mask = np.isinf(data)
        missing_count = int(np.count_nonzero(nan_mask))
        inf_count = int(np.count_nonzero(inf_mask))

        if not self.ignore_nan and missing_count > 0:
            raise DataQualityError(
                f"Array contains {missing_count} NaN value(s). "
                "Set ignore_nan=True to skip them."
            )

        # Valid = finite only
        valid_mask = np.isfinite(data)
        valid = data[valid_mask]
        n_valid = len(valid)

        if n_valid == 0:
            raise DataQualityError(
                "No valid (finite) data points after filtering NaN/Inf."
            )

        # --- Basic statistics (vectorised) ---
        mean = float(np.mean(valid))
        variance = float(np.var(valid, ddof=0))
        std = float(np.std(valid, ddof=0))
        median = float(np.median(valid))
        min_val = float(np.min(valid))
        max_val = float(np.max(valid))
        q25, q75 = (float(v) for v in np.percentile(valid, [25, 75]))
        skewness = float(sp_stats.skew(valid, bias=False))
        kurtosis = float(sp_stats.kurtosis(valid, bias=False))

        # --- Statistical errors ---
        std_ddof1 = float(np.std(valid, ddof=1)) if n_valid > 1 else 0.0
        sem = std_ddof1 / np.sqrt(n_valid) if n_valid > 1 else 0.0
        z = float(sp_stats.norm.ppf(1 - (1 - self.ci_level) / 2))
        ci_lower = mean - z * sem
        ci_upper = mean + z * sem

        # --- Histogram (single vectorised call) ---
        counts, bin_edges = np.histogram(valid, bins=self.n_bins)

        # --- Quality ratios ---
        missing_ratio = missing_count / n_samples if n_samples > 0 else 0.0

        return DistributionProfile(
            mean=mean,
            variance=variance,
            std=std,
            skewness=skewness,
            kurtosis=kurtosis,
            median=median,
            min=min_val,
            max=max_val,
            q25=q25,
            q75=q75,
            sem=float(sem),
            ci_lower=float(ci_lower),
            ci_upper=float(ci_upper),
            histogram_bin_edges=bin_edges.tolist(),
            histogram_counts=counts.tolist(),
            n_samples=n_samples,
            n_valid=n_valid,
            missing_count=missing_count,
            missing_ratio=round(missing_ratio, 6),
            inf_count=inf_count,
        )
