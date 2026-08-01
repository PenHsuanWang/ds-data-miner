"""Tests for ReportExporter — JSON file output and schema generation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import numpy as np
import pytest

from ds_data_miner.core.contracts import DatasetReport
from ds_data_miner.export.serializer import ReportExporter
from ds_data_miner.profiling.numeric import NumericProfiler

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def sample_report() -> DatasetReport:
    """A minimal DatasetReport for export testing."""
    profiler = NumericProfiler()
    rng = np.random.default_rng(0)
    profile = profiler.fit(rng.standard_normal(1000))

    return DatasetReport(
        dataset_name="test_dataset",
        created_at="2024-01-01T00:00:00Z",
        ds_data_miner_version="0.1.0",
        total_rows=1000,
        total_columns=1,
        duplicate_row_count=0,
        duplicate_row_ratio=0.0,
        columns={"values": profile},
    )


class TestReportExporter:
    def test_export_creates_json_file(
        self,
        sample_report: DatasetReport,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "report.json"
        exporter = ReportExporter()
        exporter.export(sample_report, out)
        assert out.exists()

    def test_exported_json_is_valid(
        self,
        sample_report: DatasetReport,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "report.json"
        exporter = ReportExporter()
        exporter.export(sample_report, out)

        content = out.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["dataset_name"] == "test_dataset"
        assert "values" in parsed["columns"]

    def test_no_nan_or_inf_in_json(
        self,
        sample_report: DatasetReport,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "report.json"
        exporter = ReportExporter()
        exporter.export(sample_report, out)

        content = out.read_text(encoding="utf-8")
        assert "NaN" not in content
        assert "Infinity" not in content

    def test_creates_parent_dirs(
        self,
        sample_report: DatasetReport,
        tmp_path: Path,
    ) -> None:
        out = tmp_path / "nested" / "dir" / "report.json"
        exporter = ReportExporter()
        exporter.export(sample_report, out)
        assert out.exists()


class TestSchemaExport:
    def test_export_schema_creates_file(self, tmp_path: Path) -> None:
        out = tmp_path / "report.schema.json"
        ReportExporter.export_schema(out)
        assert out.exists()

    def test_schema_is_valid_json(self, tmp_path: Path) -> None:
        out = tmp_path / "report.schema.json"
        ReportExporter.export_schema(out)

        content = out.read_text(encoding="utf-8")
        schema = json.loads(content)
        assert "properties" in schema
        assert "DatasetReport" in schema.get("title", "") or "$defs" in schema
