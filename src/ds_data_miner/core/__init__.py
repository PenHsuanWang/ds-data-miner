"""
Core layer — data contracts and exceptions.

Re-exports all public contracts for convenient access.
"""

from ds_data_miner.core.contracts import (
    CategoricalProfile,
    CategoryStats,
    DatasetReport,
    DatetimeProfile,
    DistributionProfile,
)
from ds_data_miner.core.exceptions import (
    DataMinerBaseError,
    DataQualityError,
    ShapeMismatchError,
)

__all__ = [
    "CategoricalProfile",
    "CategoryStats",
    "DataMinerBaseError",
    "DataQualityError",
    "DatasetReport",
    "DatetimeProfile",
    "DistributionProfile",
    "ShapeMismatchError",
]
