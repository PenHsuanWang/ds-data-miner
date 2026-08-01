"""Tests for MinerAccessor (df.miner) — Pandas integration."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

import ds_data_miner.pandas_ext  # noqa: F401 — registers df.miner
from ds_data_miner.core.contracts import (
    CategoricalProfile,
    DatasetReport,
    DatetimeProfile,
    DistributionProfile,
)


@pytest.fixture()
def mixed_df(rng: np.random.Generator) -> pd.DataFrame:
    """DataFrame with numeric, categorical, and datetime columns."""
    n = 300
    base = pd.Timestamp("2024-01-01")
    return pd.DataFrame(
        {
            "sensor": rng.standard_normal(n),
            "status": np.where(np.arange(n) % 3 == 0, "ok", "error"),
            "ts": pd.date_range(base, periods=n, freq="1min"),
        }
    )


@pytest.fixture()
def df_with_duplicates(rng: np.random.Generator) -> pd.DataFrame:
    base = pd.DataFrame({"x": rng.standard_normal(50)})
    return pd.concat([base, base.head(10)], ignore_index=True)


class TestMinerProfile:
    def test_returns_dataset_report(self, mixed_df: pd.DataFrame) -> None:
        report = mixed_df.miner.profile()
        assert isinstance(report, DatasetReport)

    def test_column_count(self, mixed_df: pd.DataFrame) -> None:
        report = mixed_df.miner.profile()
        assert report.total_columns == 3

    def test_row_count(self, mixed_df: pd.DataFrame) -> None:
        report = mixed_df.miner.profile()
        assert report.total_rows == 300

    def test_numeric_column_dtype_routed(self, mixed_df: pd.DataFrame) -> None:
        report = mixed_df.miner.profile()
        assert isinstance(report.columns["sensor"], DistributionProfile)

    def test_categorical_column_dtype_routed(self, mixed_df: pd.DataFrame) -> None:
        report = mixed_df.miner.profile()
        assert isinstance(report.columns["status"], CategoricalProfile)

    def test_datetime_column_dtype_routed(self, mixed_df: pd.DataFrame) -> None:
        report = mixed_df.miner.profile()
        assert isinstance(report.columns["ts"], DatetimeProfile)

    def test_dataset_name_forwarded(self, mixed_df: pd.DataFrame) -> None:
        report = mixed_df.miner.profile(dataset_name="my_sensors")
        assert report.dataset_name == "my_sensors"

    def test_duplicate_detection(self, df_with_duplicates: pd.DataFrame) -> None:
        report = df_with_duplicates.miner.profile()
        assert report.duplicate_row_count == 10
        assert report.duplicate_row_ratio == pytest.approx(10 / 60, abs=1e-5)


class TestMinerExportJson:
    def test_creates_file(self, mixed_df: pd.DataFrame, tmp_path: object) -> None:
        from pathlib import Path

        assert isinstance(tmp_path, Path)
        out = tmp_path / "report.json"
        mixed_df.miner.export_json(out)
        assert out.exists()

    def test_valid_json_output(self, mixed_df: pd.DataFrame, tmp_path: object) -> None:
        from pathlib import Path

        assert isinstance(tmp_path, Path)
        out = tmp_path / "report.json"
        mixed_df.miner.export_json(out)
        parsed = json.loads(out.read_text())
        assert "columns" in parsed
        assert "sensor" in parsed["columns"]

    def test_no_nan_in_output(self, mixed_df: pd.DataFrame, tmp_path: object) -> None:
        from pathlib import Path

        assert isinstance(tmp_path, Path)
        out = tmp_path / "report.json"
        mixed_df.miner.export_json(out)
        content = out.read_text()
        assert "NaN" not in content
        assert "Infinity" not in content

    def test_returns_dataset_report(
        self, mixed_df: pd.DataFrame, tmp_path: object
    ) -> None:
        from pathlib import Path

        assert isinstance(tmp_path, Path)
        report = mixed_df.miner.export_json(tmp_path / "r.json")
        assert isinstance(report, DatasetReport)

    def test_df_with_nan_values(self, tmp_path: object) -> None:
        """Numeric column with NaN should profile without error."""
        from pathlib import Path

        assert isinstance(tmp_path, Path)
        df = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0, 5.0]})
        report = df.miner.export_json(tmp_path / "nan_report.json")
        profile = report.columns["x"]
        assert isinstance(profile, DistributionProfile)
        assert profile.missing_count == 1
