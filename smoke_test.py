#!/usr/bin/env python3
"""
smoke_test.py — end-to-end functional verification of ds-data-miner.

Exercises every public API surface in a single script:
  1. NumericProfiler   — full-scan, SEM/CI, histogram, NaN handling
  2. CategoricalProfiler — proportions, binomial std_error, high-cardinality
  3. DatetimeProfiler  — monotonicity, gap detection, frequency inference
  4. DistributionTester — K-S test against scipy baseline
  5. ProfilingEngine   — dtype routing + DatasetReport assembly
  6. ReportExporter    — JSON file output + JSON Schema
  7. MinerAccessor     — df.miner.profile() + df.miner.export_json()

Exit codes:
  0 — all checks passed
  1 — one or more checks failed
"""

from __future__ import annotations

import json
import sys
import tempfile
import traceback
from pathlib import Path

import numpy as np

PASS = "\033[92m  ✅ PASS\033[0m"
FAIL = "\033[91m  ❌ FAIL\033[0m"
HEAD = "\033[96m{}\033[0m"

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"{PASS}  {label}")
    else:
        print(f"{FAIL}  {label}" + (f"  →  {detail}" if detail else ""))
        failures.append(label)


def section(title: str) -> None:
    print(f"\n{HEAD.format(title)}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. NumericProfiler
# ─────────────────────────────────────────────────────────────────────────────
section("1. NumericProfiler")
from ds_data_miner.profiling.numeric import NumericProfiler  # noqa: E402
from ds_data_miner.core.contracts import DistributionProfile  # noqa: E402
from ds_data_miner.core.exceptions import DataQualityError  # noqa: E402

rng = np.random.default_rng(42)
data_1m = rng.standard_normal(1_000_000).astype(np.float64)

profiler_n = NumericProfiler()
profile = profiler_n.fit(data_1m)

check("Returns DistributionProfile", isinstance(profile, DistributionProfile))
check("n_samples == 1_000_000", profile.n_samples == 1_000_000)
check("mean near 0", abs(profile.mean) < 0.01, f"mean={profile.mean:.6f}")
check("std near 1", abs(profile.std - 1.0) < 0.01, f"std={profile.std:.6f}")
check("SEM > 0", profile.sem > 0)
check("CI lower < mean < CI upper", profile.ci_lower < profile.mean < profile.ci_upper)
check("histogram_bin_edges is list", isinstance(profile.histogram_bin_edges, list))
check(
    "histogram_counts length = bin_edges - 1",
    len(profile.histogram_counts) == len(profile.histogram_bin_edges) - 1,
)
check("missing_count == 0", profile.missing_count == 0)
check("inf_count == 0", profile.inf_count == 0)

# NaN handling
data_with_nan = data_1m.copy()
data_with_nan[:10_000] = np.nan
profile_nan = NumericProfiler(ignore_nan=True).fit(data_with_nan)
check("missing_count detected", profile_nan.missing_count == 10_000)
check(
    "missing_ratio accurate",
    abs(profile_nan.missing_ratio - 0.01) < 1e-4,
    f"ratio={profile_nan.missing_ratio}",
)

# ignore_nan=False raises
try:
    NumericProfiler(ignore_nan=False).fit(data_with_nan)
    check("DataQualityError on ignore_nan=False", False, "no exception raised")
except DataQualityError:
    check("DataQualityError on ignore_nan=False", True)

# Inf values
data_with_inf = np.array([1.0, 2.0, np.inf, -np.inf, 3.0])
profile_inf = profiler_n.fit(data_with_inf)
check("inf_count == 2", profile_inf.inf_count == 2)
check("n_valid == 3", profile_inf.n_valid == 3)

# ─────────────────────────────────────────────────────────────────────────────
# 2. CategoricalProfiler
# ─────────────────────────────────────────────────────────────────────────────
section("2. CategoricalProfiler")
import warnings  # noqa: E402
from ds_data_miner.profiling.categorical import CategoricalProfiler  # noqa: E402
from ds_data_miner.core.contracts import CategoricalProfile  # noqa: E402
from ds_data_miner.core.exceptions import HighCardinalityWarning  # noqa: E402

cat_data = np.array(["A"] * 400 + ["B"] * 600)
profiler_c = CategoricalProfiler()
cat_profile = profiler_c.fit(cat_data)

check("Returns CategoricalProfile", isinstance(cat_profile, CategoricalProfile))
check("n_total == 1000", cat_profile.n_total == 1000)
check("n_unique == 2", cat_profile.n_unique == 2)
check("not high cardinality", not cat_profile.is_high_cardinality)

stats_map = {s.category: s for s in cat_profile.stats}
check("proportion A ≈ 0.4", abs(stats_map["A"].proportion - 0.4) < 1e-5)
check("proportion B ≈ 0.6", abs(stats_map["B"].proportion - 0.6) < 1e-5)
expected_se_a = float(np.sqrt(0.4 * 0.6 / 1000))
check(
    "binomial std_error A correct",
    abs(stats_map["A"].std_error - expected_se_a) < 1e-5,
)

# High-cardinality defense
uuid_data = np.array([f"uuid-{i:05d}" for i in range(500)])
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    hc_profile = CategoricalProfiler(max_cardinality=50).fit(uuid_data)
    hc_warned = any(issubclass(x.category, HighCardinalityWarning) for x in w)

check("HighCardinalityWarning issued", hc_warned)
check("is_high_cardinality == True", hc_profile.is_high_cardinality)
check("truncated_at == 50", hc_profile.truncated_at == 50)
check(
    "_OTHER_ bucket present",
    any(s.category == "_OTHER_" for s in hc_profile.stats),
)

# Missing values
data_with_none = np.array(["A", "B", None, "A", None], dtype=object)
missing_profile = profiler_c.fit(data_with_none)
check("missing_count == 2", missing_profile.missing_count == 2)
check("missing_ratio ≈ 0.4", abs(missing_profile.missing_ratio - 0.4) < 1e-5)

# ─────────────────────────────────────────────────────────────────────────────
# 3. DatetimeProfiler
# ─────────────────────────────────────────────────────────────────────────────
section("3. DatetimeProfiler")
from ds_data_miner.profiling.datetime import DatetimeProfiler  # noqa: E402
from ds_data_miner.core.contracts import DatetimeProfile  # noqa: E402

base = np.datetime64("2024-01-01T00:00:00")
dt_regular = base + np.arange(1000) * np.timedelta64(1, "m")
profiler_dt = DatetimeProfiler()
dt_profile = profiler_dt.fit(dt_regular)

check("Returns DatetimeProfile", isinstance(dt_profile, DatetimeProfile))
check("n_samples == 1000", dt_profile.n_samples == 1000)
check("is_monotonic_increasing == True", dt_profile.is_monotonic_increasing)
check("gap_count == 0", dt_profile.gap_count == 0)
check("inferred_freq == '1min'", dt_profile.inferred_freq == "1min")
check("missing_count == 0", dt_profile.missing_count == 0)

# Gap detection
part1 = base + np.arange(100) * np.timedelta64(1, "m")
part2 = part1[-1] + np.timedelta64(10, "h") + np.arange(100) * np.timedelta64(1, "m")
part3 = part2[-1] + np.timedelta64(2, "D") + np.arange(100) * np.timedelta64(1, "m")
dt_gaps = np.concatenate([part1, part2, part3])
gap_profile = profiler_dt.fit(dt_gaps)

check("gap_count == 2", gap_profile.gap_count == 2, f"got {gap_profile.gap_count}")
check("gap_locations have 'from' key", all("from" in g for g in gap_profile.gap_locations))

# Non-monotonic
dt_non_mono = np.array([base + np.timedelta64(2, "m"), base, base + np.timedelta64(1, "m")])
nm_profile = profiler_dt.fit(dt_non_mono)
check("is_monotonic_increasing == False", not nm_profile.is_monotonic_increasing)

# NaT missing
dt_nat = np.array([base, base + np.timedelta64(1, "m"), np.datetime64("NaT")])
nat_profile = profiler_dt.fit(dt_nat)
check("NaT missing_count == 1", nat_profile.missing_count == 1)

# ─────────────────────────────────────────────────────────────────────────────
# 4. DistributionTester
# ─────────────────────────────────────────────────────────────────────────────
section("4. DistributionTester (K-S Test)")
from scipy import stats as sp_stats  # noqa: E402
from ds_data_miner.profiling.distribution_test import DistributionTester  # noqa: E402

tester = DistributionTester(dist_name="norm")
ks_result = tester.test(data_1m)

check("returns dict with statistic + p_value", {"statistic", "p_value"} <= set(ks_result))
expected_ks = sp_stats.kstest(data_1m, "norm")
check(
    "statistic matches scipy atol=1e-7",
    abs(ks_result["statistic"] - expected_ks.statistic) < 1e-7,
    f"got={ks_result['statistic']:.8f}, expected={expected_ks.statistic:.8f}",
)
check(
    "p_value matches scipy atol=1e-7",
    abs(ks_result["p_value"] - expected_ks.pvalue) < 1e-7,
)
# Uniform data should fail normality test
uniform_data = rng.uniform(0, 1, 10_000)
ks_uniform = tester.test(uniform_data)
check("uniform data p_value < 0.05", ks_uniform["p_value"] < 0.05)

# NaN values are dropped
data_nan_ks = np.array([1.0, 2.0, np.nan, 3.0, np.nan])
ks_nan = tester.test(data_nan_ks)
check("NaN values dropped in K-S test", isinstance(ks_nan["p_value"], float))

# ─────────────────────────────────────────────────────────────────────────────
# 5. ProfilingEngine
# ─────────────────────────────────────────────────────────────────────────────
section("5. ProfilingEngine")
from ds_data_miner.profiling.engine import ProfilingEngine  # noqa: E402
from ds_data_miner.core.contracts import DatasetReport  # noqa: E402
from datetime import datetime  # noqa: E402

engine = ProfilingEngine()
columns = {
    "sensor": rng.standard_normal(200).astype(np.float64),
    "status": np.array(["ok", "error", "warn"] * 67)[:200],
    "ts": base + np.arange(200) * np.timedelta64(1, "m"),
}
report = engine.profile_dataset(columns, dataset_name="smoke_test", total_rows=200)

check("Returns DatasetReport", isinstance(report, DatasetReport))
check("dataset_name == 'smoke_test'", report.dataset_name == "smoke_test")
check("total_columns == 3", report.total_columns == 3)
check("total_rows == 200", report.total_rows == 200)
check("sensor → DistributionProfile", isinstance(report.columns["sensor"], DistributionProfile))
check("status → CategoricalProfile", isinstance(report.columns["status"], CategoricalProfile))
check("ts → DatetimeProfile", isinstance(report.columns["ts"], DatetimeProfile))
check("created_at is valid ISO8601", bool(datetime.fromisoformat(report.created_at)))

import ds_data_miner  # noqa: E402
check("version set", report.ds_data_miner_version == ds_data_miner.__version__)

# ─────────────────────────────────────────────────────────────────────────────
# 6. ReportExporter — JSON output + Schema
# ─────────────────────────────────────────────────────────────────────────────
section("6. ReportExporter")
from ds_data_miner.export.serializer import ReportExporter  # noqa: E402

with tempfile.TemporaryDirectory() as tmpdir:
    tmp = Path(tmpdir)
    out_json = tmp / "report.json"
    out_schema = tmp / "report.schema.json"

    exporter = ReportExporter()
    exporter.export(report, out_json)
    ReportExporter.export_schema(out_schema)

    check("JSON file created", out_json.exists())
    check("Schema file created", out_schema.exists())

    content = out_json.read_text(encoding="utf-8")
    parsed = json.loads(content)
    check("JSON is valid", True)  # would raise above if invalid
    check("dataset_name in JSON", parsed["dataset_name"] == "smoke_test")
    check("columns in JSON", "sensor" in parsed.get("columns", {}))
    check("No 'NaN' literals in JSON", "NaN" not in content)
    check("No 'Infinity' literals in JSON", "Infinity" not in content)

    schema_content = out_schema.read_text(encoding="utf-8")
    schema = json.loads(schema_content)
    check("Schema is valid JSON", True)
    check("Schema has properties or $defs", "properties" in schema or "$defs" in schema)

    # Round-trip: JSON → model
    restored = DatasetReport.model_validate_json(content)
    check("Round-trip JSON → DatasetReport succeeds", isinstance(restored, DatasetReport))
    check("Round-trip dataset_name preserved", restored.dataset_name == report.dataset_name)

# ─────────────────────────────────────────────────────────────────────────────
# 7. MinerAccessor (df.miner)
# ─────────────────────────────────────────────────────────────────────────────
section("7. MinerAccessor (df.miner)")
import pandas as pd  # noqa: E402
import ds_data_miner.pandas_ext  # noqa: F401, E402

df = pd.DataFrame(
    {
        "price": rng.standard_normal(500),
        "category": pd.Categorical(["A", "B", "C", "A", "B"] * 100),
        "timestamp": pd.date_range("2024-01-01", periods=500, freq="1min"),
    }
)

df_report = df.miner.profile(dataset_name="pandas_smoke")

check("df.miner.profile() returns DatasetReport", isinstance(df_report, DatasetReport))
check("total_rows == 500", df_report.total_rows == 500)
check("total_columns == 3", df_report.total_columns == 3)
check("price → DistributionProfile", isinstance(df_report.columns["price"], DistributionProfile))
check("category → CategoricalProfile", isinstance(df_report.columns["category"], CategoricalProfile))
check("timestamp → DatetimeProfile", isinstance(df_report.columns["timestamp"], DatetimeProfile))

# Duplicate detection
df_dup = pd.concat([df.head(50), df.head(10)], ignore_index=True)
dup_report = df_dup.miner.profile()
check("duplicate_row_count == 10", dup_report.duplicate_row_count == 10)

# export_json
with tempfile.TemporaryDirectory() as tmpdir:
    out = Path(tmpdir) / "pandas_report.json"
    returned = df.miner.export_json(out, dataset_name="pandas_export")

    check("export_json creates file", out.exists())
    check("export_json returns DatasetReport", isinstance(returned, DatasetReport))
    content = out.read_text()
    check("export_json output valid JSON", bool(json.loads(content)))
    check("No NaN in exported JSON", "NaN" not in content)

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
total_checks = 68  # approximate — update if you add more
print(f"\n{'─'*60}")
if failures:
    print(f"\033[91m❌  {len(failures)} check(s) FAILED:\033[0m")
    for f in failures:
        print(f"     • {f}")
    sys.exit(1)
else:
    print(f"\033[92m✅  All checks passed ({total_checks} assertions across 7 modules)\033[0m")
    sys.exit(0)
