"""
Numeric column profiler — full-scan statistical feature extraction.

Computes basic statistics, statistical errors (SEM, CI), and a pre-computed
histogram representation.  All operations are vectorised via NumPy / SciPy —
no Python loops, no sampling.

**Agent Usage Decision Tree**

Use :class:`NumericProfiler` when:

- The input column has ``numpy.number`` dtype (int, float, complex).
- You need any of: mean, std, skewness, kurtosis, quantiles, SEM, CI,
  missing-value ratio, or a pre-computed histogram for downstream plotting.

Do **not** use when:

- The column contains strings or categories → use :class:`CategoricalProfiler`.
- The column contains timestamps → use :class:`DatetimeProfiler`.
- You have a full :class:`pandas.DataFrame` → use :class:`~ds_data_miner.pandas_ext.accessor.MinerAccessor`.
"""

from __future__ import annotations

import numpy as np
from scipy import stats as sp_stats

from ds_data_miner.core.contracts import DistributionProfile
from ds_data_miner.core.exceptions import DataQualityError
from ds_data_miner.profiling.base import BaseProfiler


class NumericProfiler(BaseProfiler):
    """Profile numeric (int / float) columns via full-scan vectorised ops.

    Performs a single-pass full table scan over the input array using
    ``numpy`` and ``scipy`` — never samples, never iterates with Python loops.

    **Input Requirements**

    - 1-D array or any array that can be flattened via ``ravel()``.
    - Dtype must be castable to ``float64`` (int, float, bool).
    - NaN and Inf values are handled according to ``ignore_nan`` and are
      excluded from all statistical calculations.

    **Output** — a frozen :class:`~ds_data_miner.core.contracts.DistributionProfile`
    containing:

    - Descriptive stats: ``mean``, ``variance``, ``std``, ``median``,
      ``min``, ``max``, ``q25``, ``q75``, ``skewness``, ``kurtosis``
    - Statistical errors: ``sem`` (Standard Error of the Mean),
      ``ci_lower`` / ``ci_upper`` (confidence interval bounds)
    - Pre-computed histogram: ``histogram_bin_edges``, ``histogram_counts``
    - Quality metadata: ``n_samples``, ``n_valid``, ``missing_count``,
      ``missing_ratio``, ``inf_count``

    :param ignore_nan: If ``True`` (default), NaN values are silently dropped
        before computing statistics and counted in ``missing_count``.
        If ``False``, raises :class:`~ds_data_miner.core.exceptions.DataQualityError`
        on any NaN.
    :param ci_level: Confidence level for the symmetric confidence interval
        around the mean.  Must be in ``(0, 1)``.  Default ``0.95`` (95% CI).
    :param n_bins: Number of histogram bins passed to ``numpy.histogram``.
        Use ``\"auto\"`` for NumPy's automatic bin-count selection (default).

    Example::

        import numpy as np
        from ds_data_miner.profiling.numeric import NumericProfiler

        rng = np.random.default_rng(42)
        data = rng.standard_normal(1_000_000)

        profile = NumericProfiler(ignore_nan=True, ci_level=0.95).fit(data)

        print(profile.mean)          # ≈ 0.0
        print(profile.sem)           # ≈ 0.001
        print(profile.ci_lower)      # lower 95% CI bound
        print(profile.ci_upper)      # upper 95% CI bound
        print(profile.missing_ratio) # 0.0
        print(profile.model_dump_json(indent=2))  # full JSON output

    .. note::
        The returned :class:`~ds_data_miner.core.contracts.DistributionProfile`
        is **frozen** (immutable).  NaN / Inf values serialize as JSON ``null``
        automatically.
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

        Runs a complete vectorised scan over *data*, computes all statistics,
        and returns a frozen :class:`~ds_data_miner.core.contracts.DistributionProfile`.

        :param data: 1-D NumPy array of numeric dtype.  Multi-dimensional
            arrays are automatically flattened via ``ravel()``.
        :return: Frozen :class:`~ds_data_miner.core.contracts.DistributionProfile`
            with all computed statistics.
        :raises TypeError: If *data* cannot be cast to ``float64``
            (e.g., an array of strings).
        :raises DataQualityError: If *data* is empty, entirely NaN/Inf,
            or contains NaN when ``ignore_nan=False``.

        Example — basic usage::

            profile = NumericProfiler().fit(np.array([1.0, 2.0, 3.0, np.nan]))
            assert profile.n_samples == 4
            assert profile.missing_count == 1
            assert profile.n_valid == 3

        Example — reading the histogram for downstream plotting::

            edges = profile.histogram_bin_edges   # list[float], length = n_bins + 1
            counts = profile.histogram_counts     # list[int],   length = n_bins
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
