"""Tests for ProfilingEngine — dtype routing and DatasetReport assembly."""

from __future__ import annotations

import numpy as np
import pytest

from ds_data_miner.core.contracts import (
    CategoricalProfile,
    DatasetReport,
    DatetimeProfile,
    DistributionProfile,
)
from ds_data_miner.profiling.engine import ProfilingEngine


@pytest.fixture()
def engine() -> ProfilingEngine:
    return ProfilingEngine()


@pytest.fixture()
def mixed_columns(rng: np.random.Generator) -> dict[str, np.ndarray]:
    base = np.datetime64("2024-01-01T00:00:00")
    return {
        "values": rng.standard_normal(200).astype(np.float64),
        "labels": np.array(["A", "B", "C", "A", "B"] * 40),
        "ts": base + np.arange(200) * np.timedelta64(1, "m"),
    }


class TestProfilingEngineRouting:
    def test_numeric_column_routed_correctly(
        self, engine: ProfilingEngine, rng: np.random.Generator
    ) -> None:
        columns = {"price": rng.standard_normal(100).astype(np.float64)}
        report = engine.profile_dataset(columns, dataset_name="test")
        assert isinstance(report.columns["price"], DistributionProfile)

    def test_categorical_column_routed_correctly(self, engine: ProfilingEngine) -> None:
        columns = {"status": np.array(["ok", "error", "ok", "warn"])}
        report = engine.profile_dataset(columns, dataset_name="test")
        assert isinstance(report.columns["status"], CategoricalProfile)

    def test_datetime_column_routed_correctly(self, engine: ProfilingEngine) -> None:
        base = np.datetime64("2024-01-01")
        columns = {"ts": base + np.arange(50) * np.timedelta64(1, "D")}
        report = engine.profile_dataset(columns, dataset_name="test")
        assert isinstance(report.columns["ts"], DatetimeProfile)

    def test_mixed_columns(
        self,
        engine: ProfilingEngine,
        mixed_columns: dict[str, np.ndarray],
    ) -> None:
        report = engine.profile_dataset(mixed_columns, dataset_name="mixed")
        assert isinstance(report.columns["values"], DistributionProfile)
        assert isinstance(report.columns["labels"], CategoricalProfile)
        assert isinstance(report.columns["ts"], DatetimeProfile)


class TestDatasetReportAssembly:
    def test_returns_dataset_report(
        self, engine: ProfilingEngine, mixed_columns: dict[str, np.ndarray]
    ) -> None:
        report = engine.profile_dataset(mixed_columns, dataset_name="my_ds")
        assert isinstance(report, DatasetReport)

    def test_dataset_name_propagated(
        self, engine: ProfilingEngine, mixed_columns: dict[str, np.ndarray]
    ) -> None:
        report = engine.profile_dataset(mixed_columns, dataset_name="sensor_data")
        assert report.dataset_name == "sensor_data"

    def test_total_columns_count(
        self, engine: ProfilingEngine, mixed_columns: dict[str, np.ndarray]
    ) -> None:
        report = engine.profile_dataset(mixed_columns)
        assert report.total_columns == len(mixed_columns)

    def test_total_rows_inferred(
        self, engine: ProfilingEngine, mixed_columns: dict[str, np.ndarray]
    ) -> None:
        report = engine.profile_dataset(mixed_columns)
        assert report.total_rows == 200

    def test_total_rows_explicit(
        self, engine: ProfilingEngine, rng: np.random.Generator
    ) -> None:
        columns = {"x": rng.standard_normal(50).astype(np.float64)}
        report = engine.profile_dataset(columns, total_rows=100)
        assert report.total_rows == 100

    def test_duplicate_row_count_propagated(
        self, engine: ProfilingEngine, rng: np.random.Generator
    ) -> None:
        columns = {"x": rng.standard_normal(50).astype(np.float64)}
        report = engine.profile_dataset(columns, duplicate_row_count=5, total_rows=50)
        assert report.duplicate_row_count == 5
        assert report.duplicate_row_ratio == pytest.approx(0.1)

    def test_version_is_set(
        self, engine: ProfilingEngine, rng: np.random.Generator
    ) -> None:
        import ds_data_miner

        columns = {"x": rng.standard_normal(20).astype(np.float64)}
        report = engine.profile_dataset(columns)
        assert report.ds_data_miner_version == ds_data_miner.__version__

    def test_created_at_is_iso8601(
        self, engine: ProfilingEngine, rng: np.random.Generator
    ) -> None:
        from datetime import datetime

        columns = {"x": rng.standard_normal(20).astype(np.float64)}
        report = engine.profile_dataset(columns)
        # Should parse without raising
        datetime.fromisoformat(report.created_at)

    def test_report_is_json_serializable(
        self, engine: ProfilingEngine, mixed_columns: dict[str, np.ndarray]
    ) -> None:
        import json

        report = engine.profile_dataset(mixed_columns)
        json_str = report.model_dump_json()
        parsed = json.loads(json_str)
        assert "columns" in parsed
