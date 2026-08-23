# **軟體開發需求規格書 (Software Requirements Specification)**

**專案名稱：** ds-data-miner — 探索式資料分析與統計診斷核心引擎  
**文件版本：** v4.0  
**目標受眾：** 資料科學家、機器學習工程師、製程整合工程師、FDC 演算法工程師、DevOps / MLOps 工程師

---

## **1. 產品概述 (Product Overview)**

### **1.1 專案背景與目的**

在資料工程與機器學習管線（Pipeline）中，確保輸入資料的品質（Data Quality）與量化原始統計特徵的可靠性，是建立高可信度模型的第一道關卡。

`ds-data-miner` 是一個面向資料科學與半導體製造資料分析場景的核心引擎。除了傳統的探索式資料分析（EDA），v4.0 版本新增了**雙變數智慧診斷引擎 (Bivariate Statistical Intelligence)**，能根據資料型態、樣本結構、分佈特徵與統計證據，推薦合適的效應量或關聯性指標，並提供完整的決策追蹤。

系統採用三部曲架構，職責嚴格分離：

1. **`ds-data-miner`（本階段重點）：** 探索式資料分析與統計診斷核心引擎。
2. **`ds-data-miner-vis`（未來階段）：** 讀取標準化 JSON 輸出，負責視覺化渲染。
3. **`ds-data-miner-reporter`（未來階段）：** 讀取標準化 JSON 輸出，負責報告產出。

### **1.2 核心價值**

* **Evidence-driven Diagnostics：** 系統提供統計證據與推薦，而非絕對真理。每個推薦都附帶可追溯的 DecisionTrace。
* **高可靠度：** 支援本地記憶體全量資料掃描，拒絕因抽樣造成的統計偏差。
* **統計安全性：** 具備 NaN/Inf 防禦、P-value underflow 處理、zero variance 保護、multiple testing correction、pseudo-replication 偵測。
* **工程解耦：** 採用六角架構，核心數學運算不受外部框架改版影響。
* **標準化輸出：** 所有分析結果以 JSON 格式匯出，作為下游工具的標準資料合約。

---

## **2. 系統架構與領域驅動設計 (Architecture & DDD)**

本系統嚴格遵守單一職責原則（SRP）與依賴反轉原則（DIP）。

| 層級 | 模組 | 職責 | 依賴限制 |
|------|------|------|---------|
| **Adapter** | `pandas_ext` | 封裝 `df.trust` Accessor，將 DataFrame 轉換為核心合約 | 依賴 `pandas`, `core`, `profiling`, `diagnostics` |
| **Adapter** | `viz` | Matplotlib 繪圖輔助 | 依賴 `matplotlib`, `core` |
| **Export** | `export` | 將 Profile / Diagnostic 合約序列化為 JSON | 依賴 `core` |
| **Application** | `profiling.engine` | 單變數全表掃描排程 | 依賴 `profiling`, `core` |
| **Application** | `diagnostics.engine` | 雙變數智慧診斷排程 | 依賴 `diagnostics`, `core` |
| **Domain** | `profiling` | 全量掃描、統計特徵萃取、分佈檢定 | 僅依賴 `numpy`, `scipy`, `core` |
| **Domain** | `diagnostics` | 證據收集、效應量計算、策略選擇、相關性分析 | 僅依賴 `numpy`, `scipy`, `core` |
| **Domain** | `uncertainty` | 解析法 / 蒙地卡羅誤差傳遞 | 僅依賴 `numpy`, `scipy`, `core` |
| **Core** | `core` | 不可變資料合約 (Pydantic Models)、枚舉、例外 | 僅依賴 `pydantic` |

---

## **3. 核心功能需求 (Functional Requirements)**

### **3.1 core — 核心資料合約**

