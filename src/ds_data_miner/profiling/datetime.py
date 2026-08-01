"""
Datetime column profiler — monotonicity, gap detection, frequency inference.

All time-delta operations use NumPy's ``datetime64`` / ``timedelta64``
vectorised arithmetic.
"""

from __future__ import annotations

import numpy as np

from ds_data_miner.core.contracts import DatetimeProfile
from ds_data_miner.core.exceptions import DataQualityError
from ds_data_miner.profiling.base import BaseProfiler


class DatetimeProfiler(BaseProfiler):
    """Profile datetime columns — monotonicity, gaps, frequency.

    :param gap_threshold_factor: A gap is detected when the time-delta
        between consecutive (sorted) timestamps exceeds
        ``median_delta * gap_threshold_factor``.
    """

    def __init__(self, gap_threshold_factor: float = 2.0) -> None:
        if gap_threshold_factor <= 0:
            raise ValueError("gap_threshold_factor must be > 0.")
        self.gap_threshold_factor = gap_threshold_factor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, data: np.ndarray) -> DatetimeProfile:
        """Full-scan profile of a 1-D datetime64 array.

        :param data: 1-D NumPy array of ``datetime64`` dtype.
        :return: Frozen :class:`DatetimeProfile`.
        :raises DataQualityError: If the array is empty or all NaT.
        :raises TypeError: If *data* is not datetime64.
        """
        data = np.asarray(data).ravel()

        if not np.issubdtype(data.dtype, np.datetime64):
            raise TypeError(f"Expected datetime64 array, got dtype={data.dtype}")

        n_samples = len(data)
        if n_samples == 0:
            raise DataQualityError("Cannot profile an empty array.")

        # --- Missing (NaT) ---
        nat_mask = np.isnat(data)
        missing_count = int(np.count_nonzero(nat_mask))
        valid = data[~nat_mask]

        if len(valid) == 0:
            raise DataQualityError("All values are NaT.")

        # --- Sort valid timestamps ---
        sorted_valid = np.sort(valid)
        start = str(sorted_valid[0])
        end = str(sorted_valid[-1])
        duration_td = sorted_valid[-1] - sorted_valid[0]
        duration_seconds = float(duration_td / np.timedelta64(1, "s"))

        # --- Monotonicity (on original order, not sorted) ---
        is_monotonic = bool(np.all(np.diff(valid) >= np.timedelta64(0)))

        # --- Gap detection ---
        gap_count = 0
        gap_locations: list[dict[str, str | float]] = []

        if len(sorted_valid) > 1:
            diffs = np.diff(sorted_valid)
            # Convert to float seconds for statistical comparison
            diffs_seconds = diffs / np.timedelta64(1, "s")
            median_diff = float(np.median(diffs_seconds))

            if median_diff > 0:
                threshold = median_diff * self.gap_threshold_factor
                gap_mask = diffs_seconds > threshold
                gap_indices = np.flatnonzero(gap_mask)
                gap_count = len(gap_indices)

                for idx in gap_indices:
                    gap_locations.append(
                        {
                            "from": str(sorted_valid[idx]),
                            "to": str(sorted_valid[idx + 1]),
                            "duration_seconds": float(diffs_seconds[idx]),
                        }
                    )

        # --- Frequency inference ---
        inferred_freq = _infer_freq(sorted_valid)

        missing_ratio = missing_count / n_samples if n_samples > 0 else 0.0

        return DatetimeProfile(
            start=start,
            end=end,
            duration_seconds=duration_seconds,
            is_monotonic_increasing=is_monotonic,
            gap_count=gap_count,
            gap_locations=gap_locations,
            inferred_freq=inferred_freq,
            n_samples=n_samples,
            missing_count=missing_count,
            missing_ratio=round(missing_ratio, 6),
        )


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

_FREQ_MAP: list[tuple[float, str]] = [
    (1.0, "1s"),
    (60.0, "1min"),
    (300.0, "5min"),
    (600.0, "10min"),
    (900.0, "15min"),
    (1800.0, "30min"),
    (3600.0, "1h"),
    (7200.0, "2h"),
    (14400.0, "4h"),
    (21600.0, "6h"),
    (43200.0, "12h"),
    (86400.0, "1d"),
    (604800.0, "1w"),
]


def _infer_freq(sorted_valid: np.ndarray) -> str | None:
    """Infer a human-readable sampling frequency from sorted timestamps.

    Uses the median time-delta and snaps to the nearest known frequency
    if the coefficient of variation is low enough (< 0.1).

    :param sorted_valid: Sorted datetime64 array (no NaT).
    :return: Frequency string like ``"1min"``, ``"1h"``, or ``None``.
    """
    if len(sorted_valid) < 2:
        return None

    diffs_seconds = np.diff(sorted_valid) / np.timedelta64(1, "s")
    median_diff = float(np.median(diffs_seconds))
    std_diff = float(np.std(diffs_seconds))

    if median_diff <= 0:
        return None

    # Check regularity — CV must be < 10%
    cv = std_diff / median_diff if median_diff > 0 else float("inf")
    if cv > 0.1:
        return None

    # Snap to nearest known frequency
    best_freq: str | None = None
    best_dist = float("inf")
    for target_seconds, label in _FREQ_MAP:
        dist = abs(median_diff - target_seconds)
        if dist < best_dist:
            best_dist = dist
            best_freq = label

    # Only return if within 20% of the snapped value
    if best_freq is not None:
        for target_seconds, label in _FREQ_MAP:
            if (
                label == best_freq
                and abs(median_diff - target_seconds) / target_seconds < 0.2
            ):
                return best_freq

    return None
