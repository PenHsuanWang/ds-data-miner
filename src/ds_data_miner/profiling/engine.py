"""
Profiling engine — orchestrates full-dataset scanning.

Routes each column to the appropriate profiler based on its ``dtype``,
aggregates results into a :class:`~ds_data_miner.core.contracts.DatasetReport`.

**Agent Usage**

Use :class:`ProfilingEngine` when:

- You have column data already as a ``dict[str, numpy.ndarray]`` (no Pandas).
- You need fine-grained control over which profiler handles each column type.
- You are building a custom data pipeline without Pandas.

If you have a :class:`pandas.DataFrame`, prefer
:class:`~ds_data_miner.pandas_ext.accessor.MinerAccessor` (``df.miner``) which
handles dtype conversion and duplicate detection automatically.
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

    Accepts column data as ``dict[str, numpy.ndarray]``, routes each column
    to the correct profiler by ``dtype``, and assembles a frozen
    :class:`~ds_data_miner.core.contracts.DatasetReport`.

    **Dtype Routing Rules**

    .. list-table::
       :header-rows: 1
       :widths: 30 70

       * - Array dtype
         - Profiler selected
       * - ``numpy.datetime64``
         - :class:`~ds_data_miner.profiling.datetime.DatetimeProfiler`
       * - Any numeric subtype
         - :class:`~ds_data_miner.profiling.numeric.NumericProfiler`
       * - Anything else
         - :class:`~ds_data_miner.profiling.categorical.CategoricalProfiler`

    :param numeric_profiler: Optional custom :class:`NumericProfiler` instance.
        If ``None``, a default ``NumericProfiler()`` is created.
    :param categorical_profiler: Optional custom :class:`CategoricalProfiler`
        instance.  If ``None``, a default ``CategoricalProfiler()`` is created.
    :param datetime_profiler: Optional custom :class:`DatetimeProfiler`
        instance.  If ``None``, a default ``DatetimeProfiler()`` is created.

    Example — default engine, mixed columns::

        import numpy as np
        from ds_data_miner.profiling.engine import ProfilingEngine

        base = np.datetime64("2024-01-01T00:00:00")
        columns = {
            "price":    np.array([1.5, 2.3, np.nan, 4.1]),
            "category": np.array(["A", "B", "A", "C"]),
            "ts":       base + np.arange(4) * np.timedelta64(1, "h"),
        }

        engine = ProfilingEngine()
        report = engine.profile_dataset(columns, dataset_name="my_dataset")

        print(report.total_columns)                # 3
        print(report.columns["price"].mean)        # DistributionProfile field
        print(report.columns["category"].n_unique) # CategoricalProfile field
        print(report.columns["ts"].inferred_freq)  # DatetimeProfile field
        print(report.model_dump_json(indent=2))    # full JSON

    Example — custom profiler for high-cardinality guard::

        from ds_data_miner.profiling.categorical import CategoricalProfiler

        engine = ProfilingEngine(
            categorical_profiler=CategoricalProfiler(max_cardinality=50),
        )
        report = engine.profile_dataset(columns)
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
        """Profile all columns and produce a :class:`~ds_data_miner.core.contracts.DatasetReport`.

        Iterates over every column in *columns*, routes it to the appropriate
        profiler by dtype, and aggregates all profiles into a single frozen
        :class:`~ds_data_miner.core.contracts.DatasetReport`.

        :param columns: Mapping of column name → 1-D NumPy array.
            Arrays may have any dtype; routing is automatic.
        :param dataset_name: Human-readable dataset identifier embedded in
            the report metadata.  Default ``\"unnamed\"``.
        :param duplicate_row_count: Number of fully-duplicated rows in the
            original dataset.  Must be computed externally (e.g. by the Pandas
            adapter which has access to the full DataFrame).  Default ``0``.
        :param total_rows: Total number of rows in the dataset.  If ``None``,
            inferred from the length of the first column array.
        :return: Frozen :class:`~ds_data_miner.core.contracts.DatasetReport`
            with per-column profiles and dataset-level metadata.

        Example::

            report = engine.profile_dataset(
                columns,
                dataset_name="sensor_readings",
                duplicate_row_count=5,
                total_rows=1000,
            )
            assert report.ds_data_miner_version == "0.1.0"
            assert "price" in report.columns
            json_bytes = report.model_dump_json()   # ready for export
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
        :return: The profiler instance to use for this column.
        """
        if np.issubdtype(data.dtype, np.datetime64):
            return self.datetime_profiler
        if np.issubdtype(data.dtype, np.number):
            return self.numeric_profiler
        return self.categorical_profiler
