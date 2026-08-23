# **高階系統設計文件 (High-Level Design Document)**

**專案代號：** ds-data-miner  
**文件版本：** v4.0  
**文件狀態：** Approved for Development  
**設計原則：** 領域驅動設計 (DDD)、六角架構 (Hexagonal Architecture)、SOLID、Evidence-driven Statistical Diagnostics

---

## **1. 系統定位與核心哲學**

ds-data-miner 不僅是一個探索式資料分析 (EDA) 引擎，更是一個**以證據為基礎的統計診斷引擎 (Evidence-driven Statistical Diagnostic Engine)**。

系統的核心哲學為：

> **The system provides statistical evidence and recommendations, not absolute truth.**

此原則貫穿整個系統設計：系統不得僅根據單一統計檢定結果武斷選擇演算法，而必須收集統計證據、評估證據可靠程度、檢查樣本獨立性與時間相依性，最終提供可追溯的推薦與完整的 Decision Trace。當證據不足時，系統應優先回傳 Warning / Insufficient Evidence，而不是產生一個看似精確但缺乏統計依據的數值。

### **1.1 三部曲架構願景**

`ds-data-miner` 是三部曲系統的第一部，負責計算核心：

1. **`ds-data-miner`（本階段）：** 探索式資料分析與統計診斷核心引擎。
2. **`ds-data-miner-vis`（未來）：** 讀取標準化 JSON 輸出，負責渲染視覺化與製圖。
3. **`ds-data-miner-reporter`（未來）：** 讀取標準化 JSON 輸出，負責產出完整的 PDF/HTML 報告。

### **1.2 系統能力範圍**

| 能力範圍 | Epic | 狀態 |
|---------|------|------|
| 單變數資料輪廓 (Data Profiling) | Epic 1 | ✅ 已實作 |
| 不確定性誤差傳遞 (Uncertainty Propagation) | Epic 2 | ✅ 已實作 |
| 生態系整合 (Pandas / Matplotlib Adapters) | Epic 3 | ✅ 已實作 |
| 工程品質與交付 (CI/CD, Type Safety) | Epic 4 | ✅ 已實作 |
| **雙變數智慧診斷引擎 (Bivariate Statistical Intelligence)** | **Epic 5** | **🔧 開發中** |

---

## **2. 架構分層 (Layered Architecture)**

系統採用六角架構（Ports and Adapters），嚴格遵守依賴反轉原則（DIP）。

```text
┌─────────────────────────────────────────────────────────────┐
│                    External Interfaces                      │
│                                                             │
│        Pandas Adapter / Future API / CLI / Notebook         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                       │
│                                                             │
│              ProfilingEngine                                │
│              BivariateDiagnosticEngine                      │
│              UncertaintyPropagationEngine                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       Domain Layer                          │
│                                                             │
│  Profilers          Evidence Collectors                     │
│  Statistical Tests  MetricSelector + Strategy Registry      │
│  Effect Size Calculators  Dependency Diagnostics            │
│  Correlation Engine  Multiple Testing Strategies            │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       Core Contracts                        │
│                                                             │
│  DistributionProfile    DiagnosticEvidence                  │
│  CategoricalProfile     HypothesisTestResult                │
│  DatetimeProfile        DynamicEffectSize                   │
│  DatasetReport          CorrelationResult                   │
│  UncertaintyArray       DecisionTrace                       │
└─────────────────────────────────────────────────────────────┘
```

### **2.1 依賴規則**

| 模組 | 可依賴 | 禁止依賴 |
|------|--------|---------|
| `core` | `pydantic` | `pandas`, `matplotlib`, `numpy` |
| `profiling` (Domain) | `core`, `numpy`, `scipy` | `pandas`, `matplotlib` |
| `diagnostics` (Domain) | `core`, `numpy`, `scipy` | `pandas`, `matplotlib` |
| `uncertainty` (Domain) | `core`, `numpy`, `scipy` | `pandas`, `matplotlib` |
| `pandas_ext` (Adapter) | `core`, `profiling`, `diagnostics`, `pandas` | — |
| `viz` (Adapter) | `core`, `matplotlib` | `pandas` |
| `export` (Export) | `core` | `pandas`, `matplotlib` |

---

## **3. 專案實體目錄結構**