* **[REQ-CORE-01] 單變數統計合約：** 必須定義 `DistributionProfile`, `CategoricalProfile`, `DatetimeProfile`，包含基礎統計量、統計誤差、資料品質指標與直方圖預計算。
* **[REQ-CORE-02] 資料集報告合約：** 必須定義 `DatasetReport` 作為頂層聚合容器，包含元資料、全域品質指標與各欄位 Profile。
* **[REQ-CORE-03] 假設檢定合約：** 必須定義 `HypothesisTestResult`，包含 `test_name`, `statistic`, `p_value`, `p_value_display`, `p_value_is_underflowed`, `alpha`, `n_samples`, `reject_null`, `evidence_level`。
* **[REQ-CORE-04] 診斷證據合約：** 必須定義 `DiagnosticEvidence`，包含 `data_type`, `sample_structure`, `sample_sizes`, `group_size_ratio`, `n_valid_pairs`, `missing_data_strategy`, `missing_count`, `missing_ratio`, `normality_evidence`, `variance_evidence`, `outlier_evidence`, `dependency_evidence`, `group_balance`, `multiple_testing_evidence`, `evidence_level`, `warnings`。
* **[REQ-CORE-05] 效應量合約：** 必須定義 `DynamicEffectSize`，包含 `metric`, `estimate`, `standard_error`, `confidence_interval`, `sample_sizes`, `diagnostic_evidence`, `decision_trace`, `status`, `warnings`。
* **[REQ-CORE-06] 決策軌跡合約：** 必須定義 `DecisionTrace`，包含 `steps`, `assumptions_checked`, `assumptions_supported`, `assumptions_not_supported`, `warnings`, `final_reason`。
* **[REQ-CORE-07] 相關性結果合約：** 必須定義 `CorrelationResult`，包含 `method`, `feature_names`, `correlation_matrix`, `sparse_pairs`, `sample_size`, `sample_size_matrix`, `missing_data_strategy`, `raw_p_values`, `adjusted_p_values`, `multiple_testing_method`, `threshold`, `warnings`。
* **[REQ-CORE-08] 枚舉定義：** 必須定義 `EvidenceLevel` (HIGH, MODERATE, LOW, INSUFFICIENT)、`VariableType` (CONTINUOUS, CATEGORICAL, DATETIME)、`SampleStructure` (INDEPENDENT, PAIRED, REPEATED_MEASURES, TIME_SERIES, UNKNOWN)、`MissingDataStrategy` (PAIRWISE_COMPLETE, LISTWISE_COMPLETE, ERROR)。
* **[REQ-CORE-09] JSON 序列化：** 所有合約必須支援 `model_dump_json()`。`NaN` / `Inf` → `null`。NumPy 型別自動轉換為 Python 原生型別。
* **[REQ-CORE-10] Report 分離：** 大型雙變數診斷結果（`CorrelationResult`, `DynamicEffectSize`, `DiagnosticReport`）不得無條件塞入 `DatasetReport`，必須支援獨立產生與序列化。

### **3.2 profiling — 單變數資料統計與品質檢驗**

* **[REQ-PROF-01] 全量掃描：** 必須在本地 Python Runtime 中完整掃描 NumPy Array，嚴禁任何形式的抽樣。
* **[REQ-PROF-02] 數值型統計量：** `NumericProfiler` 必須計算 mean, variance, std, skewness, kurtosis, median, q25, q75, min, max, SEM, CI, 直方圖。
* **[REQ-PROF-03] 極端值防禦：** 掃描過程遭遇 NaN / Inf 時，必須依策略處理或拋出 `DataQualityError`。
* **[REQ-PROF-04] 類別型掃描：** `CategoricalProfiler` 必須計算次數、比例與二項式標準誤。
* **[REQ-PROF-05] 高基數防禦：** 遭遇高基數欄位時自動截斷至 Top-N，發出 `HighCardinalityWarning`。
* **[REQ-PROF-06] 時序型分析：** `DatetimeProfiler` 必須驗證單調性、偵測時間斷層、推估頻率。
* **[REQ-PROF-07] 分佈檢定：** `DistributionTester` 必須回傳 `HypothesisTestResult`（非裸 dict），輸出不得將 p > α 解釋為「資料已證明符合該分佈」。
* **[REQ-PROF-08] 全表路由：** `ProfilingEngine` 必須根據 dtype 自動路由至對應 Profiler。

