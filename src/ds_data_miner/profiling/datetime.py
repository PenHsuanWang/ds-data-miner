"""
Datetime column profiler — monotonicity, gap detection, frequency inference.

All time-delta operations use NumPy's ``datetime64`` / ``timedelta64``
vectorised arithmetic — no Python loops, no sampling.

**Agent Usage Decision Tree**

Use :class:`DatetimeProfiler` when:

- The array dtype is ``numpy.datetime64`` (any resolution: ns, us, ms, s).
- You need any of: date range, monotonicity check, gap detection, or
  inferred sampling frequency.
- You are auditing whether a time-series has missing intervals.

Do **not** use when:

- The column contains numbers → use :class:`NumericProfiler`.
- The column contains strings or categories → use :class:`CategoricalProfiler`.
- You have a :class:`pandas.DataFrame` → use :class:`~ds_data_miner.pandas_ext.accessor.MinerAccessor`.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from ds_data_miner.core.contracts import DatetimeProfile
from ds_data_miner.core.exceptions import DataQualityError
from ds_data_miner.profiling.base import BaseProfiler


class DatetimeProfiler(BaseProfiler):
    """Profile datetime columns — monotonicity, gaps, and frequency inference.

    Performs a complete vectorised scan over ``datetime64`` arrays to detect
    temporal quality issues.

    **Input Requirements**

    - 1-D array with dtype ``numpy.datetime64`` (any resolution).
    - ``NaT`` values are treated as missing and excluded from all computations.

    **Output** — a frozen :class:`~ds_data_miner.core.contracts.DatetimeProfile`
    containing:

    - ``start``, ``end``: ISO 8601 strings of the earliest and latest timestamps.
    - ``duration_seconds``: total time span in seconds.
    - ``is_monotonic_increasing``: ``True`` if timestamps in **original order**
      are non-decreasing.
    - ``gap_count``: number of detected time gaps.
    - ``gap_locations``: list of ``{"from": str, "to": str, "duration_seconds": float}``
      dicts — one per detected gap.
    - ``inferred_freq``: human-readable frequency string (``"1min"``, ``"1h"``,
      ``"1d"``, …) if regular, else ``None``.
    - ``n_samples``, ``missing_count``, ``missing_ratio``: quality metadata.

    **Gap Detection Algorithm**

    A gap is flagged when the time-delta between two consecutive *sorted*
    timestamps exceeds ``median_delta * gap_threshold_factor``.
    The default factor of ``2.0`` means any interval more than twice the
    median interval is considered a gap.

    :param gap_threshold_factor: Multiplier applied to the median time-delta
        to determine the gap threshold.  Must be ``> 0``.  Default ``2.0``.

    Example — regular 1-minute series::

        import numpy as np
        from ds_data_miner.profiling.datetime import DatetimeProfiler

        base = np.datetime64("2024-01-01T00:00:00")
        ts = base + np.arange(1440) * np.timedelta64(1, "m")  # 1 day of minutes

        profile = DatetimeProfiler().fit(ts)

        print(profile.is_monotonic_increasing)  # True
        print(profile.gap_count)                # 0
        print(profile.inferred_freq)            # "1min"
        print(profile.duration_seconds)         # 86340.0

    Example — series with a 10-hour outage gap::

        part1 = base + np.arange(100) * np.timedelta64(1, "m")
        part2 = part1[-1] + np.timedelta64(10, "h") + np.arange(100) * np.timedelta64(1, "m")
        ts_with_gap = np.concatenate([part1, part2])

        profile = DatetimeProfiler().fit(ts_with_gap)
        print(profile.gap_count)                          # 1
        print(profile.gap_locations[0]["duration_seconds"])  # 36000.0
    """

    def __init__(self, gap_threshold_factor: float = 2.0) -> None:
        if gap_threshold_factor <= 0:
            raise ValueError("gap_threshold_factor must be > 0.")
        self.gap_threshold_factor = gap_threshold_factor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, data: NDArray[Any]) -> DatetimeProfile:
        """Full-scan profile of a 1-D datetime64 array.

        :param data: 1-D NumPy array of ``datetime64`` dtype (any resolution).
            Multi-dimensional arrays are flattened via ``ravel()``.
        :return: Frozen :class:`~ds_data_miner.core.contracts.DatetimeProfile`.
        :raises DataQualityError: If the array is empty or entirely ``NaT``.
        :raises TypeError: If *data* dtype is not a ``datetime64`` subtype.

        Example::

            profile = DatetimeProfiler().fit(ts)
            print(profile.start)         # "2024-01-01T00:00:00"
            print(profile.end)           # "2024-01-01T23:59:00"
            print(profile.inferred_freq) # "1min" or None
            for gap in profile.gap_locations:
                print(gap["from"], gap["to"], gap["duration_seconds"])
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


def _infer_freq(sorted_valid: NDArray[Any]) -> str | None:
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
