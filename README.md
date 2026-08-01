# ds-data-miner

> **EDA Profiling Engine** — Full-scan statistical analysis with standardized JSON output.
>
> The first part of a three-library trilogy. It ingests raw data, performs
> **strict full-table scans in local Python memory**, and exports statistical
> features, data-quality metrics, and native statistical errors as
> standardized **JSON**.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue.svg)](http://mypy-lang.org/)

---

## Table of Contents

1. [Why ds-data-miner?](#why-ds-data-miner)
2. [System Design — The Trilogy](#system-design--the-trilogy)
3. [Architecture Overview](#architecture-overview)
4. [Installation](#installation)
   - [Option A — pip (stable)](#option-a--pip-stable)
   - [Option B — uv (recommended for development)](#option-b--uv-recommended-for-development)
   - [Option C — from Git](#option-c--from-git)
5. [Quick Start](#quick-start)
   - [Step 1 — Profile a numeric array](#step-1--profile-a-numeric-array)
   - [Step 2 — Profile categorical data](#step-2--profile-categorical-data)
   - [Step 3 — Profile datetime columns](#step-3--profile-datetime-columns)
   - [Step 4 — Full-table scan with Pandas](#step-4--full-table-scan-with-pandas)
   - [Step 5 — Export to JSON](#step-5--export-to-json)
6. [Data Contracts (Output Schema)](#data-contracts-output-schema)
7. [Development Setup](#development-setup)
8. [Running Tests](#running-tests)
9. [Code Quality](#code-quality)
10. [Version Management](#version-management)
11. [API Documentation (Sphinx)](#api-documentation-sphinx)
12. [Project Structure](#project-structure)
13. [License](#license)

---

## Why ds-data-miner?

Most EDA tools couple **data scanning**, **visualization**, and **reporting**
into one monolithic package. This creates hard dependencies on Matplotlib and
heavy report frameworks even when you only need the numbers.

`ds-data-miner` solves this by doing **one thing well**:

- ✅ Performs a **strict, 100% full-table scan** — never samples
- ✅ Computes statistical features, data-quality indicators, and **native
  statistical errors** (SEM, confidence intervals, binomial std errors)
- ✅ Outputs everything as a clean, **standardized JSON** file
- ✅ Has a minimal core dependency footprint: `numpy`, `scipy`, `pydantic`

---

## System Design — The Trilogy

| Library | Role | Status |
|:---|:---|:---|
| **`ds-data-miner`** | EDA compute engine → outputs JSON | ✅ This library |
| `ds-data-miner-vis` | Reads JSON → renders Matplotlib plots | 🔜 Planned |
| `ds-data-miner-reporter` | Reads JSON → produces PDF/HTML reports | 🔜 Planned |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────┐
│  pandas_ext (Adapter Layer)                      │
│  df.miner.profile()  /  df.miner.export_json()  │
│  Deps: pandas + core + profiling                 │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────┐
│  profiling (Domain Layer)                        │
│  NumericProfiler / CategoricalProfiler /         │
│  DatetimeProfiler / ProfilingEngine              │
│  Deps: numpy + scipy + core only                 │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────┐
│  export (Export Layer)                           │
│  ReportExporter — JSON + Schema                  │
│  Deps: core only                                 │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────┐
│  core (Inner Core)                               │
│  Pydantic Contracts: DistributionProfile,        │
│  CategoricalProfile, DatetimeProfile,            │
│  DatasetReport, CategoryStats                    │
│  Deps: pydantic only                             │
└──────────────────────────────────────────────────┘
```

**Dependency rule:** Arrows point downward only. `core` never imports from
`profiling`; `profiling` never imports `pandas` or `matplotlib`.

---

## Installation

### Option A — pip (stable)

```bash
# Core only (numpy + scipy + pydantic)
pip install ds-data-miner

# With Pandas integration (enables df.miner accessor)
pip install "ds-data-miner[pandas]"
```

### Option B — uv (recommended for development)

[`uv`](https://github.com/astral-sh/uv) creates a fully isolated, reproducible
environment in seconds.

```bash
# Step 1 — Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Step 2 — Clone the repository
git clone https://github.com/your-org/ds-data-miner.git
cd ds-data-miner

# Step 3 — Create an isolated venv and install with all dev extras
uv venv .venv --python 3.11
uv pip install -e ".[dev,pandas]" --python .venv/bin/python

# Step 4 — Activate the environment
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows

# Step 5 — Verify the installation
python -c "import ds_data_miner; print(ds_data_miner.__version__)"
```

### Option C — from Git

```bash
pip install "git+https://github.com/your-org/ds-data-miner.git"

# With Pandas support
pip install "ds-data-miner[pandas] @ git+https://github.com/your-org/ds-data-miner.git"
```

---

## Quick Start

### Step 1 — Profile a numeric array

```python
import numpy as np
from ds_data_miner.profiling.numeric import NumericProfiler

# Create a profiler (ignore NaN by default; 95% CI)
profiler = NumericProfiler(ignore_nan=True, ci_level=0.95)

# Run full-scan analysis on 1 million data points
data = np.random.default_rng(42).standard_normal(1_000_000)
profile = profiler.fit(data)

# Access computed statistics
print(f"Mean:          {profile.mean:.4f}")
print(f"Std:           {profile.std:.4f}")
print(f"SEM:           {profile.sem:.6f}")       # Standard Error of the Mean
print(f"95% CI:        [{profile.ci_lower:.4f}, {profile.ci_upper:.4f}]")
print(f"Missing count: {profile.missing_count}")
print(f"Histogram bins: {len(profile.histogram_counts)} buckets")

# Serialize to JSON (NaN/Inf → null automatically)
print(profile.model_dump_json(indent=2))
```

### Step 2 — Profile categorical data

```python
import numpy as np
from ds_data_miner.profiling.categorical import CategoricalProfiler

data = np.array(["ok"] * 700 + ["error"] * 250 + ["warn"] * 50)
profiler = CategoricalProfiler(max_cardinality=100)  # high-cardinality guard
profile = profiler.fit(data)

for stat in profile.stats:
    print(
        f"  {stat.category:8s}  count={stat.count:4d}  "
        f"proportion={stat.proportion:.3f}  std_error={stat.std_error:.4f}"
    )
# ok        count= 700  proportion=0.700  std_error=0.0145
# error     count= 250  proportion=0.250  std_error=0.0137
# warn      count=  50  proportion=0.050  std_error=0.0069
```

> **High-cardinality guard:** If a column has more unique values than
> `max_cardinality`, the profiler automatically truncates to Top-N categories
> and merges the rest into `_OTHER_`, emitting a `HighCardinalityWarning`.

### Step 3 — Profile datetime columns

```python
import numpy as np
from ds_data_miner.profiling.datetime import DatetimeProfiler

base = np.datetime64("2024-01-01T00:00:00")
timestamps = base + np.arange(1440) * np.timedelta64(1, "m")  # 1 day of minutes

profiler = DatetimeProfiler(gap_threshold_factor=2.0)
profile = profiler.fit(timestamps)

print(f"Start:               {profile.start}")
print(f"End:                 {profile.end}")
print(f"Monotonic:           {profile.is_monotonic_increasing}")
print(f"Gap count:           {profile.gap_count}")
print(f"Inferred frequency:  {profile.inferred_freq}")   # "1min"
```

### Step 4 — Full-table scan with Pandas

```python
import pandas as pd
import ds_data_miner.pandas_ext  # registers df.miner accessor

df = pd.read_csv("sensor_data.csv", parse_dates=["timestamp"])

# One call profiles every column, auto-routes by dtype
report = df.miner.profile(dataset_name="sensor_data")

print(f"Rows:             {report.total_rows}")
print(f"Columns:          {report.total_columns}")
print(f"Duplicate rows:   {report.duplicate_row_count}")

# Access per-column profiles
numeric_col = report.columns["temperature"]
print(f"Temperature mean: {numeric_col.mean:.2f}")
print(f"Temperature SEM:  {numeric_col.sem:.4f}")
```

### Step 5 — Export to JSON

```python
import ds_data_miner.pandas_ext  # noqa: F401
import pandas as pd

df = pd.read_csv("sensor_data.csv", parse_dates=["timestamp"])

# One-shot: scan + export
df.miner.export_json("reports/sensor_report.json", dataset_name="sensor_data")
```

The exported file looks like:

```json
{
  "dataset_name": "sensor_data",
  "created_at": "2024-08-01T10:30:00+00:00",
  "ds_data_miner_version": "0.1.0",
  "total_rows": 10000,
  "total_columns": 4,
  "duplicate_row_count": 0,
  "duplicate_row_ratio": 0.0,
  "columns": {
    "temperature": {
      "mean": 22.31,
      "std": 3.14,
      "sem": 0.0314,
      "ci_lower": 22.25,
      "ci_upper": 22.37,
      "missing_count": 0,
      "missing_ratio": 0.0,
      ...
    }
  }
}
```

---

## Data Contracts (Output Schema)

| Contract | Produced by | Key fields |
|:---|:---|:---|
| `DistributionProfile` | `NumericProfiler` | `mean`, `std`, `sem`, `ci_lower/upper`, `histogram_bin_edges/counts`, `missing_ratio` |
| `CategoricalProfile` | `CategoricalProfiler` | `stats[].proportion`, `stats[].std_error`, `is_high_cardinality`, `missing_ratio` |
| `DatetimeProfile` | `DatetimeProfiler` | `is_monotonic_increasing`, `gap_count`, `gap_locations`, `inferred_freq` |
| `DatasetReport` | `ProfilingEngine` / `df.miner` | All columns + `duplicate_row_count`, `created_at`, version |

Export the JSON Schema for downstream validation:

```python
from ds_data_miner.export.serializer import ReportExporter

ReportExporter.export_schema("reports/report.schema.json")
```

---

## Development Setup

**Prerequisites:** Python ≥ 3.10, [`uv`](https://github.com/astral-sh/uv)

```bash
# Step 1 — Clone
git clone https://github.com/your-org/ds-data-miner.git
cd ds-data-miner

# Step 2 — Create an isolated virtual environment
uv venv .venv --python 3.11

# Step 3 — Install the package in editable mode with all extras
uv pip install -e ".[dev,pandas]" --python .venv/bin/python

# Step 4 — Activate
source .venv/bin/activate     # macOS / Linux
# .venv\Scripts\activate      # Windows

# Step 5 — Confirm everything works
python smoke_test.py
```

---

## Running Tests

```bash
# Run all tests (quiet output)
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=ds_data_miner --cov-report=term-missing

# Run only a specific module's tests
pytest tests/test_profiling/test_numeric.py -v

# Skip slow tests (marked with @pytest.mark.slow)
pytest -m "not slow"

# Full multi-Python CI matrix via tox
tox
```

---

## Code Quality

```bash
# Lint (check only)
ruff check src/ tests/

# Lint + auto-fix safe issues
ruff check --fix src/ tests/

# Format (check only)
ruff format --check src/ tests/

# Format in-place
ruff format src/ tests/

# Static type checking
mypy src/

# Run lint env via tox (mirrors CI)
tox -e lint
tox -e typecheck
```

---

## Version Management

Version is managed by [`bump-my-version`](https://github.com/callowayproject/bump-my-version).
It simultaneously updates `pyproject.toml` **and** `src/ds_data_miner/__init__.py`,
then creates a Git commit and tag.

```bash
# Patch release: 0.1.0 → 0.1.1
bump-my-version bump patch

# Minor release: 0.1.0 → 0.2.0
bump-my-version bump minor

# Major release: 0.1.0 → 1.0.0
bump-my-version bump major

# Preview without committing
bump-my-version bump patch --dry-run --verbose
```

---

## API Documentation (Sphinx)

Build the full HTML API docs locally:

```bash
# Step 1 — Install docs extras
pip install -e ".[docs]"

# Step 2 — Build
cd docs/
make html

# Step 3 — Open in browser
open _build/html/index.html          # macOS
xdg-open _build/html/index.html      # Linux
start _build\html\index.html         # Windows

# Or use tox
tox -e docs
```

---

## Project Structure

```
ds-data-miner/
│
├── pyproject.toml          ← PEP 621 metadata + tool configs
├── tox.ini                 ← CI matrix: py310–py313, lint, typecheck, docs
├── README.md
├── smoke_test.py           ← End-to-end functional verification script
│
├── src/ds_data_miner/
│   ├── __init__.py         ← __version__
│   ├── py.typed            ← PEP 561 marker (type-checking support)
│   │
│   ├── core/               ← Inner core: zero external deps (pydantic only)
│   │   ├── contracts.py    ← All Pydantic models (DistributionProfile etc.)
│   │   └── exceptions.py   ← DataQualityError, HighCardinalityWarning
│   │
│   ├── profiling/          ← Domain layer: numpy + scipy only
│   │   ├── base.py         ← BaseProfiler ABC
│   │   ├── numeric.py      ← NumericProfiler
│   │   ├── categorical.py  ← CategoricalProfiler (+ high-cardinality guard)
│   │   ├── datetime.py     ← DatetimeProfiler
│   │   ├── distribution_test.py  ← DistributionTester (K-S test)
│   │   └── engine.py       ← ProfilingEngine (orchestrator)
│   │
│   ├── export/             ← Export layer: core only
│   │   └── serializer.py   ← ReportExporter (JSON + Schema)
│   │
│   └── pandas_ext/         ← Adapter layer: pandas (optional)
│       └── accessor.py     ← df.miner accessor
│
├── tests/
│   ├── conftest.py         ← Shared fixtures (arrays, DataFrames)
│   ├── test_core/          ← Contract serialization & round-trip tests
│   ├── test_profiling/     ← Per-profiler unit tests (scipy baseline)
│   ├── test_export/        ← JSON export & schema tests
│   └── test_adapters/      ← Pandas accessor integration tests
│
└── docs/                   ← Sphinx API documentation
    ├── conf.py
    ├── index.rst
    └── api/
```

---

## License

MIT © ds-data-miner contributors
