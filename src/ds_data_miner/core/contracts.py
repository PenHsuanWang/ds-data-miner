"""
Core data contracts for ds-data-miner.

All contracts are **immutable** Pydantic v2 Models that serve as the sole
communication standard across modules. They handle:

- JSON serialization with NaN → null / Inf → null conversion
- NumPy scalar → Python native type coercion
- Frozen (immutable) instances to prevent side-effects
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Base Model
# ---------------------------------------------------------------------------
class ProfileBaseModel(BaseModel):
    """Base class for all profile contracts.

    Provides frozen immutability and automatic NaN/Inf → JSON null handling
    via Pydantic v2's ``ser_json_inf_nan`` option.
    """

    model_config = ConfigDict(
        frozen=True,
        ser_json_inf_nan="null",
    )


# ---------------------------------------------------------------------------
# Numeric Profile
# ---------------------------------------------------------------------------
class DistributionProfile(ProfileBaseModel):
    """Statistical profile of a numeric column after full-scan analysis.

    :param mean: Arithmetic mean.
    :param variance: Population variance.
    :param std: Population standard deviation.
    :param skewness: Fisher's skewness.
    :param kurtosis: Excess kurtosis (Fisher's definition).
    :param median: Median value.
    :param min: Minimum value.
    :param max: Maximum value.
    :param q25: 25th percentile.
    :param q75: 75th percentile.
    :param sem: Standard Error of the Mean (std / sqrt(N)).
    :param ci_lower: Lower bound of the confidence interval.
    :param ci_upper: Upper bound of the confidence interval.
    :param histogram_bin_edges: Pre-computed histogram bin edges for
        downstream visualisation (no raw arrays stored).
    :param histogram_counts: Pre-computed histogram counts.
    :param n_samples: Total number of elements (including missing).
    :param n_valid: Number of valid (finite) elements.
    :param missing_count: Number of NaN values.
    :param missing_ratio: ``missing_count / n_samples``.
    :param inf_count: Number of Inf / -Inf values.
    :param distribution_type: Best-fit distribution name (optional).
    :param ks_statistic: K-S test statistic (optional).
    :param ks_p_value: K-S test p-value (optional).
    """

    # Basic statistics
    mean: float
    variance: float
    std: float
    skewness: float
    kurtosis: float
    median: float
    min: float
    max: float
    q25: float
    q75: float

    # Statistical errors
    sem: float
    ci_lower: float
    ci_upper: float

    # Histogram representation
    histogram_bin_edges: list[float]
    histogram_counts: list[int]

    # Sample & quality metadata
    n_samples: int
    n_valid: int
    missing_count: int
    missing_ratio: float
    inf_count: int

    # Distribution test results (filled by DistributionTester, optional)
    distribution_type: str | None = None
    ks_statistic: float | None = None
    ks_p_value: float | None = None


# ---------------------------------------------------------------------------
# Categorical Profile
# ---------------------------------------------------------------------------
class CategoryStats(ProfileBaseModel):
    """Statistics for a single category value.

    :param category: The category label.
    :param count: Absolute count.
    :param proportion: Relative proportion (count / n_total).
    :param std_error: Binomial standard error √(p*(1-p)/N).
    """

    category: str
    count: int
    proportion: float
    std_error: float


class CategoricalProfile(ProfileBaseModel):
    """Statistical profile of a categorical column after full-scan analysis.

    :param stats: Per-category statistics.
    :param n_total: Total number of non-missing elements.
    :param n_unique: Number of unique categories.
    :param missing_count: Number of missing (None / NaN) values.
    :param missing_ratio: ``missing_count / (n_total + missing_count)``.
    :param is_high_cardinality: Whether the column exceeds the cardinality
        threshold and was truncated.
    :param truncated_at: The Top-N threshold applied (None if not truncated).
    """

    stats: list[CategoryStats]
    n_total: int
    n_unique: int
    missing_count: int
    missing_ratio: float
    is_high_cardinality: bool
    truncated_at: int | None = None


# ---------------------------------------------------------------------------
# Datetime Profile
# ---------------------------------------------------------------------------
class DatetimeProfile(ProfileBaseModel):
    """Statistical profile of a datetime column after full-scan analysis.

    :param start: Earliest timestamp (ISO 8601).
    :param end: Latest timestamp (ISO 8601).
    :param duration_seconds: Total duration in seconds.
    :param is_monotonic_increasing: Whether timestamps are monotonically
        increasing.
    :param gap_count: Number of detected time-gaps.
    :param gap_locations: Details of each gap (from, to, duration_seconds).
    :param inferred_freq: Inferred sampling frequency string, or None
        if irregular.
    :param n_samples: Total number of elements (including NaT).
    :param missing_count: Number of NaT values.
    :param missing_ratio: ``missing_count / n_samples``.
    """

    start: str
    end: str
    duration_seconds: float
    is_monotonic_increasing: bool
    gap_count: int
    gap_locations: list[dict[str, str | float]]
    inferred_freq: str | None

    n_samples: int
    missing_count: int
    missing_ratio: float


# ---------------------------------------------------------------------------
# Dataset Report (top-level aggregator)
# ---------------------------------------------------------------------------
class DatasetReport(ProfileBaseModel):
    """Top-level report aggregating all column profiles for a dataset.

    :param dataset_name: Human-readable dataset identifier.
    :param created_at: Report creation timestamp (ISO 8601).
    :param ds_data_miner_version: Version of ds-data-miner used.
    :param total_rows: Number of rows in the dataset.
    :param total_columns: Number of columns profiled.
    :param duplicate_row_count: Number of fully-duplicated rows.
    :param duplicate_row_ratio: ``duplicate_row_count / total_rows``.
    :param columns: Mapping of column name → profile object.
    """

    dataset_name: str
    created_at: str
    ds_data_miner_version: str
    total_rows: int
    total_columns: int

    duplicate_row_count: int
    duplicate_row_ratio: float

    columns: dict[
        str,
        DistributionProfile | CategoricalProfile | DatetimeProfile,
    ]
