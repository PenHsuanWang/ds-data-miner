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

**For Data Scientists & AI Agents**
1. [What questions can this library answer?](#what-questions-can-this-library-answer)
2. [Quick Start — choose your entry point](#quick-start--choose-your-entry-point)
3. [Output Field Reference (all fields, all types)](#output-field-reference)
4. [Error Handling & Edge Cases](#error-handling--edge-cases)

**For Developers**

5. [Why ds-data-miner?](#why-ds-data-miner)
6. [System Design — The Trilogy](#system-design--the-trilogy)
7. [Architecture Overview](#architecture-overview)
8. [Installation](#installation)
9. [Development Setup](#development-setup)
10. [Running Tests](#running-tests)
11. [Code Quality](#code-quality)
12. [How to Add a New Profiler](#how-to-add-a-new-profiler)
13. [Docstring & Typing Standards](#docstring--typing-standards)
14. [Branch & PR Workflow](#branch--pr-workflow)
15. [Version Management](#version-management)
16. [API Documentation (Sphinx)](#api-documentation-sphinx)
17. [Project Structure](#project-structure)
18. [License](#license)

---

## What questions can this library answer?

`ds-data-miner` answers **statistical profiling questions** about raw data columns.
It does NOT visualize, does NOT train models, does NOT sample.

| Question | Column type | Key output field |
|:---|:---|:---|
| What is the mean / median / std of this column? | numeric | `mean`, `median`, `std` |
| How uncertain is the mean estimate? | numeric | `sem`, `ci_lower`, `ci_upper` |
| Is the distribution skewed or heavy-tailed? | numeric | `skewness`, `kurtosis` |
| What does the value distribution look like? | numeric | `histogram_bin_edges`, `histogram_counts` |
| How many values are missing or infinite? | numeric | `missing_count`, `missing_ratio`, `inf_count` |
| What are the most common categories? | categorical | `stats[].category`, `stats[].count`, `stats[].proportion` |
| How reliable is each category's proportion? | categorical | `stats[].std_error` (binomial SE) |
| Does this column have too many unique values? | categorical | `is_high_cardinality`, `truncated_at` |
| What is the date range of this time column? | datetime | `start`, `end`, `duration_seconds` |
| Are timestamps monotonically increasing? | datetime | `is_monotonic_increasing` |
| Are there gaps in this time series? | datetime | `gap_count`, `gap_locations` |
| What is the sampling frequency? | datetime | `inferred_freq` |
| Does the full dataset have duplicate rows? | any | `duplicate_row_count`, `duplicate_row_ratio` |

---

## Quick Start — choose your entry point

### Decision tree

```
Do you have a pandas.DataFrame?
│
├─ YES ──► df.miner.profile()            # profiles every column automatically
│          df.miner.export_json(path)    # scan + write JSON in one call
│
└─ NO (raw numpy arrays)
    │
    ├─ Single column, numeric dtype  ──► NumericProfiler().fit(array)
    ├─ Single column, string/object  ──► CategoricalProfiler().fit(array)
    ├─ Single column, datetime64     ──► DatetimeProfiler().fit(array)
    └─ Multiple columns as dict      ──► ProfilingEngine().profile_dataset(dict)
```

### Option 1 — Pandas (recommended, handles all dtype routing)

```python
import pandas as pd
import ds_data_miner.pandas_ext  # noqa: F401 — must import once to activate df.miner

df = pd.read_csv("sensor_data.csv", parse_dates=["timestamp"])

# Profile every column (auto-routes by dtype)
report = df.miner.profile(dataset_name="sensor_data")

# Dataset-level quality
print(report.total_rows)              # int
print(report.total_columns)           # int
print(report.duplicate_row_count)     # int — fully-duplicated rows
print(report.duplicate_row_ratio)     # float [0.0, 1.0]
print(report.created_at)             # ISO 8601 UTC timestamp

# Per-column: access by column name — type depends on dtype
temp = report.columns["temperature"]  # DistributionProfile (numeric)
print(temp.mean, temp.std, temp.sem)
print(temp.ci_lower, temp.ci_upper)   # 95% confidence interval

status = report.columns["status"]     # CategoricalProfile (string)
for stat in status.stats:
    print(stat.category, stat.proportion, stat.std_error)

ts = report.columns["timestamp"]      # DatetimeProfile (datetime)
print(ts.inferred_freq, ts.gap_count)

# One-shot: scan + write to JSON file
df.miner.export_json("reports/sensor_report.json", dataset_name="sensor_data")
```

### Option 2 — NumPy: profile a single numeric column

```python
import numpy as np
from ds_data_miner.profiling.numeric import NumericProfiler

data = np.random.default_rng(42).standard_normal(1_000_000)

profile = NumericProfiler(ignore_nan=True, ci_level=0.95).fit(data)

print(profile.mean)            # float
print(profile.std)             # population std (ddof=0)
print(profile.sem)             # standard error of the mean
print(profile.ci_lower)        # lower 95% CI bound
print(profile.ci_upper)        # upper 95% CI bound
print(profile.skewness)        # Fisher-corrected skewness
print(profile.kurtosis)        # Fisher-corrected excess kurtosis
print(profile.q25, profile.q75)
print(profile.missing_count)   # NaN count
print(profile.inf_count)       # Inf/-Inf count

# Pre-computed histogram (use directly for plotting)
edges  = profile.histogram_bin_edges  # list[float], len = n_bins + 1
counts = profile.histogram_counts     # list[int],   len = n_bins

# Serialize to JSON (NaN/Inf → null automatically)
json_str = profile.model_dump_json(indent=2)
```

### Option 3 — NumPy: profile a single categorical column

```python
import numpy as np
from ds_data_miner.profiling.categorical import CategoricalProfiler

data = np.array(["ok"] * 700 + ["error"] * 250 + ["warn"] * 50)
profile = CategoricalProfiler(max_cardinality=100).fit(data)

# Stats are sorted by frequency (descending)
for stat in profile.stats:
    print(f"{stat.category:8s}  count={stat.count}  "
          f"proportion={stat.proportion:.3f}  ±{stat.std_error:.4f}")
# ok        count=700  proportion=0.700  ±0.0145
# error     count=250  proportion=0.250  ±0.0137
# warn      count=50   proportion=0.050  ±0.0069

print(profile.n_unique)             # int: total unique before truncation
print(profile.is_high_cardinality)  # bool: True if truncated
print(profile.truncated_at)         # int | None: Top-N threshold
print(profile.missing_count)        # int: None/NaN values
```

> **High-cardinality guard:** If `n_unique > max_cardinality`, the profiler
> automatically truncates to Top-N categories, merges the rest into `_OTHER_`,
> and emits a `HighCardinalityWarning`. Profiling always completes — it never
> raises on high cardinality.

### Option 4 — NumPy: profile a datetime column

```python
import numpy as np
from ds_data_miner.profiling.datetime import DatetimeProfiler

base = np.datetime64("2024-01-01T00:00:00")
ts   = base + np.arange(1440) * np.timedelta64(1, "m")

profile = DatetimeProfiler(gap_threshold_factor=2.0).fit(ts)

print(profile.start)                    # ISO 8601 string
print(profile.end)                      # ISO 8601 string
print(profile.duration_seconds)         # float
print(profile.is_monotonic_increasing)  # bool
print(profile.inferred_freq)            # "1min" | "1h" | "1d" | None
print(profile.gap_count)               # int
for gap in profile.gap_locations:
    # Each gap: {"from": str, "to": str, "duration_seconds": float}
    print(gap["from"], "→", gap["to"], f"({gap['duration_seconds']}s)")
print(profile.missing_count)           # NaT count
```

### Option 5 — Export JSON Schema (for downstream validation)

```python
from ds_data_miner.export.serializer import ReportExporter

# Write JSON Schema — use to validate report.json in consumer libraries
ReportExporter.export_schema("schemas/report.schema.json")
```

### Sample JSON output

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
      "mean": 22.31, "variance": 9.86, "std": 3.14,
      "median": 22.15, "min": 10.1, "max": 35.7,
      "q25": 20.1, "q75": 24.5,
      "skewness": 0.12, "kurtosis": -0.05,
      "sem": 0.0314, "ci_lower": 22.25, "ci_upper": 22.37,
      "histogram_bin_edges": [10.1, 12.5, "..."],
      "histogram_counts": [42, 130, "..."],
      "n_samples": 10000, "n_valid": 9980,
      "missing_count": 20, "missing_ratio": 0.002,
      "inf_count": 0
    },
    "status": {
      "stats": [
        {"category": "ok",    "count": 8500, "proportion": 0.85, "std_error": 0.0036},
        {"category": "error", "count": 1200, "proportion": 0.12, "std_error": 0.0033},
        {"category": "warn",  "count": 300,  "proportion": 0.03, "std_error": 0.0017}
      ],
      "n_total": 10000, "n_unique": 3,
      "missing_count": 0, "missing_ratio": 0.0,
      "is_high_cardinality": false, "truncated_at": null
    }
  }
}
```

---

## Output Field Reference

All output types are **immutable Pydantic models**.
Convert with `model.model_dump_json()` (JSON string) or `model.model_dump()` (dict).
All `float` fields are serialized as JSON `null` when the value is `NaN` or `Inf`.

### `DistributionProfile` — numeric columns

| Field | Type | Description |
|:---|:---|:---|
| `mean` | `float` | Arithmetic mean of valid (finite) values |
| `variance` | `float` | Population variance (`ddof=0`) |
| `std` | `float` | Population standard deviation (`ddof=0`) |
| `median` | `float` | 50th percentile |
| `min` | `float` | Minimum finite value |
| `max` | `float` | Maximum finite value |
| `q25` | `float` | 25th percentile (1st quartile) |
| `q75` | `float` | 75th percentile (3rd quartile) |
| `skewness` | `float` | Fisher-corrected skewness (`scipy.stats.skew`) |
| `kurtosis` | `float` | Fisher-corrected excess kurtosis (`scipy.stats.kurtosis`) |
| `sem` | `float` | Standard Error of the Mean = `std_ddof1 / sqrt(n_valid)` |
| `ci_lower` | `float` | Lower bound of symmetric CI around the mean |
| `ci_upper` | `float` | Upper bound of symmetric CI around the mean |
| `histogram_bin_edges` | `list[float]` | Bin boundaries; length = `n_bins + 1` |
| `histogram_counts` | `list[int]` | Per-bin counts; length = `n_bins` |
| `n_samples` | `int` | Total elements including NaN/Inf |
| `n_valid` | `int` | Finite elements used in all statistics |
| `missing_count` | `int` | Number of `NaN` values |
| `missing_ratio` | `float` | `missing_count / n_samples`, rounded to 6dp |
| `inf_count` | `int` | Number of `Inf` / `-Inf` values |

### `CategoricalProfile` — string / object / category columns

| Field | Type | Description |
|:---|:---|:---|
| `stats` | `list[CategoryStats]` | Per-category stats, sorted by frequency descending |
| `stats[].category` | `str` | Category label (`"_OTHER_"` for merged remainder) |
| `stats[].count` | `int` | Absolute count |
| `stats[].proportion` | `float` | `count / n_total`, rounded to 6dp |
| `stats[].std_error` | `float` | Binomial SE = `sqrt(p*(1-p)/N)`, rounded to 6dp |
| `n_total` | `int` | Total non-missing elements |
| `n_unique` | `int` | Total unique values **before** any truncation |
| `missing_count` | `int` | Number of `None` / `NaN` values |
| `missing_ratio` | `float` | `missing_count / n_samples`, rounded to 6dp |
| `is_high_cardinality` | `bool` | `True` when `n_unique > max_cardinality` |
| `truncated_at` | `int \| None` | Top-N threshold used, or `None` if not truncated |

### `DatetimeProfile` — `datetime64` columns

| Field | Type | Description |
|:---|:---|:---|
| `start` | `str` | ISO 8601 string of the earliest timestamp |
| `end` | `str` | ISO 8601 string of the latest timestamp |
| `duration_seconds` | `float` | Total span: `(end - start)` in seconds |
| `is_monotonic_increasing` | `bool` | `True` if original-order timestamps are non-decreasing |
| `gap_count` | `int` | Number of detected temporal gaps |
| `gap_locations` | `list[dict]` | `[{"from": str, "to": str, "duration_seconds": float}]` |
| `inferred_freq` | `str \| None` | Human-readable frequency: `"1min"`, `"1h"`, `"1d"`, etc. |
| `n_samples` | `int` | Total elements including `NaT` |
| `missing_count` | `int` | Number of `NaT` values |
| `missing_ratio` | `float` | `missing_count / n_samples`, rounded to 6dp |

### `DatasetReport` — top-level container

| Field | Type | Description |
|:---|:---|:---|
| `dataset_name` | `str` | User-supplied name |
| `created_at` | `str` | ISO 8601 UTC timestamp of scan |
| `ds_data_miner_version` | `str` | Library version that produced this report |
| `total_rows` | `int` | Total rows in the dataset |
| `total_columns` | `int` | Number of columns profiled |
| `duplicate_row_count` | `int` | Fully-duplicated rows (all columns identical) |
| `duplicate_row_ratio` | `float` | `duplicate_row_count / total_rows`, rounded to 6dp |
| `columns` | `dict[str, DistributionProfile \| CategoricalProfile \| DatetimeProfile]` | Per-column profiles |

---

## Error Handling & Edge Cases

Understanding how the library behaves on imperfect data is critical for
production use.

| Situation | Behavior | Exception / Warning |
|:---|:---|:---|
| Empty array `[]` | **Raises** immediately | `DataQualityError` |
| All-NaN array (numeric) | **Raises** after filtering | `DataQualityError` |
| NaN present, `ignore_nan=False` | **Raises** | `DataQualityError` |
| NaN present, `ignore_nan=True` | Silently excluded; counted in `missing_count` | — |
| Inf / -Inf values | Always excluded from stats; counted in `inf_count` | — |
| All-`None` categorical array | **Raises** | `DataQualityError` |
| Categorical `n_unique > max_cardinality` | Top-N kept; rest → `_OTHER_`; **completes** | `HighCardinalityWarning` |
| All-`NaT` datetime array | **Raises** | `DataQualityError` |
| Non-datetime64 passed to `DatetimeProfiler` | **Raises** | `TypeError` |
| Single-element array (numeric) | `sem=0.0`, `ci_lower=ci_upper=mean` | — |

```python
from ds_data_miner.core.exceptions import DataQualityError, HighCardinalityWarning
import warnings

# Catch DataQualityError on bad input
try:
    profile = NumericProfiler().fit(np.array([]))
except DataQualityError as e:
    print(f"Bad data: {e}")

# Catch HighCardinalityWarning without stopping
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    profile = CategoricalProfiler(max_cardinality=5).fit(large_cardinality_array)
    if any(issubclass(x.category, HighCardinalityWarning) for x in w):
        print("Column was truncated — check is_high_cardinality and truncated_at")
```

---

## Why ds-data-miner?

Most EDA tools couple **data scanning**, **visualization**, and **reporting**
into one monolithic package. This creates hard dependencies on Matplotlib and
heavy report frameworks even when you only need the numbers.

`ds-data-miner` solves this by doing **one thing well**:

- ✅ Performs a **strict, 100% full-table scan** — never samples
- ✅ Computes statistical features, data-quality indicators, and **native
  statistical errors** (SEM, confidence intervals, binomial std errors)
- ✅ All operations are vectorised via `numpy`/`scipy` — no Python loops
- ✅ Outputs everything as a clean, **standardized JSON** file
- ✅ Minimal core dependency footprint: `numpy`, `scipy`, `pydantic`
- ✅ `pandas` is an **optional** dependency — `core` and `profiling` are pure NumPy

---

## System Design — The Trilogy

| Library | Role | Status |
|:---|:---|:---|
| **`ds-data-miner`** | EDA compute engine → outputs JSON | ✅ This library |
| `ds-data-miner-vis` | Reads JSON → renders Matplotlib plots | 🔜 Planned |
| `ds-data-miner-reporter` | Reads JSON → produces PDF/HTML reports | 🔜 Planned |

The JSON report produced by `ds-data-miner` is the **contract** between the three libraries.
Consumer libraries validate against the JSON Schema (`report.schema.json`).

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

**Dependency rule:** Arrows point downward only.
- `core` never imports from `profiling`, `export`, or `pandas_ext`
- `profiling` never imports `pandas` or `matplotlib`
- Violating this is a CI-failing lint error

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

# Step 3 — Create isolated venv + install with all dev extras
uv venv .venv --python 3.11
uv pip install -e ".[dev,pandas]" --python .venv/bin/python

# Step 4 — Activate
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows

# Step 5 — Verify
python -c "import ds_data_miner; print(ds_data_miner.__version__)"
```

### Option C — from Git

```bash
pip install "git+https://github.com/your-org/ds-data-miner.git"
pip install "ds-data-miner[pandas] @ git+https://github.com/your-org/ds-data-miner.git"
```

---

## Development Setup

**Prerequisites:** Python ≥ 3.10, [`uv`](https://github.com/astral-sh/uv)

```bash
# Step 1 — Clone
git clone https://github.com/your-org/ds-data-miner.git
cd ds-data-miner

# Step 2 — Create isolated virtual environment
uv venv .venv --python 3.11

# Step 3 — Install in editable mode with all extras
uv pip install -e ".[dev,pandas,docs]" --python .venv/bin/python

# Step 4 — Activate
source .venv/bin/activate     # macOS / Linux
# .venv\Scripts\activate      # Windows

# Step 5 — Confirm everything works
python smoke_test.py           # end-to-end functional check (all 7 modules)
pytest                         # 80 unit/integration tests
```

---

## Running Tests

```bash
# Run all tests (quiet)
pytest

# Verbose with coverage report
pytest -v --cov=ds_data_miner --cov-report=term-missing

# Run only one module
pytest tests/test_profiling/test_numeric.py -v

# Skip slow tests
pytest -m "not slow"

# Full multi-Python CI matrix (py3.10–3.13 + lint + typecheck + docs)
tox
```

The test suite requires ≥ 85% coverage to pass (currently at **95.7%**).

---

## Code Quality

All three checks must pass before any commit is merged:

```bash
# Lint (check only — mirrors CI)
ruff check src/ tests/

# Lint + auto-fix safe issues
ruff check --fix src/ tests/

# Format check
ruff format --check src/ tests/

# Format in-place
ruff format src/ tests/

# Static type checking
mypy src/

# All-in-one via tox
tox -e lint
tox -e typecheck
```

---

## How to Add a New Profiler

Follow this checklist to add a new column profiler (e.g. `BinaryProfiler`):

1. **Define the output contract** in [`src/ds_data_miner/core/contracts.py`](src/ds_data_miner/core/contracts.py):

   ```python
   class BinaryProfile(BaseModel, frozen=True):
       """Output contract for binary (0/1 or bool) columns."""
       true_count: int
       false_count: int
       true_ratio: float
       ...
   ```

2. **Implement the profiler** in a new file `src/ds_data_miner/profiling/binary.py`:
   - Inherit from `BaseProfiler`
   - Implement `def fit(self, data: np.ndarray) -> BinaryProfile`
   - Use only `numpy`/`scipy` — no `pandas`, no Python loops
   - Add a module-level docstring with the **Agent Usage Decision Tree**

3. **Add dtype routing** in [`src/ds_data_miner/profiling/engine.py`](src/ds_data_miner/profiling/engine.py):

   ```python
   def _route(self, data: np.ndarray) -> ...:
       if np.issubdtype(data.dtype, np.bool_):
           return self.binary_profiler
       ...
   ```

4. **Update the Pandas adapter** in [`src/ds_data_miner/pandas_ext/accessor.py`](src/ds_data_miner/pandas_ext/accessor.py) to convert the new dtype.

5. **Export from `profiling/__init__.py`** and update `DatasetReport.columns` union type.

6. **Write tests** in `tests/test_profiling/test_binary.py` covering:
   - Happy path
   - Missing values
   - Edge cases (single element, all-missing)
   - Scipy/numpy baseline comparison

7. **Update the Sphinx API docs** in [`docs/api/profiling.rst`](docs/api/profiling.rst).

---

## Docstring & Typing Standards

All code must follow these standards (enforced by `mypy --strict` and `ruff`):

**Typing — Python 3.10+ union syntax:**

```python
# ✅ Correct
def fit(self, data: np.ndarray, threshold: int | None = None) -> DistributionProfile: ...

# ❌ Wrong — do not use
from typing import Optional, Union
def fit(self, data: np.ndarray, threshold: Optional[int] = None) -> DistributionProfile: ...
```

**Docstrings — Sphinx reST format:**

```python
def fit(self, data: np.ndarray) -> DistributionProfile:
    """Full-scan profile of a 1-D numeric array.

    One-line summary. Then a longer explanation if needed.

    :param data: 1-D NumPy array of numeric dtype.
    :return: Frozen :class:`~ds_data_miner.core.contracts.DistributionProfile`.
    :raises DataQualityError: If data is empty or entirely NaN.

    Example::

        profile = NumericProfiler().fit(np.array([1.0, 2.0, 3.0]))
        print(profile.mean)  # 2.0
    """
```

Rules:
- Do NOT add `:type param:` tags — types come from annotations
- Cross-reference with `:class:`~fully.qualified.ClassName`` (tilde strips the path in rendered docs)
- Every public class and method must have a docstring
- Include at least one `Example::` block on every public class

---

## Branch & PR Workflow

```
main   ← stable releases (protected, requires CI + 1 approval)
dev    ← integration branch (requires CI)
feat/* ← feature branches (branch from dev, merge into dev)
fix/*  ← bug fix branches (branch from dev or main)
```

**Step-by-step PR process:**

```bash
# Step 1 — Branch from dev
git checkout dev && git pull
git checkout -b feat/binary-profiler

# Step 2 — Develop + test
# ... write code ...
pytest && ruff check src/ tests/ && mypy src/

# Step 3 — Run smoke test
python smoke_test.py

# Step 4 — Push and open PR → targeting dev
git push -u origin feat/binary-profiler
# Open PR on GitHub: base=dev, compare=feat/binary-profiler

# Step 5 — CI must pass (all 5 jobs: lint, typecheck, test matrix, docs, smoke)
# Step 6 — 1 reviewer approval required
# Step 7 — Squash-merge into dev
```

**Merging `dev` → `main` (releases only):**

```bash
# Open a PR: base=main, compare=dev
# All CI must pass + 1 approval
# After merge, tag a release:
bump-my-version bump patch   # or minor/major
git push && git push --tags   # triggers the release workflow
```

---

## Version Management

Version is managed by [`bump-my-version`](https://github.com/callowayproject/bump-my-version).
It simultaneously updates `pyproject.toml` **and** `src/ds_data_miner/__init__.py`,
then creates a Git commit and tag.

```bash
# Patch release: 0.1.0 → 0.1.1  (bug fixes)
bump-my-version bump patch

# Minor release: 0.1.0 → 0.2.0  (new features, backward-compatible)
bump-my-version bump minor

# Major release: 0.1.0 → 1.0.0  (breaking changes to output schema)
bump-my-version bump major

# Preview without committing
bump-my-version bump patch --dry-run --verbose
```

> **When to bump major:** Any change to the `DatasetReport` JSON structure that
> removes or renames a field is a **breaking change** and requires a major version bump.
> Adding new fields is backward-compatible (minor).

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

# Live-reload (requires: pip install sphinx-autobuild)
make livehtml                        # opens browser at localhost:8888
```

The docs landing page ([`docs/index.rst`](docs/index.rst)) contains the full
**AI Agent Usage Guide** with decision tree, task→function quick reference,
and 6 runnable recipes.

---

## Project Structure

```
ds-data-miner/
│
├── pyproject.toml          ← PEP 621 metadata + tool configs (ruff, mypy, pytest, bumpversion)
├── tox.ini                 ← CI matrix: py310–py313, lint, typecheck, docs
├── README.md               ← This file
├── smoke_test.py           ← End-to-end functional verification (all 7 modules, ~68 checks)
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml          ← PR gate: lint, typecheck, test matrix, docs, smoke
│   │   └── release.yml     ← PyPI publish on tag push (Trusted Publishing)
│   ├── CODEOWNERS          ← Auto-assign reviewers
│   └── pull_request_template.md
│
├── src/ds_data_miner/
│   ├── __init__.py         ← __version__ = "0.1.0"
│   ├── py.typed            ← PEP 561 marker (type-checking support for consumers)
│   │
│   ├── core/               ← Inner core — zero external deps (pydantic only)
│   │   ├── contracts.py    ← All Pydantic output models (DistributionProfile, etc.)
│   │   └── exceptions.py   ← DataQualityError, HighCardinalityWarning
│   │
│   ├── profiling/          ← Domain layer — numpy + scipy only
│   │   ├── base.py         ← BaseProfiler ABC
│   │   ├── numeric.py      ← NumericProfiler
│   │   ├── categorical.py  ← CategoricalProfiler (+ high-cardinality guard)
│   │   ├── datetime.py     ← DatetimeProfiler (gaps, monotonicity, freq)
│   │   ├── distribution_test.py  ← DistributionTester (K-S test vs scipy)
│   │   └── engine.py       ← ProfilingEngine (dtype router + DatasetReport)
│   │
│   ├── export/             ← Export layer — core only
│   │   └── serializer.py   ← ReportExporter (JSON file + JSON Schema)
│   │
│   └── pandas_ext/         ← Adapter layer — pandas (optional extra)
│       └── accessor.py     ← df.miner accessor (profile + export_json)
│
├── tests/
│   ├── conftest.py         ← Shared fixtures (numpy arrays, DataFrames)
│   ├── test_core/          ← Contract serialization & round-trip tests
│   ├── test_profiling/     ← Per-profiler unit tests (scipy baseline comparisons)
│   ├── test_export/        ← JSON export & schema generation tests
│   └── test_adapters/      ← Pandas accessor integration tests
│
└── docs/                   ← Sphinx API documentation (Furo theme)
    ├── conf.py
    ├── index.rst            ← AI Agent Usage Guide + API toctree
    ├── Makefile
    ├── api/                 ← Per-module autodoc RST files
    ├── getting_started/
    └── dev/
```

---

## License

MIT © ds-data-miner contributors
