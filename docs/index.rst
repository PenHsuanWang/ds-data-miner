.. ds-data-miner — API Documentation
   ====================================

ds-data-miner API Reference
============================

**EDA Profiling Engine** — full-scan statistical analysis with standardized
JSON output.

.. rubric:: Version

.. code-block:: python

   import ds_data_miner
   print(ds_data_miner.__version__)   # e.g. "0.1.0"

.. rubric:: One-line install

.. code-block:: bash

   pip install ds-data-miner           # core (numpy + scipy + pydantic)
   pip install "ds-data-miner[pandas]" # + Pandas df.miner accessor

----

.. _agent-guide:

AI Agent Usage Guide
--------------------

This section tells you **exactly which function to call** for any EDA task.
Follow the decision tree, pick the right entry point, and use the code
snippets directly.

.. _agent-activation:

Step 0 — Activate the library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Required import (registers df.miner on pd.DataFrame)
   import ds_data_miner.pandas_ext   # noqa: F401

   # Core profilers (if you are NOT using Pandas)
   from ds_data_miner.profiling.numeric    import NumericProfiler
   from ds_data_miner.profiling.categorical import CategoricalProfiler
   from ds_data_miner.profiling.datetime   import DatetimeProfiler
   from ds_data_miner.profiling.engine     import ProfilingEngine
   from ds_data_miner.export.serializer    import ReportExporter

.. _agent-decision-tree:

Step 1 — Choose your entry point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Do you have a pandas.DataFrame?
   │
   ├─ YES ──► df.miner.profile()        # profiles every column automatically
   │           df.miner.export_json()   # scan + write JSON in one call
   │
   └─ NO (raw numpy arrays)
       │
       ├─ Single column?
       │   ├─ numeric dtype    ──► NumericProfiler().fit(array)
       │   ├─ string/object    ──► CategoricalProfiler().fit(array)
       │   └─ datetime64       ──► DatetimeProfiler().fit(array)
       │
       └─ Multiple columns (dict)?
           └──► ProfilingEngine().profile_dataset(columns_dict)

.. _agent-task-table:

Step 2 — Task → Function Quick Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 35 25

   * - Task
     - Call
     - Returns
   * - Profile a full DataFrame (all columns)
     - ``df.miner.profile()``
     - :class:`~ds_data_miner.core.contracts.DatasetReport`
   * - Profile a DataFrame and write JSON
     - ``df.miner.export_json("out.json")``
     - :class:`~ds_data_miner.core.contracts.DatasetReport`
   * - Profile a numeric numpy array
     - ``NumericProfiler().fit(array)``
     - :class:`~ds_data_miner.core.contracts.DistributionProfile`
   * - Profile a categorical numpy array
     - ``CategoricalProfiler().fit(array)``
     - :class:`~ds_data_miner.core.contracts.CategoricalProfile`
   * - Profile a datetime64 numpy array
     - ``DatetimeProfiler().fit(array)``
     - :class:`~ds_data_miner.core.contracts.DatetimeProfile`
   * - Profile multiple numpy columns
     - ``ProfilingEngine().profile_dataset(dict)``
     - :class:`~ds_data_miner.core.contracts.DatasetReport`
   * - Write DatasetReport to JSON file
     - ``ReportExporter().export(report, path)``
     - ``None``
   * - Write JSON Schema for report format
     - ``ReportExporter.export_schema(path)``
     - ``None``
   * - Run K-S distribution test on array
     - ``DistributionTester().test(array)``
     - ``dict[str, float]``

.. _agent-recipes:

Step 3 — Runnable Recipes
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Recipe A — Pandas: one-shot scan + export**