### **3.3 diagnostics — 雙變數智慧診斷引擎**

#### **3.3.1 Evidence Collection**

* **[REQ-DIAG-01] 資料型態辨識：** 必須在診斷開始前辨識 Continuous / Categorical / Datetime。
* **[REQ-DIAG-02] 樣本結構辨識：** 必須評估 Independent, Paired, Repeated Measurements, Time Series, Unknown。當無法證明獨立性時，不得默認為 INDEPENDENT。
* **[REQ-DIAG-03] 常態性證據：** 收集常態性檢定結果，不得將 p > α 解讀為「證明常態」。
* **[REQ-DIAG-04] 變異數證據：** 使用 Brown-Forsythe / median-centered Levene 評估兩組變異差異。
* **[REQ-DIAG-05] 離群值偵測：** 掃描兩組資料中是否存在離群值。
* **[REQ-DIAG-06] 相依性偵測：** 若資料包含 Lot, Wafer, Chamber, Tool 等 grouping 資訊，必須產生 `DependencyWarning` / `DependencyEvidence`。不得在無警告的情況下假設所有觀測值為獨立樣本。
* **[REQ-DIAG-07] 時間相依性：** 若資料仍維持 timestamp-level resolution（未經 aggregation），必須辨識 temporal dependency / autocorrelation 風險。
* **[REQ-DIAG-08] 群組平衡性：** 必須檢查 Group Size Ratio。當 `max(n_a, n_b) / min(n_a, n_b) > 10` 時，產生 `ImbalancedSampleWarning`。
* **[REQ-DIAG-09] 缺失值策略：** 雙變數分析必須明確記錄 `missing_data_strategy`，禁止將含 NaN 的原始矩陣直接傳入統計計算。

#### **3.3.2 Metric Selection & Effect Size**

* **[REQ-DIAG-10] 策略註冊表：** 統計方法推薦必須透過可擴充的 `MetricRegistry` + `EffectSizeStrategy` 管理，不得硬編碼於單一 if/elif/else Router。
* **[REQ-DIAG-11] Cohen's d：** 當證據支持 continuous, independent, approximately normal, no strong evidence of unequal variance 時推薦。
* **[REQ-DIAG-12] Hedges' g：** 小樣本校正。
* **[REQ-DIAG-13] Glass's Δ：** 當證據支持 unequal variance 且 reference group SD stable 時推薦。若 `SD_reference == 0`，拋出 `MetricCalculationError`，禁止輸出 `inf` / `NaN`。
* **[REQ-DIAG-14] Cliff's δ：** 當資料 severely skewed, outlier contaminated, non-normal, strongly imbalanced 且缺乏足夠證據支持 parametric assumptions 時推薦。
* **[REQ-DIAG-15] Decision Trace：** 每一次推薦必須保存完整 `DecisionTrace`，記錄 Variable Type → Sample Structure → Diagnostics → Evidence → Recommendation。
* **[REQ-DIAG-16] Insufficient Evidence：** 當資料品質、樣本數或樣本結構不足以支持可靠判斷時，回傳 Warning / Insufficient Evidence，而非強制選擇統計方法。

#### **3.3.3 Correlation**

* **[REQ-CORR-01] Pearson MVP：** 提供 `df.trust.correlation(method="pearson")` API。MVP 支援 Pearson's r。
* **[REQ-CORR-02] Missing Data Masking：** 每個 feature pair 必須建立 boolean mask，禁止直接對含 NaN 的矩陣呼叫 `np.corrcoef`。每個 pair 的有效樣本數必須記錄。
* **[REQ-CORR-03] Multiple Testing：** 支援 Benjamini-Hochberg FDR correction。必須區分 raw p-value 與 adjusted p-value。
* **[REQ-CORR-04] High Dimensionality Guard：** 當 feature 數量超過門檻時，不得無條件將完整 N×N 矩陣作為 JSON payload 輸出。必須支援 threshold filtering（僅保留 `|r| ≥ threshold` 的 pairs）。
* **[REQ-CORR-05] Feature Screening Semantics：** 文件與輸出必須明確聲明 correlation ≠ causation，Pairwise Correlation 不得被視為完整 Multicollinearity Diagnosis。
* **[REQ-CORR-06] Non-linear Extension：** 架構必須預留 Mutual Information / Distance Correlation 的擴充能力，不得破壞 Registry Architecture。