```
ds-data-miner/
├── pyproject.toml
├── src/
│   └── ds_data_miner/
│       ├── __init__.py
│       ├── py.typed
│       │
│       ├── core/                        # 【Core Contracts】
│       │   ├── contracts.py             #   Pydantic Models (immutable)
│       │   ├── enums.py                 #   EvidenceLevel, VariableType, etc.
│       │   ├── exceptions.py            #   Custom Exceptions & Warnings
│       │   └── types.py                 #   Type aliases
│       │
│       ├── profiling/                   # 【Domain: Univariate Profiling】
│       │   ├── base.py                  #   BaseProfiler (ABC)
│       │   ├── numeric.py               #   NumericProfiler
│       │   ├── categorical.py           #   CategoricalProfiler
│       │   ├── datetime.py              #   DatetimeProfiler
│       │   ├── distribution.py          #   DistributionTester
│       │   └── engine.py                #   ProfilingEngine (type routing)
│       │
│       ├── diagnostics/                 # 【Domain: Bivariate Diagnostics】
│       │   ├── engine.py                #   BivariateDiagnosticEngine
│       │   ├── evidence/                #   Evidence Collectors
│       │   │   ├── collector.py
│       │   │   ├── normality.py
│       │   │   ├── variance.py
│       │   │   ├── outlier.py
│       │   │   ├── dependency.py
│       │   │   └── balance.py
│       │   ├── metrics/                 #   Effect Size Strategies
│       │   │   ├── base.py
│       │   │   ├── cohens_d.py
│       │   │   ├── hedges_g.py
│       │   │   ├── glass_delta.py
│       │   │   ├── cliffs_delta.py
│       │   │   └── registry.py
│       │   ├── correlation/             #   Correlation Engine
│       │   │   ├── pearson.py
│       │   │   ├── multiple_testing.py
│       │   │   └── engine.py
│       │   └── selection/               #   MetricSelector
│       │       ├── selector.py
│       │       └── rules.py
│       │
│       ├── uncertainty/                 # 【Domain: Uncertainty Propagation】
│       │   ├── analytical.py
│       │   └── monte_carlo.py
│       │
│       ├── pandas_ext/                  # 【Adapter: Pandas】
│       │   └── accessor.py             #   df.trust accessor
│       │
│       ├── export/                      # 【Export: JSON Serialization】
│       │   └── serializer.py
│       │
│       └── viz/                         # 【Adapter: Matplotlib】
│           └── uncertainty.py
│
├── tests/
│   ├── test_core/
│   ├── test_profiling/
│   ├── test_diagnostics/
│   ├── test_uncertainty/
│   ├── test_export/
│   └── test_adapters/
│
└── design-doc/
    ├── SDD.md
    ├── user-stories.md
    ├── high-level-design-doc.md
    └── software-design-doc.md
```

---

## **4. 核心資料流向 (Data Flow)**

### **4.1 單變數 Profiling 資料流**

```text
[User] df.trust.profile()
    │
    ▼
[Adapter] pandas_ext → 將 pd.Series 轉為 np.ndarray
    │
    ▼
[Application] ProfilingEngine → 根據 dtype 路由至對應 Profiler
    │
    ├─ numeric   → NumericProfiler.fit()      → DistributionProfile
    ├─ object    → CategoricalProfiler.fit()  → CategoricalProfile
    └─ datetime  → DatetimeProfiler.fit()     → DatetimeProfile
    │
    ▼
[Application] ProfilingEngine → 聚合為 DatasetReport
    │
    ▼
[Export] ReportExporter → 序列化為 JSON
```

### **4.2 雙變數診斷資料流（Epic 5 新增）**

```text
[User] df.trust.diagnose(x="col_a", y="col_b", grouping_columns=["lot"])
    │
    ▼
[Adapter] pandas_ext → 將指定欄位轉為 np.ndarray
    │
    ▼
[Application] BivariateDiagnosticEngine
    │
    ├─ 1. VariableTypeDetector    → 辨識 Continuous / Categorical
    ├─ 2. SampleStructureDetector → 辨識 Independent / Paired / Repeated
    ├─ 3. EvidenceCollector       → 收集 Normality / Variance / Outlier /
    │                                Dependency / Group Balance / Missing Data
    ├─ 4. MetricSelector          → 根據 DiagnosticEvidence 推薦 Metric
    └─ 5. EffectSizeStrategy      → 透過 Registry 計算效應量
    │
    ▼
[Core] DynamicEffectSize (含 DiagnosticEvidence + DecisionTrace)
```

### **4.3 相關性分析資料流（Epic 5 新增）**

```text
[User] df.trust.correlation(method="pearson")
    │
    ▼
[Adapter] pandas_ext → 擷取數值欄位為 np.ndarray 矩陣
    │
    ▼
[Domain] CorrelationEngine
    │
    ├─ 1. Missing Data Masking    → pairwise_complete boolean mask
    ├─ 2. Pearson Computation     → 向量化相關係數矩陣
    ├─ 3. Multiple Testing        → Benjamini-Hochberg FDR correction
    └─ 4. High Dimensionality     → Sparsification if p > threshold
    │
    ▼
[Core] CorrelationResult (含 raw_p_values + adjusted_p_values)
```

---

## **5. Epic 5 診斷引擎：統計方法選擇原則**

系統不得採用簡化的 `if normal → Cohen's d / else → Cliff's Delta` 邏輯。推薦流程必須遵循以下管線：

```text
Input Data
    ↓
Data Type Detection
    ↓
Sample Structure Detection
    ↓
Data Quality Assessment
    ├── Missing Data
    ├── Outlier
    ├── Group Balance
    ├── Dependency
    └── Temporal Dependency
    ↓
Statistical Evidence Collection
    ├── Normality
    ├── Variance
    └── Dependency
    ↓
Evidence Evaluation
    ↓
MetricSelector + Strategy Registry
    ↓
Recommendation + DecisionTrace
```

