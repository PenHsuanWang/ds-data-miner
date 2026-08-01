"""
Profiling engine — orchestrates full-dataset scanning.

Routes each column to the appropriate profiler based on its ``dtype``,
aggregates results into a :class:`DatasetReport`.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

import ds_data_miner
from ds_data_miner.core.contracts import DatasetReport
from ds_data_miner.profiling.categorical import CategoricalProfiler
from ds_data_miner.profiling.datetime import DatetimeProfiler
from ds_data_miner.profiling.numeric import NumericProfiler


class ProfilingEngine:
    """Full-dataset scanning orchestrator.

    Accepts column data as ``dict[str, np.ndarray]``, routes each column
    to the correct profiler, and assembles a :class:`DatasetReport`.

    :param numeric_profiler: Custom numeric profiler instance.
    :param categorical_profiler: Custom categorical profiler instance.
    :param datetime_profiler: Custom datetime profiler instance.
    """

    def __init__(
        self,
        numeric_profiler: NumericProfiler | None = None,
        categorical_profiler: CategoricalProfiler | None = None,
        datetime_profiler: DatetimeProfiler | None = None,
    ) -> None:
        self.numeric_profiler = numeric_profiler or NumericProfiler()
        self.categorical_profiler = categorical_profiler or CategoricalProfiler()
        self.datetime_profiler = datetime_profiler or DatetimeProfiler()

    def profile_dataset(
        self,
        columns: dict[str, np.ndarray],
        *,
        dataset_name: str = "unnamed",
        duplicate_row_count: int = 0,
        total_rows: int | None = None,
    ) -> DatasetReport:
        """Profile all columns and produce a :class:`DatasetReport`.

        :param columns: Mapping of column name → 1-D NumPy array.
        :param dataset_name: Human-readable dataset identifier.
        :param duplicate_row_count: Pre-computed duplicate row count
            (computed by the adapter layer which has access to the full
            DataFrame).
        :param total_rows: Total rows in the dataset. If ``None``,
            inferred from the first column's length.
        :return: Frozen :class:`DatasetReport`.
        """
        if total_rows is None:
            first_col = next(iter(columns.values()), np.array([]))
            total_rows = len(first_col)

        column_profiles = {}
        for col_name, col_data in columns.items():
            col_data = np.asarray(col_data).ravel()
            profiler = self._route(col_data)
            column_profiles[col_name] = profiler.fit(col_data)

        duplicate_ratio = duplicate_row_count / total_rows if total_rows > 0 else 0.0

        return DatasetReport(
            dataset_name=dataset_name,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            ds_data_miner_version=ds_data_miner.__version__,
            total_rows=total_rows,
            total_columns=len(columns),
            duplicate_row_count=duplicate_row_count,
            duplicate_row_ratio=round(duplicate_ratio, 6),
            columns=column_profiles,
        )

    # ------------------------------------------------------------------
    # Internal routing
    # ------------------------------------------------------------------

    def _route(
        self,
        data: np.ndarray,
    ) -> NumericProfiler | CategoricalProfiler | DatetimeProfiler:
        """Select the appropriate profiler based on array dtype.

        :param data: 1-D NumPy array.
        :return: The profiler instance to use.
        """
        if np.issubdtype(data.dtype, np.datetime64):
            return self.datetime_profiler
        if np.issubdtype(data.dtype, np.number):
            return self.numeric_profiler
        return self.categorical_profiler
