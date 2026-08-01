# Changelog

All notable changes to `ds-data-miner` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

## [0.1.0] — 2024-08-01

### Added

- `NumericProfiler` — full-scan statistics with SEM, confidence intervals,
  and pre-computed histogram bins/counts
- `CategoricalProfiler` — binomial standard errors, high-cardinality defense
  (automatic Top-N truncation + `_OTHER_` bucket)
- `DatetimeProfiler` — monotonicity check, gap detection, frequency inference
- `DistributionTester` — K-S test wrapper with scipy baseline
- `ProfilingEngine` — dtype-routing orchestrator producing `DatasetReport`
- `ReportExporter` — JSON file output + JSON Schema generation
- `MinerAccessor` — `df.miner.profile()` and `df.miner.export_json()` Pandas
  accessor
- Pydantic v2 data contracts with NaN/Inf → null JSON serialization
- 80 pytest tests, 95.7% coverage
- `tox` matrix for Python 3.10–3.13, lint, typecheck, docs
- `bump-my-version` integration for automated semver tagging