### **5.1 MVP 支援的統計方法**

| 分析類型 | Metric / Method |
|---------|----------------|
| Continuous vs Continuous | Pearson's r |
| Two Independent Groups | Cohen's d |
| Small Sample Correction | Hedges' g |
| Unequal Variance | Glass's Δ |
| Non-parametric | Cliff's δ |
| Variance Diagnostic | Brown-Forsythe / median-centered Levene |
| Multiple Testing | Benjamini-Hochberg FDR |
| Dependency Detection | DependencyEvidence + Warning |

### **5.2 架構預留（Future Extension）**

Spearman's ρ, Kendall's τ, Mutual Information, Distance Correlation, VIF, Partial Correlation, Paired Effect Size, Repeated-measures analysis, Hierarchical / mixed-effects models, Time-series dependency-aware statistics。

---

## **6. 工程實踐與開發規範**

### **6.1 效能與數值穩定性**

* **向量化：** 所有 Array 等級的數值運算必須使用 NumPy / SciPy 向量化操作，嚴禁 Python 原生 `for` 迴圈。
* **NaN / Inf 防禦：** 所有統計運算前必須檢測與處理。全為 invalid 值時拋出 `DataQualityError`。
* **P-value Underflow：** `p_value == 0.0` 時必須標記 `p_value_is_underflowed = True`，提供 `p_value_display = "< 1e-300"`。
* **Zero Variance：** 需要除以 SD 的效應量必須先檢查 `std == 0`，否則拋出 `MetricCalculationError`，禁止輸出 `inf` / `NaN`。
* **高基數防禦：** `CategoricalProfiler` 遭遇高基數欄位時自動截斷並發出 `HighCardinalityWarning`。
* **高維度防禦：** Correlation Matrix 超過特徵門檻時啟動 Sparse Mode 或發出 `HighDimensionalityWarning`。

### **6.2 統計語義規範**

系統所有 UI、Log、JSON metadata 與 Exception message 必須遵守統計語義：

| ❌ 禁止 | ✅ 應使用 |
|---------|---------|
| `Data is normally distributed` | `Insufficient evidence to reject the normality assumption` |
| `Equal variance = True` | `Insufficient evidence to reject equal variance` |
| `H0 is proven` | `Insufficient evidence to reject H0` |
| `Correlation = causation` | `Observed association does not imply causation` |

### **6.3 測試策略**

| 測試類型 | 要求 |
|---------|------|
| Statistical Validation | Effect Size 與 reference implementation 比較，`atol ≤ 1e-7` |
| Diagnostic Decision | Normal/Unequal Var/Non-normal/Dependency/Imbalance 等情境覆蓋 |
| Correlation | NaN, Inf, Pairwise Complete, Sparse, FDR |
| P-value Underflow | 極大樣本驗證 `p_value_is_underflowed` |
| Dependency | Lot/Wafer repeated measurements 驗證 DependencyWarning |
| Architecture | CI 檢查 core/domain 不含 `import pandas` / `import matplotlib` |
| Property-Based | `hypothesis` 套件暴力測試 |
| JSON Round-trip | `model → JSON → model` 往返一致性 |
| Coverage | ≥ 85% |

### **6.4 套件管理**

```toml
[project]
name = "ds-data-miner"
version = "0.2.0"
requires-python = ">=3.10"
dependencies = ["numpy>=1.21.0", "scipy>=1.7.0", "pydantic>=2.0.0"]

[project.optional-dependencies]
pandas = ["pandas>=1.3.0"]
viz = ["matplotlib>=3.5.0"]
dev = ["pytest>=7.0.0", "mypy>=1.0", "hypothesis>=6.0", "ruff>=0.1.0"]
```

### **6.5 CI Quality Gate**

* `mypy --strict src/` → 0 errors
* Test Coverage → ≥ 85%
* Core Contract Property-Based Testing → Required
* Architecture Dependency Test → Passed

---

## **7. 結案驗收會議 (Sign-off Meeting)**

1. **Demo：** Pandas DataFrame → Data Profiling → Statistical Diagnostics → Bivariate Analysis → Effect Size / Correlation → Decision Trace。
2. **Dependency Defense：** Wafer / Lot / Chamber repeated measurements → DependencyWarning。
3. **High-Dimensionality：** 高維 FDC dataset → memory guard、threshold filtering、sparse representation。
4. **Statistical Evidence：** normality、variance、sample imbalance、missing data、dependency evidence。
5. **Multiple Testing：** raw p-value vs BH-adjusted p-value。
6. **Numerical Stability：** 極小 p-value、zero variance、NaN、Inf edge cases。
7. **Code Review：** core / domain 不依賴 Pandas / Matplotlib。
8. **CI/CD：** type checking、linting、testing、coverage。
9. **Installation：** 乾淨 Python environment 成功安裝並執行 smoke test。

**核准人 (Tech Lead)：** [等待簽核]