### **3.4 uncertainty — 不確定性誤差傳遞**

* **[REQ-UNC-01] 解析法：** `AnalyticalPropagator` 必須接收 `UncertaintyArray` 與轉換函式，回傳新的 `UncertaintyArray`。
* **[REQ-UNC-02] 蒙地卡羅法：** `MonteCarloPropagator` 必須允許自定義 `n_simulations`，Random Seed 可固定，輸出包含 simulation configuration。
* **[REQ-UNC-03] 數值穩定：** 數學無效操作時產生 `NumericalInstabilityError`。

### **3.5 介面轉接層 (Adapters)**

* **[REQ-ADPT-01] Pandas Accessor：** 註冊 `df.trust` accessor，提供 `profile()`, `correlation()`, `diagnose()` 三個主要 API。
* **[REQ-ADPT-02] 動態型別路由：** 依據 DataFrame 欄位 dtype 自動派發至對應 Profiler。
* **[REQ-ADPT-03] Adapter 邊界：** 不得將 `pd.DataFrame` / `pd.Series` 傳入 Domain Layer。必須在 Adapter 層轉換為 `np.ndarray`。
* **[REQ-ADPT-04] Viz Helper：** `viz.plot_uncertainty_trend(...)` 能正確渲染折線與 uncertainty band。Core / Domain 不得依賴 Matplotlib。

### **3.6 export — JSON 匯出**

* **[REQ-EXPORT-01] JSON 匯出：** `ReportExporter` 必須支援 `DatasetReport`, `DiagnosticReport`, `CorrelationResult`, `DynamicEffectSize` 的獨立輸出。
* **[REQ-EXPORT-02] JSON Schema：** 支援透過 Pydantic `model_json_schema()` 自動產出 Schema 定義。

---

## **4. 非功能性需求 (Non-Functional Requirements)**

### **4.1 效能與資源管理 (Performance)**

* **[NFR-PERF-01]** 核心數學運算必須全面使用 NumPy / SciPy 向量化操作。嚴禁 Python 原生 `for` 迴圈處理 Array 資料。
* **[NFR-PERF-02]** 不得產生不必要的 DataFrame 深拷貝（Deep Copy）。不得將原始大型陣列保存於合約物件中。
* **[NFR-PERF-03]** Correlation Matrix 建立、轉換與輸出過程必須具備 memory guard。Feature 超過門檻時自動啟動 Sparse Mode 或發出 Warning。

### **4.2 數值穩定性 (Numerical Stability)**

* **[NFR-NUM-01]** P-value underflow 至 `0.0` 時，必須標記 `p_value_is_underflowed = True` 並提供 `p_value_display = "< 1e-300"`。
* **[NFR-NUM-02]** 需要除以 SD 的統計量必須先檢查 `std == 0`，否則拋出 `MetricCalculationError`。禁止輸出 `inf` / `NaN` 作為正常效應量結果。
* **[NFR-NUM-03]** 統計運算優先使用 SciPy / NumPy 提供的 numerical stable implementation。不得自行重新實作已存在且經驗證的基礎統計演算法。

### **4.3 統計語義正確性 (Statistical Semantics)**

* **[NFR-STAT-01]** p > α 時，必須使用 "Insufficient evidence to reject the null hypothesis"。禁止 "Data is normally distributed", "Equal variance = True", "Null hypothesis is proven"。
* **[NFR-STAT-02]** Evidence Level 不代表統計假設「為真」，而代表目前資料對該判斷所提供的證據強度。
* **[NFR-STAT-03]** Correlation 輸出必須聲明 association does not imply causation。

