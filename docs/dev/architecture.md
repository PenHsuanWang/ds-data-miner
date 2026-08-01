# Architecture

## Layer Diagram

```
pandas_ext (Adapter)   ← optional, pandas only
       ↑
profiling (Domain)     ← numpy + scipy only
       ↑
export  (Export)       ← core only
       ↑
core    (Inner Core)   ← pydantic only
```

## Dependency Rules

- `core` has **no** internal imports from other layers
- `profiling` may import `core` but **never** `pandas` or `matplotlib`
- `export` may import `core` only
- `pandas_ext` may import `core`, `profiling`, and `export`

These rules are enforced at CI time using `ruff` import checks and can be
verified with:

```bash
ruff check src/ds_data_miner/profiling/ --select E402,TCH
```

## Data Flow

```
[User calls df.miner.profile()]
       │
       ▼
pandas_ext/accessor.py
  → converts each pd.Series to np.ndarray
  → detects duplicates
  → calls ProfilingEngine.profile_dataset()
       │
       ▼
profiling/engine.py  (ProfilingEngine)
  → routes each column by dtype
  → numeric dtype    → NumericProfiler.fit()
  → object/category  → CategoricalProfiler.fit()
  → datetime64       → DatetimeProfiler.fit()
       │
       ▼
core/contracts.py
  → DistributionProfile / CategoricalProfile / DatetimeProfile
  → aggregated into DatasetReport
       │
       ▼
export/serializer.py  (ReportExporter)
  → model_dump_json()  (NaN/Inf → null)
  → writes formatted JSON file
```