.. code-block:: python

   import pandas as pd
   import ds_data_miner.pandas_ext   # noqa: F401 — activates df.miner

   df = pd.read_csv("sensor_data.csv", parse_dates=["ts"])

   # Scans every column, routes by dtype, writes JSON
   report = df.miner.export_json(
       "reports/sensor_report.json",
       dataset_name="sensor_data",
   )

   # Dataset-level quality
   print(report.total_rows)             # int
   print(report.duplicate_row_count)    # int
   print(report.ds_data_miner_version)  # "0.1.0"

   # Per-column profile — type depends on column dtype
   price_profile = report.columns["price"]           # DistributionProfile
   print(price_profile.mean, price_profile.sem)      # float, float
   print(price_profile.missing_ratio)                # float [0.0, 1.0]

   status_profile = report.columns["status"]         # CategoricalProfile
   for stat in status_profile.stats:
       print(stat.category, stat.proportion)         # str, float

   ts_profile = report.columns["ts"]                 # DatetimeProfile
   print(ts_profile.inferred_freq, ts_profile.gap_count)

**Recipe B — NumPy only: profile a single numeric array**

.. code-block:: python

   import numpy as np
   from ds_data_miner.profiling.numeric import NumericProfiler

   data = np.random.default_rng(42).standard_normal(1_000_000)
   profile = NumericProfiler(ignore_nan=True, ci_level=0.95).fit(data)

   print(profile.mean)                   # ≈ 0.0
   print(profile.std)                    # ≈ 1.0
   print(profile.sem)                    # standard error of the mean
   print(profile.ci_lower, profile.ci_upper)  # 95% CI bounds
   print(profile.skewness, profile.kurtosis)
   print(profile.missing_count, profile.inf_count)

   # Histogram (for downstream plotting)
   edges  = profile.histogram_bin_edges  # list[float], len = n_bins + 1
   counts = profile.histogram_counts     # list[int],   len = n_bins

   # Serialize → JSON (NaN / Inf → null automatically)
   print(profile.model_dump_json(indent=2))

**Recipe C — NumPy only: profile categorical + handle high cardinality**

.. code-block:: python

   import warnings
   import numpy as np
   from ds_data_miner.profiling.categorical import CategoricalProfiler
   from ds_data_miner.core.exceptions import HighCardinalityWarning

   data = np.array(["ok"] * 700 + ["error"] * 250 + ["warn"] * 50)
   profile = CategoricalProfiler(max_cardinality=100).fit(data)

   for stat in profile.stats:
       # stat.category: str
       # stat.count: int
       # stat.proportion: float   ← count / n_total
       # stat.std_error: float    ← sqrt(p*(1-p)/N), binomial SE
       print(f"{stat.category:10s}  {stat.proportion:.3f}  ±{stat.std_error:.4f}")

   # High-cardinality guard (auto-triggered when n_unique > max_cardinality)
   uuid_col = np.array([f"uuid-{i}" for i in range(500)])
   with warnings.catch_warnings(record=True) as w:
       warnings.simplefilter("always")
       hc_profile = CategoricalProfiler(max_cardinality=50).fit(uuid_col)
       # HighCardinalityWarning is emitted — profiling still succeeds

   print(hc_profile.is_high_cardinality)            # True
   print(hc_profile.truncated_at)                   # 50
   other = [s for s in hc_profile.stats if s.category == "_OTHER_"]
   print(other[0].count)                            # sum of all dropped cats

**Recipe D — NumPy only: profile datetime + inspect gaps**

.. code-block:: python

   import numpy as np
   from ds_data_miner.profiling.datetime import DatetimeProfiler

   base = np.datetime64("2024-01-01T00:00:00")
   ts   = base + np.arange(1440) * np.timedelta64(1, "m")

   profile = DatetimeProfiler(gap_threshold_factor=2.0).fit(ts)

   print(profile.start)                    # "2024-01-01T00:00:00"
   print(profile.end)                      # "2024-01-01T23:59:00"
   print(profile.is_monotonic_increasing)  # True
   print(profile.inferred_freq)            # "1min"
   print(profile.gap_count)               # 0
   for gap in profile.gap_locations:
       print(gap["from"], "→", gap["to"], f"({gap['duration_seconds']}s)")

