# Quick Start

## 1 — Numeric Profiling

```python
import numpy as np
from ds_data_miner.profiling.numeric import NumericProfiler

data = np.random.default_rng(42).standard_normal(1_000_000)
profile = NumericProfiler().fit(data)

print(profile.mean, profile.sem, profile.ci_lower, profile.ci_upper)
print(profile.model_dump_json(indent=2))
```

## 2 — Categorical Profiling

```python
import numpy as np
from ds_data_miner.profiling.categorical import CategoricalProfiler

data = np.array(["ok"] * 700 + ["error"] * 300)
profile = CategoricalProfiler(max_cardinality=100).fit(data)

for stat in profile.stats:
    print(stat.category, stat.proportion, stat.std_error)
```

## 3 — Datetime Profiling

```python
import numpy as np
from ds_data_miner.profiling.datetime import DatetimeProfiler

base = np.datetime64("2024-01-01T00:00:00")
ts = base + np.arange(1440) * np.timedelta64(1, "m")
profile = DatetimeProfiler().fit(ts)

print(profile.is_monotonic_increasing, profile.gap_count, profile.inferred_freq)
```

## 4 — Full Dataset + JSON Export (Pandas)

```python
import pandas as pd
import ds_data_miner.pandas_ext  # noqa: F401

df = pd.read_csv("sensor_data.csv", parse_dates=["ts"])
df.miner.export_json("reports/report.json", dataset_name="sensors")
```

## 5 — JSON Schema for downstream consumers

```python
from ds_data_miner.export.serializer import ReportExporter

ReportExporter.export_schema("reports/report.schema.json")
```
