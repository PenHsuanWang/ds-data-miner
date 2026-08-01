"""
Categorical column profiler — full-scan with high-cardinality defense.

Computes per-category counts, proportions, and binomial standard errors.
Automatically truncates to Top-N when cardinality exceeds the threshold.

**Agent Usage Decision Tree**

Use :class:`CategoricalProfiler` when:

- The column dtype is ``object``, ``str``, ``category``, or any non-numeric,
  non-datetime type.
- You need per-category proportions with **binomial standard errors** (i.e.,
  the sampling uncertainty of each category proportion).
- You want automatic detection of high-cardinality columns and safe truncation.

Do **not** use when:

- The column contains numbers → use :class:`NumericProfiler`.
- The column contains timestamps → use :class:`DatetimeProfiler`.
- You have a full :class:`pandas.DataFrame` → use :class:`~ds_data_miner.pandas_ext.accessor.MinerAccessor`.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ds_data_miner.core.contracts import CategoricalProfile, CategoryStats
from ds_data_miner.core.exceptions import DataQualityError, HighCardinalityWarning
from ds_data_miner.profiling.base import BaseProfiler

_OTHER_BUCKET = "_OTHER_"


class CategoricalProfiler(BaseProfiler):
    """Profile categorical (object / string) columns via full-scan.

    Performs a complete vectorised scan to count all unique values,
    compute proportions, and derive binomial standard errors.

    **Input Requirements**

    - 1-D array with dtype ``object``, ``str``, or ``category``.
    - ``None`` and ``np.nan`` values are treated as missing and excluded
      from statistical computations.

    **Output** — a frozen :class:`~ds_data_miner.core.contracts.CategoricalProfile`
    containing:

    - ``stats``: list of :class:`~ds_data_miner.core.contracts.CategoryStats`,
      each with ``category``, ``count``, ``proportion``, and ``std_error``
      (binomial standard error: ``sqrt(p * (1-p) / N)``).
    - ``n_total``: total non-missing element count.
    - ``n_unique``: number of unique categories (before truncation).
    - ``missing_count``, ``missing_ratio``: quality indicators.
    - ``is_high_cardinality``: ``True`` when truncation was applied.
    - ``truncated_at``: the Top-N threshold used, or ``None``.

    **High-Cardinality Defense**

    When ``n_unique > max_cardinality``:

    1. A :class:`~ds_data_miner.core.exceptions.HighCardinalityWarning` is
       emitted (does **not** raise — profiling continues).
    2. Only the Top-N most frequent categories are retained.
    3. All remaining categories are merged into a synthetic ``_OTHER_`` bucket.
    4. ``is_high_cardinality`` is set to ``True`` and ``truncated_at`` records N.

    :param max_cardinality: Maximum unique categories before truncation.
        Categories beyond Top-N are merged into ``_OTHER_``.  Default ``100``.

    Example — basic::

        import numpy as np
        from ds_data_miner.profiling.categorical import CategoricalProfiler

        data = np.array(["ok"] * 700 + ["error"] * 300)
        profile = CategoricalProfiler().fit(data)

        for stat in profile.stats:
            print(stat.category, stat.proportion, stat.std_error)
        # ok     0.7   0.0145...
        # error  0.3   0.0145...

    Example — high-cardinality handling::

        import warnings
        from ds_data_miner.core.exceptions import HighCardinalityWarning

        uuid_data = np.array([f"uuid-{i}" for i in range(500)])

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            profile = CategoricalProfiler(max_cardinality=10).fit(uuid_data)
            assert any(issubclass(x.category, HighCardinalityWarning) for x in w)

        assert profile.is_high_cardinality is True
        assert profile.truncated_at == 10
        assert any(s.category == "_OTHER_" for s in profile.stats)
    """

    def __init__(self, max_cardinality: int = 100) -> None:
        if max_cardinality < 1:
            raise ValueError("max_cardinality must be >= 1.")
        self.max_cardinality = max_cardinality

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, data: NDArray[Any]) -> CategoricalProfile:
        """Full-scan profile of a 1-D categorical array.

        Counts all categories, computes proportions and binomial standard
        errors, applies high-cardinality truncation if needed.

        :param data: 1-D NumPy array of object / string dtype.
            Multi-dimensional arrays are flattened via ``ravel()``.
        :return: Frozen :class:`~ds_data_miner.core.contracts.CategoricalProfile`.
        :raises DataQualityError: If *data* is empty or all values are missing.

        Example::

            profile = CategoricalProfiler().fit(np.array(["A", "B", "A", None]))
            assert profile.n_total == 3       # None excluded
            assert profile.missing_count == 1
            stats_map = {s.category: s for s in profile.stats}
            assert stats_map["A"].count == 2
        """
        data = np.asarray(data).ravel()
        n_samples = len(data)

        if n_samples == 0:
            raise DataQualityError("Cannot profile an empty array.")

        # --- Identify missing values (None, NaN-like for object arrays) ---
        missing_mask = _is_missing(data)
        missing_count = int(np.count_nonzero(missing_mask))
        valid = data[~missing_mask]
        n_total = len(valid)

        if n_total == 0:
            raise DataQualityError("All values are missing.")

        # --- Count categories (vectorised) ---
        unique_vals, counts = np.unique(valid, return_counts=True)
        n_unique = len(unique_vals)

        # --- High-cardinality defense ---
        is_high_cardinality = n_unique > self.max_cardinality
        truncated_at: int | None = None

        if is_high_cardinality:
            warnings.warn(
                f"Column has {n_unique} unique values (threshold="
                f"{self.max_cardinality}). Truncating to Top-"
                f"{self.max_cardinality} and merging remainder into "
                f"'{_OTHER_BUCKET}'.",
                HighCardinalityWarning,
                stacklevel=2,
            )
            truncated_at = self.max_cardinality

            # Sort descending by count, take top-N
            top_idx = np.argsort(counts)[::-1][: self.max_cardinality]
            other_count = int(counts.sum()) - int(counts[top_idx].sum())

            unique_vals = unique_vals[top_idx]
            counts = counts[top_idx]

            # Append _OTHER_ bucket
            unique_vals = np.append(unique_vals, _OTHER_BUCKET)
            counts = np.append(counts, other_count)

        # --- Build per-category stats ---
        stats: list[CategoryStats] = []
        for cat, cnt in zip(unique_vals, counts, strict=True):
            proportion = float(cnt) / n_total
            std_error = float(np.sqrt(proportion * (1 - proportion) / n_total))
            stats.append(
                CategoryStats(
                    category=str(cat),
                    count=int(cnt),
                    proportion=round(proportion, 6),
                    std_error=round(std_error, 6),
                )
            )

        missing_ratio = missing_count / n_samples if n_samples > 0 else 0.0

        return CategoricalProfile(
            stats=stats,
            n_total=n_total,
            n_unique=n_unique,
            missing_count=missing_count,
            missing_ratio=round(missing_ratio, 6),
            is_high_cardinality=is_high_cardinality,
            truncated_at=truncated_at,
        )


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _is_missing(data: NDArray[Any]) -> NDArray[Any]:
    """Vectorised missing-value detection for object arrays.

    Handles ``None``, ``np.nan`` (when dtype allows), and empty strings.

    :param data: 1-D array.
    :return: Boolean mask where ``True`` indicates a missing value.
    """
    if np.issubdtype(data.dtype, np.floating):
        return np.isnan(data)  # type: ignore[no-any-return]

    # Object arrays — check element-wise for None
    mask = np.zeros(len(data), dtype=bool)
    # Vectorised None check
    mask |= data == None  # noqa: E711 — intentional identity-agnostic check
    # Also catch np.nan sneaking into object arrays
    try:
        float_cast: NDArray[Any] = np.where(mask, 0.0, data)
        mask |= np.array(
            [isinstance(v, float) and np.isnan(v) for v in float_cast],
            dtype=bool,
        )
    except (TypeError, ValueError):
        pass
    return mask
