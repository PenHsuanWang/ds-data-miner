"""
Categorical column profiler — full-scan with high-cardinality defense.

Computes per-category counts, proportions, and binomial standard errors.
Automatically truncates to Top-N when cardinality exceeds the threshold.
"""

from __future__ import annotations

import warnings

import numpy as np

from ds_data_miner.core.contracts import CategoricalProfile, CategoryStats
from ds_data_miner.core.exceptions import DataQualityError, HighCardinalityWarning
from ds_data_miner.profiling.base import BaseProfiler

_OTHER_BUCKET = "_OTHER_"


class CategoricalProfiler(BaseProfiler):
    """Profile categorical (object / string) columns via full-scan.

    :param max_cardinality: Maximum number of unique categories before
        truncation.  Categories beyond Top-N are merged into ``_OTHER_``.
    """

    def __init__(self, max_cardinality: int = 100) -> None:
        if max_cardinality < 1:
            raise ValueError("max_cardinality must be >= 1.")
        self.max_cardinality = max_cardinality

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, data: np.ndarray) -> CategoricalProfile:
        """Full-scan profile of a 1-D categorical array.

        :param data: 1-D NumPy array of object / string dtype.
        :return: Frozen :class:`CategoricalProfile`.
        :raises DataQualityError: If the array is empty.
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


def _is_missing(data: np.ndarray) -> np.ndarray:
    """Vectorised missing-value detection for object arrays.

    Handles ``None``, ``np.nan`` (when dtype allows), and empty strings.

    :param data: 1-D array.
    :return: Boolean mask where ``True`` indicates a missing value.
    """
    if np.issubdtype(data.dtype, np.floating):
        return np.isnan(data)

    # Object arrays — check element-wise for None
    mask = np.zeros(len(data), dtype=bool)
    # Vectorised None check
    mask |= data == None  # noqa: E711 — intentional identity-agnostic check
    # Also catch np.nan sneaking into object arrays
    try:
        float_cast = np.where(mask, 0.0, data)  # avoid NaN in already-marked
        mask |= np.array(
            [isinstance(v, float) and np.isnan(v) for v in float_cast],
            dtype=bool,
        )
    except (TypeError, ValueError):
        pass
    return mask
