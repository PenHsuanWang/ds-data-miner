"""
Custom exception hierarchy for ds-data-miner.

All exceptions inherit from :class:`DataMinerBaseException` to allow
blanket catching at the library boundary.
"""


class DataMinerBaseError(Exception):
    """Base exception for all ds-data-miner errors."""


class DataQualityError(DataMinerBaseError):
    """Raised when a profiler encounters irrecoverable dirty data.

    Examples: an array that is entirely NaN, or contains NaN/Inf when
    ``ignore_nan=False``.
    """


class ShapeMismatchError(DataMinerBaseError):
    """Raised when array dimensions do not match expectations."""


class HighCardinalityWarning(UserWarning):
    """Issued when a categorical column's unique count exceeds the
    truncation threshold.

    This is a *warning*, not an exception — the profiler will
    automatically truncate to Top-N and continue.
    """
