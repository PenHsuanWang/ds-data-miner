"""
Pandas extension adapter — ``df.miner`` accessor.

Importing this module registers the ``miner`` accessor on
:class:`pandas.DataFrame`.  The core and profiling modules remain
completely free of any ``pandas`` dependency.

**Agent Usage — Recommended Entry Point**

If you have a :class:`pandas.DataFrame`, this is the **primary interface**
for all profiling tasks.  A single import activates the accessor:

.. code-block:: python

    import ds_data_miner.pandas_ext  # registers df.miner — must import once

After that, call ``df.miner.profile()`` or ``df.miner.export_json()`` on
any :class:`pandas.DataFrame`.

- Dtype routing (numeric / categorical / datetime) is handled **automatically**.
- Duplicate row detection is computed at the DataFrame level.
- No manual dtype conversion is needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from ds_data_miner.export.serializer import ReportExporter
from ds_data_miner.profiling.engine import ProfilingEngine

if TYPE_CHECKING:
    from pathlib import Path

    from ds_data_miner.core.contracts import DatasetReport


@pd.api.extensions.register_dataframe_accessor("miner")
class MinerAccessor:
    """Pandas DataFrame accessor providing one-line profiling + export.

    Registered as ``df.miner`` after importing ``ds_data_miner.pandas_ext``.

    **Dtype Routing (automatic)**

    .. list-table::
       :header-rows: 1
       :widths: 40 60

       * - Pandas column type
         - Profiler used
       * - ``datetime64[*]`` (any tz)
         - :class:`~ds_data_miner.profiling.datetime.DatetimeProfiler`
       * - Any numeric dtype
         - :class:`~ds_data_miner.profiling.numeric.NumericProfiler`
       * - ``object``, ``category``, str
         - :class:`~ds_data_miner.profiling.categorical.CategoricalProfiler`

    **Workflow**

    1. Import ``ds_data_miner.pandas_ext`` once (registers the accessor).
    2. Load your DataFrame.
    3. Call ``df.miner.profile()`` to get a :class:`~ds_data_miner.core.contracts.DatasetReport`.
    4. Call ``df.miner.export_json(path)`` to scan + write JSON in one step.

    Example — profile only::

        import pandas as pd
        import ds_data_miner.pandas_ext  # noqa: F401

        df = pd.read_csv("sensor_data.csv", parse_dates=["ts"])
        report = df.miner.profile(dataset_name="sensors")

        print(report.total_rows)
        print(report.duplicate_row_count)
        print(report.columns["temperature"].mean)  # DistributionProfile
        print(report.columns["status"].stats)      # list[CategoryStats]

    Example — one-shot scan + JSON export::

        df.miner.export_json(
            "reports/sensor_report.json",
            dataset_name="sensors",
            indent=2,
        )

    Example — custom profiler (e.g. higher cardinality limit)::

        from ds_data_miner.profiling.engine import ProfilingEngine
        from ds_data_miner.profiling.categorical import CategoricalProfiler

        engine = ProfilingEngine(
            categorical_profiler=CategoricalProfiler(max_cardinality=500),
        )
        report = df.miner.profile(engine=engine)

    :param pandas_obj: The DataFrame this accessor is attached to.
        Set automatically by Pandas when you access ``df.miner``.
    """

    def __init__(self, pandas_obj: pd.DataFrame) -> None:
        self._obj = pandas_obj

    def profile(
        self,
        *,
        dataset_name: str = "unnamed",
        engine: ProfilingEngine | None = None,
    ) -> DatasetReport:
        """Full-table scan producing a :class:`~ds_data_miner.core.contracts.DatasetReport`.

        Converts every column to a NumPy array with the correct dtype,
        detects duplicate rows, and delegates to :class:`~ds_data_miner.profiling.engine.ProfilingEngine`.

        :param dataset_name: Human-readable name embedded in the report
            metadata.  Default ``\"unnamed\"``.
        :param engine: Custom :class:`~ds_data_miner.profiling.engine.ProfilingEngine`
            instance.  Pass one to override default profiler settings
            (e.g. ``ci_level``, ``max_cardinality``).  Uses defaults if ``None``.
        :return: Frozen :class:`~ds_data_miner.core.contracts.DatasetReport`
            containing all column profiles and dataset-level quality metadata.

        Example::

            report = df.miner.profile(dataset_name="my_dataset")

            # Dataset-level info
            print(report.total_rows)            # int
            print(report.duplicate_row_count)   # int
            print(report.created_at)            # ISO 8601 timestamp string

            # Column profiles (type depends on column dtype)
            p = report.columns["price"]         # DistributionProfile
            print(p.mean, p.std, p.sem)

            c = report.columns["status"]        # CategoricalProfile
            print([(s.category, s.proportion) for s in c.stats])

            t = report.columns["ts"]            # DatetimeProfile
            print(t.inferred_freq, t.gap_count)
        """
        engine = engine or ProfilingEngine()
        df = self._obj

        # --- Duplicate detection (DataFrame-level) ---
        duplicate_row_count = int(df.duplicated().sum())

        # --- Convert columns to numpy arrays with dtype routing ---
        columns: dict[str, np.ndarray] = {}
        for col in df.columns:
            series = df[col]
            if pd.api.types.is_datetime64_any_dtype(series):
                columns[str(col)] = series.to_numpy(dtype="datetime64[ns]")
            elif pd.api.types.is_numeric_dtype(series):
                columns[str(col)] = series.to_numpy(dtype=np.float64)
            else:
                columns[str(col)] = series.to_numpy(dtype=object)

        return engine.profile_dataset(
            columns,
            dataset_name=dataset_name,
            duplicate_row_count=duplicate_row_count,
            total_rows=len(df),
        )

    def export_json(
        self,
        path: str | Path,
        *,
        dataset_name: str = "unnamed",
        indent: int = 2,
        engine: ProfilingEngine | None = None,
    ) -> DatasetReport:
        """One-shot: full-table scan + JSON export.

        Equivalent to calling :meth:`profile` and then
        :meth:`~ds_data_miner.export.serializer.ReportExporter.export`.
        NaN and Inf values in the output are serialized as JSON ``null``
        automatically.

        :param path: Output JSON file path (``str`` or :class:`pathlib.Path`).
            Parent directories are created automatically.
        :param dataset_name: Human-readable name embedded in the report.
            Default ``\"unnamed\"``.
        :param indent: JSON indentation level.  Default ``2`` (pretty-printed).
            Set to ``0`` or ``None`` for compact output.
        :param engine: Custom :class:`~ds_data_miner.profiling.engine.ProfilingEngine`.
            Uses defaults if ``None``.
        :return: The :class:`~ds_data_miner.core.contracts.DatasetReport` that
            was written, for further in-memory use.

        Example::

            # Returns the report AND writes the file
            report = df.miner.export_json(
                "reports/my_report.json",
                dataset_name="production_data",
            )
            print(report.total_rows)  # still usable after export
        """
        report = self.profile(dataset_name=dataset_name, engine=engine)
        exporter = ReportExporter()
        exporter.export(report, path, indent=indent)
        return report