### **4.4 序列化與型別安全 (Serialization)**

* **[NFR-SERIAL-01]** 所有核心合約使用 Pydantic v2 BaseModel，`frozen=True`, `ser_json_inf_nan="null"`。
* **[NFR-SERIAL-02]** NumPy 型別自動轉換為 Python 原生型別。

### **4.5 封裝與部署 (Packaging)**

* **[NFR-PKG-01]** 採用 PEP 621 標準 `pyproject.toml`，廢棄 `setup.py`。
* **[NFR-PKG-02]** 支援 `pip install git+https://[repository_url]` 安裝。
* **[NFR-PKG-03]** 核心依賴：`numpy`, `scipy`, `pydantic`。可選依賴：`pandas`, `matplotlib`。

### **4.6 程式碼品質與測試 (Quality)**

* **[NFR-QA-01]** 全專案 100% 覆蓋 Type Hints，通過 `mypy --strict`。
* **[NFR-QA-02]** Test Coverage ≥ 85%。
* **[NFR-QA-03]** 統計計算結果與 `scipy` / `statsmodels` 進行 Baseline 比對，容許誤差 ≤ `1e-7`。
* **[NFR-QA-04]** JSON Round-trip Testing：所有合約通過 `model → JSON → model` 往返測試。
* **[NFR-QA-05]** Core Contracts 必須包含 Property-Based Testing（`hypothesis`）。
* **[NFR-QA-06]** Architecture Dependency Test：CI 必須檢查 `core/` 與 `profiling/` 不含 `import pandas` / `import matplotlib`。

---

## **5. 驗收標準 (Acceptance Criteria)**

> 1. **安裝驗收：** 在乾淨 Python 虛擬環境中，透過 Git URL 成功安裝，`import ds_data_miner` 無報錯。
> 2. **架構驗收：** `core`, `profiling`, `diagnostics` 模組內部不含 `import pandas` / `import matplotlib`。
> 3. **單變數 Profiling 驗收：** 完整演示 Pandas DataFrame → 全表掃描 → JSON 匯出 → Schema 驗證。
> 4. **雙變數 Diagnostic 驗收：** 完整演示 A/B Comparison → Evidence Collection → MetricSelector → DynamicEffectSize → DecisionTrace。
> 5. **Dependency Defense 驗收：** 展示含 Lot/Wafer/Chamber repeated measurements 的資料，確認系統產生 DependencyWarning。
> 6. **Correlation 驗收：** 展示高維 FDC dataset 的 memory guard、sparse representation、FDR correction。
> 7. **Numerical Stability 驗收：** 展示 p-value underflow, zero variance, NaN/Inf 等 edge cases 產生可解讀的 diagnostic status。
> 8. **JSON 驗收：** 匯出 JSON 為有效 JSON、不含 `NaN` / `Infinity` 字面量、通過 Schema 驗證。
> 9. **Statistical Semantics 驗收：** 所有輸出不含禁止的統計語義表述。

---

## **6. Release Gate**

Release 必須同時滿足：

| Gate | 要求 |
|------|------|
| **Correctness** | 統計公式與 reference implementation 一致 |
| **Data Quality** | NaN / Inf / missing data 有明確策略 |
| **Statistical Validity** | 不誤用 independence, normality, variance assumptions |
| **Scalability** | 高維 correlation 不造成非預期 memory blow-up |
| **Inference Safety** | Multiple Testing 有明確處理 |
| **Numerical Stability** | underflow / zero variance / invalid operation 有防禦 |
| **Explainability** | 每個推薦結果都有 DiagnosticEvidence + DecisionTrace |
| **Extensibility** | 新增統計方法不需修改既有核心 Router |
| **Architectural Integrity** | Domain Layer 不依賴 Pandas / Matplotlib |