"""
Pandas extension adapter — ``df.miner`` accessor.

Importing this module registers the ``miner`` accessor on
:class:`pandas.DataFrame`.  The core and profiling modules remain
completely free of any ``pandas`` dependency.
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

    Usage::

        import ds_data_miner.pandas_ext  # noqa: F401

        df = pd.read_csv("data.csv")
        report = df.miner.profile()
        df.miner.export_json("report.json")

    :param pandas_obj: The DataFrame this accessor is attached to.
    """

    def __init__(self, pandas_obj: pd.DataFrame) -> None:
        self._obj = pandas_obj

    def profile(
        self,
        *,
        dataset_name: str = "unnamed",
        engine: ProfilingEngine | None = None,
    ) -> DatasetReport:
        """Full-table scan producing a :class:`DatasetReport`.

        :param dataset_name: Human-readable name for the dataset.
        :param engine: Custom :class:`ProfilingEngine` (uses defaults
            if ``None``).
        :return: Frozen :class:`DatasetReport`.
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

        :param path: Output JSON file path.
        :param dataset_name: Human-readable name for the dataset.
        :param indent: JSON indentation level.
        :param engine: Custom :class:`ProfilingEngine`.
        :return: The :class:`DatasetReport` that was exported.
        """
        report = self.profile(dataset_name=dataset_name, engine=engine)
        exporter = ReportExporter()
        exporter.export(report, path, indent=indent)
        return report