**Recipe E — Multi-column NumPy dict → DatasetReport**

.. code-block:: python

   import numpy as np
   from ds_data_miner.profiling.engine import ProfilingEngine

   base = np.datetime64("2024-01-01T00:00:00")
   columns = {
       "price":    np.random.default_rng(0).standard_normal(1000),
       "category": np.array(["A", "B", "C"] * 334)[:1000],
       "ts":       base + np.arange(1000) * np.timedelta64(1, "m"),
   }

   engine = ProfilingEngine()
   report = engine.profile_dataset(columns, dataset_name="my_dataset")

   # Serialize to JSON string (in-memory)
   json_str = report.model_dump_json(indent=2)

   # Or write to file
   from ds_data_miner.export.serializer import ReportExporter
   ReportExporter().export(report, "reports/my_report.json")

**Recipe F — Generate JSON Schema for report validation**

.. code-block:: python

   from ds_data_miner.export.serializer import ReportExporter

   # Writes JSON Schema for DatasetReport (and all nested types)
   ReportExporter.export_schema("schemas/report.schema.json")

   # Consumers can use this schema to validate report.json before reading it

.. _agent-output-schema:

Step 4 — Output Field Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All output types are immutable Pydantic models.  They can be converted to
JSON with ``model.model_dump_json()`` or to a dict with ``model.model_dump()``.
All ``float`` fields with ``NaN`` or ``Inf`` values are automatically
serialized as JSON ``null``.

.. rubric:: DistributionProfile (numeric columns)

.. code-block:: text

   mean, variance, std, median, min, max     ← descriptive stats
   q25, q75                                  ← quartiles
   skewness, kurtosis                        ← distribution shape
   sem                                       ← Standard Error of the Mean
   ci_lower, ci_upper                        ← symmetric CI bounds
   histogram_bin_edges  list[float]          ← bin boundaries (len = n_bins+1)
   histogram_counts     list[int]            ← per-bin counts  (len = n_bins)
   n_samples, n_valid, missing_count         ← quality counters
   missing_ratio, inf_count                  ← quality ratios
   distribution_type, ks_statistic, ks_p_value  ← optional (from DistributionTester)

.. rubric:: CategoricalProfile (object / string / category columns)

.. code-block:: text

   stats            list[CategoryStats]    ← per-category stats
     .category      str
     .count         int
     .proportion    float                  ← count / n_total
     .std_error     float                  ← sqrt(p*(1-p)/N) binomial SE
   n_total          int                    ← non-missing count
   n_unique         int                    ← before truncation
   missing_count, missing_ratio
   is_high_cardinality  bool              ← True when truncated
   truncated_at     int | None             ← Top-N threshold used

.. rubric:: DatetimeProfile (datetime64 columns)

.. code-block:: text

   start, end          str (ISO 8601)      ← date range
   duration_seconds    float               ← end - start in seconds
   is_monotonic_increasing  bool           ← original order check
   gap_count           int
   gap_locations       list[dict]          ← [{from, to, duration_seconds}]
   inferred_freq       str | None          ← "1min", "1h", "1d", etc.
   n_samples, missing_count, missing_ratio

.. rubric:: DatasetReport (top-level, from ProfilingEngine or df.miner)

.. code-block:: text

   dataset_name            str
   created_at              str (ISO 8601 UTC)
   ds_data_miner_version   str
   total_rows, total_columns
   duplicate_row_count, duplicate_row_ratio
   columns   dict[str, DistributionProfile | CategoricalProfile | DatetimeProfile]

----

.. toctree::
   :maxdepth: 1
   :caption: Getting Started

   getting_started/installation
   getting_started/quickstart

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/core
   api/profiling
   api/export
   api/pandas_ext

.. toctree::
   :maxdepth: 1
   :caption: Developer Guide

   dev/architecture
   dev/contributing
   changelog

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
