# **scikit-trust — User Stories & Acceptance Criteria**

## **系統結案驗收清單 (Final Sign-off Checklist)**

---

## **Epic 1: 資料輪廓與檢定引擎 (Data Profiling & Testing)**

**目標：確保系統能安全、精準地在本地端處理巨量原始資料，提供可靠的統計特徵。**

### **US 1.1: 本地全量特徵掃描**

**User Story:**
身為一名資料工程師，我希望套件能在本地記憶體中完整掃描一維或二維陣列（不進行隨機抽樣），以便獲得精準的基礎統計量。

* **[ ] AC 1.1.1:** 給定一個包含 100 萬筆 Float64 的 NumPy Array，呼叫 `NumericProfiler.fit()` 必須在定義的效能基準內回傳結果。
* **[ ] AC 1.1.2:** 系統不能在未明確配置的情況下偷偷使用抽樣（Sampling），必須完整處理輸入資料。
* **[ ] AC 1.1.3:** 回傳物件必須是嚴格定義的 `DistributionProfile`，包含 `mean`, `variance`, `skewness` 等統計屬性。

### **US 1.2: 極端值防禦與警告**

**User Story:**
身為一名資料科學家，我希望在掃描含有 NaN 或 Inf 等髒資料時，系統能主動防禦並提供明確的資料品質資訊，而不是默默產生可能誤導的統計結果。

* **[ ] AC 1.2.1:** 給定包含 NaN 或 Inf 的陣列，Profiler 必須依照既定資料品質策略進行處理，並產生明確的 `DataQualityWarning` 或對應的資料品質結果。
* **[ ] AC 1.2.2:** 提供參數選項（如 `ignore_nan=True`）讓使用者決定缺失值的處理策略。
* **[ ] AC 1.2.3:** 系統輸出必須保留有效樣本數與被排除資料數量，使下游分析能判斷統計結果的資料基礎。

### **US 1.3: 統計分佈檢定 (K-S Test)**

**User Story:**
身為一名資料科學家，我希望對感測器數值進行分佈檢定，以便判斷後續統計分析可採用的假設與方法。

* **[ ] AC 1.3.1:** 呼叫 `DistributionTester.test(data, dist="norm")` 時，必須回傳 test statistic、p-value、sample size 與 hypothesis decision。
* **[ ] AC 1.3.2:** 單元測試中，檢定結果必須與 scipy.stats 對應實作進行驗證。
* **[ ] AC 1.3.3:** 系統輸出不得將 p > α 解釋為「資料已證明符合該分佈」，應描述為「insufficient evidence to reject the null hypothesis」。

### **US 1.4: 類別型資料比例與誤差推估**

**User Story:**
身為一名資料分析師，我希望系統能針對類別型或字串特徵進行全量掃描，並提供帶有統計不確定性的比例資訊，以準確反映類別分佈。

* **[ ] AC 1.4.1:** 系統能精準計算各獨立類別的出現次數與比例。
* **[ ] AC 1.4.2:** 系統必須提供適當的比例不確定性估計。
* **[ ] AC 1.4.3:** 對小樣本或接近 0/1 的比例，不得強制使用不適當的 Wald standard error；系統應支援適當的 binomial confidence interval 方法。

---

## **Epic 2: 不確定性誤差推估引擎 (Uncertainty Propagation)**

**目標：確保數學引擎能正確執行誤差傳遞，且完全不依賴外部資料容器。**

### **US 2.1: 基於 Jacobian 的解析法傳遞**

**User Story:**
身為一名演算法工程師，我希望針對線性或可微的特徵轉換公式，使用解析法進行誤差傳遞，以獲得高效且可重現的結果。

* **[ ] AC 2.1.1:** 給定兩個 `UncertaintyArray` 與數學轉換函式 f(A, B)，`AnalyticalPropagator` 必須回傳新的 `UncertaintyArray`。
* **[ ] AC 2.1.2:** 內部實作必須採用向量化運算，避免逐筆 Python-level iteration。
* **[ ] AC 2.1.3:** 當公式導致數學無效操作時，系統需產生明確的 `NumericalInstabilityError` 或等價診斷結果。

### **US 2.2: 基於蒙地卡羅的抽樣傳遞**

**User Story:**
身為一名機器學習工程師，我希望針對高度非線性或不可微的黑盒公式，使用蒙地卡羅法推估最終的不確定性範圍。

* **[ ] AC 2.2.1:** `MonteCarloPropagator` 必須允許使用者自定義 `n_simulations`。
* **[ ] AC 2.2.2:** Random Seed 必須可以被固定，以保證結果可重現。
* **[ ] AC 2.2.3:** 輸出結果必須包含 simulation configuration，使分析結果具備 reproducibility。

---

## **Epic 3: 生態系與介面整合 (Adapters: Pandas & Matplotlib)**

**目標：提供流暢的使用者體驗，同時保衛核心領域的乾淨度。**

### **US 3.1: Pandas DataFrame 無縫擴充**

**User Story:**
身為一名習慣使用 Pandas 的分析師，我希望可以直接在 DataFrame 上呼叫 Profiling 函式，而不需要手動將 DataFrame 轉換為 NumPy Array。

* **[ ] AC 3.1.1:** 必須成功註冊 Pandas Accessor，例如 `df.trust.profile(...)`。
* **[ ] AC 3.1.2:** `profiling` 與 core domain modules 不得依賴 Pandas。
* **[ ] AC 3.1.3:** Adapter 必須根據欄位型態正確派發至對應的 profiler。
* **[ ] AC 3.1.4:** Adapter 不得將 Pandas-specific object 傳入核心 domain service。

### **US 3.2: 誤差帶繪圖輔助工具 (Viz Helper)**

**User Story:**
身為一名分析師，我希望在推估完 Uncertainty 後，能輕易畫出帶有信心水準誤差帶的折線圖。

* **[ ] AC 3.2.1:** `viz.plot_uncertainty_trend(...)` 能正確渲染折線與 uncertainty band。
* **[ ] AC 3.2.2:** Core domain modules 不得依賴 Matplotlib。

---

## **Epic 4: 工程品質、交付與部署 (Engineering & Delivery)**

**目標：符合現代化 Python 套件標準，隨時可供團隊透過 Git 進行安裝與維護。**

### **US 4.1: 現代化套件建置與安裝**

**User Story:**
身為一名 DevOps / MLOps 工程師，我希望這個套件採用現代化 Python packaging 標準，以方便整合進 Docker Image 與 CI/CD pipeline。

* **[ ] AC 4.1.1:** 專案根目錄必須使用 `pyproject.toml`，且不使用 `setup.py`。
* **[ ] AC 4.1.2:** 在乾淨 Python environment 中必須可以從 Git repository 成功安裝。
* **[ ] AC 4.1.3:** Optional dependencies 必須正確定義，例如 `[viz]`。

### **US 4.2: 型別安全與程式碼檢驗**

**User Story:**
身為團隊的 Tech Lead，我希望套件的程式碼品質受到嚴格管控，以確保核心統計邏輯可長期維護。

* **[ ] AC 4.2.1:** 全專案必須具備完整 Type Hints。
* **[ ] AC 4.2.2:** CI 必須通過 `mypy --strict`。
* **[ ] AC 4.2.3:** Test Coverage 必須達到 85% 以上。
* **[ ] AC 4.2.4:** Core contracts 必須包含 Property-Based Testing。

---

## **Epic 5: 雙變數智慧診斷引擎 (Bivariate Statistical Intelligence)**

**目標：將 scikit-trust 從「單變數統計分析工具」擴充為具備資料型態辨識、樣本結構診斷、統計證據評估與方法推薦能力的雙變數智慧診斷引擎。**

**核心原則：**
The system provides statistical evidence and recommendations, not absolute truth.
系統不得將統計檢定結果解讀為「證明資料符合某項假設」，而應提供：
Data → Diagnostics → Evidence → Recommendation → Decision Trace

---

### **US 5.1: 設備效能與製程配方比較 (A/B Comparison)**

**User Story:**
身為製程整合工程師，我希望系統能協助比較不同機台或製程條件下的 Removal Rate 等關鍵指標差異，並根據資料特性推薦適當的效應量，以量化設備升級或製程變更的實質效益。

**Acceptance Criteria**

* **[ ] AC 5.1.1 — Sample Structure:** 系統必須在進行效應量分析前辨識樣本結構，至少區分 Independent、Paired 與 Repeated Measurements 等情境。
* **[ ] AC 5.1.2 — Dependency Detection:** 若資料包含 Lot、Wafer、Chamber、Tool 或其他可能代表重複測量層級的識別資訊，系統必須產生 DependencyWarning 或 DependencyEvidence。
* **[ ] AC 5.1.3 — Variance Diagnostics:** 系統應使用適當的 robust variance diagnostic，例如 Brown-Forsythe / median-centered Levene test，評估兩組變異程度差異。
* **[ ] AC 5.1.4 — Effect-size Recommendation:** 當證據支持變異數不具同質性，且 Reference / Control group 的標準差具有足夠穩定性時，系統應優先推薦 Glass’s Δ。
* **[ ] AC 5.1.5 — Small Sample:** 當樣本數不足以支持可靠的常態性或變異數判斷時，系統不得僅依據檢定結果強制選擇 Cohen’s d；應回傳 InsufficientEvidence 或提供較保守的方法推薦。
* **[ ] AC 5.1.6 — Imbalanced Groups:** 系統必須檢查 Group Size Ratio。當兩組樣本數高度不平衡時，必須產生 ImbalancedSampleWarning，並將樣本不平衡納入推薦決策的 DiagnosticEvidence。
* **[ ] AC 5.1.7 — Decision Trace:** `DynamicEffectSize` 必須保存推薦方法、主要統計證據、樣本結構、資料品質資訊與 decision_trace。
* **[ ] AC 5.1.8 — Numerical Safety:** 當 Reference / Control group 的標準差為零或效應量無法定義時，系統不得產生無意義的 NaN 或 Inf 作為正常結果，必須回傳明確的 diagnostic status。

---

### **US 5.2: FDC 批次特徵漂移與異常監控**

**User Story:**
身為 FDC 演算法工程師，我希望在比對正常批次與異常批次的 Lot/Wafer-level 聚合特徵時，系統能診斷資料分佈、離群值、缺失資料與時間相依性，並推薦適當的差異評估方法。

**Acceptance Criteria**

* **[ ] AC 5.2.1 — Robust Distribution Diagnosis:** 當資料具有明顯偏態、極端離群值或缺乏足夠證據支持常態性時，系統應提供 Cliff’s δ 等無母數效應量作為推薦選項。
* **[ ] AC 5.2.2 — Missing Data Strategy:** 雙變數分析必須明確記錄 missing_data_strategy，至少支援明確定義的 pairwise_complete 或其他受支援策略。
* **[ ] AC 5.2.3 — Missing Data Evidence:** 輸出必須包含有效樣本數、缺失數量及缺失比例，避免使用者將不同 pair 的統計結果誤認為使用相同樣本數。
* **[ ] AC 5.2.4 — NaN / Inf Defense:** NaN 與 Inf 不得未經處理直接進入統計計算。系統必須依據既定資料品質策略處理並留下 evidence。
* **[ ] AC 5.2.5 — Temporal Dependency:** 若輸入資料仍維持 timestamp-level time-series resolution，系統必須辨識其可能存在 temporal dependency / autocorrelation。
* **[ ] AC 5.2.6 — Pseudo-replication Defense:** 系統不得在沒有 Dependency Warning 或明確 sample-structure declaration 的情況下，將同一 Lot、Wafer、Chamber 或連續 timestamp 的觀測值直接視為完全獨立樣本。
* **[ ] AC 5.2.7 — Blocking / Aggregation Recommendation:** 若偵測到明顯的 temporal dependency 或 repeated measurements，系統應建議使用者進行適當的 Lot/Wafer-level aggregation、blocking 或其他 dependency-aware analysis。

---

### **US 5.3: 多變數關聯性與特徵篩選 (Feature Screening)**

**User Story:**
身為資料科學家，我希望在建立機器學習模型前快速產生特徵間的關聯性資訊，以識別高度相關的 Feature Pairs，作為特徵篩選的第一階段依據。

**Acceptance Criteria**

* **[ ] AC 5.3.1 — Correlation API:** 提供 `df.trust.correlation(method="pearson")` 的 API。
* **[ ] AC 5.3.2 — Pearson MVP:** MVP 必須支援 Pearson’s r。
* **[ ] AC 5.3.3 — Future Statistical Extensions:** 架構必須預留 Spearman’s ρ、Kendall’s τ 等 rank-based correlation 方法的擴充能力。
* **[ ] AC 5.3.4 — Missing Data:** Correlation result 必須明確記錄缺失資料處理策略與每個 correlation pair 的有效樣本數。
* **[ ] AC 5.3.5 — High Dimensionality Guard:** 當 feature 數量超過系統定義門檻時，系統不得無條件將完整 $N \times N$ correlation matrix 作為大型 JSON payload 輸出。
* **[ ] AC 5.3.6 — Sparse / Filtered Representation:** 系統必須支援 correlation result filtering，例如僅保留 $|r| \geq threshold$ 的 Feature Pairs。
* **[ ] AC 5.3.7 — Memory Safety:** 系統必須在 correlation matrix 建立、轉換與輸出過程中具備明確的 memory guard，避免因高維度資料導致非預期的 OOM。
* **[ ] AC 5.3.8 — Multiple Testing:** 當系統對大量 Feature Pairs 執行 hypothesis testing 時，若提供 statistical significance 結果，必須支援 multiple-testing correction。
* **[ ] AC 5.3.9 — FDR Control:** MVP 至少應支援 Benjamini-Hochberg FDR correction；系統必須區分 raw p-value 與 adjusted p-value。
* **[ ] AC 5.3.10 — Feature Screening Semantics:** 文件與輸出必須明確聲明 correlation 不等於 causation，且 Pairwise Correlation Matrix 不得被視為完整 Multicollinearity Diagnosis。
* **[ ] AC 5.3.11 — Non-linear Dependency Extension:** 架構必須預留 Mutual Information 或 Distance Correlation 等非線性 dependency measure 的擴充能力。

---

### **US 5.4: 雙變數自動診斷與統計方法推薦 (Bivariate Automatic Diagnostics)**

**User Story:**
身為資料科學家，我希望系統能根據資料型態、樣本結構、資料品質與統計證據，自動推薦適合的雙變數統計指標，並提供可追溯的決策依據，而不是武斷地回傳單一統計方法。

**Acceptance Criteria**

* **[ ] AC 5.4.1 — Data Type Detection:** 系統必須辨識輸入變數的資料型態，包括至少 Continuous, Categorical。
* **[ ] AC 5.4.2 — Sample Structure:** 系統必須評估 Independent, Paired, Repeated Measurements, Hierarchical / Grouped observations。
* **[ ] AC 5.4.3 — Diagnostic Evidence:** 系統必須產生 `DiagnosticEvidence`，至少涵蓋 Normality, Variance, Outlier, Sample Size, Group Balance, Dependency, Missing Data。
* **[ ] AC 5.4.4 — Statistical Test Evidence:** 每一項 hypothesis test 必須保存 test name, test statistic, raw p-value, sample size, alpha, decision / evidence interpretation。
* **[ ] AC 5.4.5 — P-value Semantics:** 當 $p > \alpha$ 時，系統必須使用 “Insufficient evidence to reject the null hypothesis.” 等統計語義正確的描述。禁止輸出 "Data is normally distributed.", "Equal variance = True.", "Null hypothesis is proven."
* **[ ] AC 5.4.6 — P-value Underflow:** 若數值運算造成 p-value underflow 至 0.0，系統必須保留其「極小 p-value」的語義，不得將 0.0 解讀為數學上的絕對零機率。
* **[ ] AC 5.4.7 — P-value Representation:** `HypothesisTestResult` 必須能區分實際數值、數值下限或顯示用格式，例如 `p < 1e-300`，而不是單純依賴 `p_value == 0.0`。
* **[ ] AC 5.4.8 — Multiple Testing Awareness:** 若一次診斷涉及多個 hypothesis tests，系統必須能標示 Multiple Testing 狀態，並在支援的情況下提供 adjusted p-value。
* **[ ] AC 5.4.9 — Evidence Level:** `DiagnosticEvidence` 必須提供明確的 evidence level (High, Moderate, Low, Insufficient)。Evidence Level 不得直接等同於「真 / 假」。
* **[ ] AC 5.4.10 — Recommendation:** 系統必須根據 evidence 與 sample structure 產生 `RecommendedMetric`。
* **[ ] AC 5.4.11 — Decision Trace:** DiagnosticReport 必須保存完整 `DecisionTrace`，使使用者能追溯：Data Type → Sample Structure → Diagnostics → Evidence → Recommendation
* **[ ] AC 5.4.12 — Insufficient Evidence:** 當資料品質、樣本數或樣本結構不足以支持可靠判斷時，系統應回傳 Warning / Insufficient Evidence，而非強制選擇統計方法。
* **[ ] AC 5.4.13 — Strategy Registry:** 統計方法推薦必須透過可擴充的 Strategy Registry / Metric Registry 管理，不得將所有方法選擇邏輯硬編碼於單一 Router。
* **[ ] AC 5.4.14 — Report Separation:** 大型雙變數診斷結果（如 `CorrelationResult`、`DynamicEffectSize`、`DiagnosticReport`）不得無條件塞入 `DatasetReport`。系統必須支援將 Bivariate Diagnostic 結果獨立產生與序列化，避免 JSON payload explosion。

---

## **Epic 5 — MVP Statistical Method Scope**

MVP 應明確限制第一階段實際實作範圍。

**MVP 必須支援：**
* Continuous vs Continuous: Pearson’s r
* Two Independent Continuous Groups: Cohen’s d
* Small Sample: Hedges’ g
* Unequal Variance: Glass’s Δ
* Non-parametric Group Difference: Cliff’s δ
* Variance Diagnostic: Brown-Forsythe / median-centered Levene
* Multiple Testing: Benjamini-Hochberg FDR
* Missing Data: 明確定義的 pairwise / complete-case strategy
* Dependency: Dependency detection + warning
* Evidence: DiagnosticEvidence
* Decision: DecisionTrace
* Numerical Safety: Underflow / zero variance handling

**Future Extension — Architecture Reserved:**
* Spearman’s ρ, Kendall’s τ, Mutual Information, Distance Correlation, VIF, Partial Correlation, Paired Effect Size, Repeated-measures analysis, Hierarchical / mixed-effects models, Time-series dependency-aware statistics。

---

## **Epic 5 — Domain Contracts**

Epic 5 的統計診斷結果必須透過明確的 domain contracts 傳遞，而不是回傳散亂的 `dict[str, Any]`。至少包含以下概念：

* **`HypothesisTestResult`**
  應能描述：test_name, statistic, p_value, p_value_display, alpha, sample_size, decision, evidence_level

* **`DiagnosticEvidence`**
  應能描述：data_type, sample_structure, sample_sizes, group_size_ratio, missing_data_strategy, missing_count, missing_ratio, normality_evidence, variance_evidence, outlier_evidence, dependency_evidence, multiple_testing_evidence

* **`DynamicEffectSize`**
  應能描述：metric, estimate, standard_error, confidence_interval, sample_sizes, diagnostic_evidence, decision_trace, status, warnings

* **`CorrelationResult`**
  應能描述：method, feature_names, correlation_matrix / sparse_pairs, sample_size, missing_data_strategy, raw_p_values, adjusted_p_values, multiple_testing_method, threshold

---

## **Epic 5 — 統計方法選擇原則**

系統的責任是提供 evidence-based recommendation，而不是宣稱資料「符合」或「不符合」某個統計假設。

```text
                    ┌─────────────────┐
                    │   Input Data    │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │  Data Type      │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Sample Structure │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Data Quality    │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Statistical     │
                    │ Diagnostics     │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Evidence        │
                    │ Evaluation      │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Metric /        │
                    │ Strategy        │
                    │ Selection       │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Recommendation  │
                    │ + DecisionTrace │
                    └─────────────────┘
```

---

## **結案驗收會議 (Sign-off Meeting)**

1. **Demo 階段：** 展示 Notebook：Pandas DataFrame → Data Profiling → Statistical Diagnostics → Bivariate Analysis → Effect Size / Correlation → Decision Trace。
2. **Dependency Defense Demo：** 展示包含多個 Wafer / Lot / Chamber repeated measurements 的資料，確認系統能偵測 dependency risk，而不是將所有 timestamp 視為獨立樣本。
3. **High-Dimensionality Demo：** 使用高維 FDC dataset 展示 correlation matrix 的 memory guard、threshold filtering 與 sparse representation。
4. **Statistical Evidence Demo：** 展示 normality、variance、sample imbalance、missing data 與 dependency evidence。
5. **Multiple Testing Demo：** 展示大量 feature pairs 的 raw p-value 與 BH-adjusted p-value，確認系統不會將未校正的偽陽性直接標示為 significant。
6. **Numerical Stability Demo：** 展示極小 p-value、zero variance、NaN、Inf 等 edge cases，確認系統產生可解讀的 diagnostic status。
7. **Code Review：** 確認 core 與 domain layer 不依賴 Pandas / Matplotlib。
8. **CI/CD：** 展示 type checking、linting、unit testing、property-based testing 與 coverage 結果。
9. **Installation：** 在乾淨 Python environment 中透過 Git repository 安裝並成功執行完整 smoke test。

---

## **Release Gate**

scikit-trust 在 Epic 5 完成後，Release 必須同時滿足：

* **Correctness** → 統計公式與 reference implementation 一致
* **Data Quality** → NaN / Inf / missing data 有明確策略
* **Statistical Validity** → 不誤用 independence, normality, variance assumptions
* **Scalability** → 高維 correlation 不造成非預期 memory blow-up
* **Inference Safety** → Multiple Testing 有明確處理
* **Numerical Stability** → underflow / zero variance / invalid operation 有防禦
* **Explainability** → 每個推薦結果都有 DiagnosticEvidence + DecisionTrace
* **Extensibility** → 新增統計方法不需要修改既有核心 Router
* **Architectural Integrity** → Domain Layer 不依賴 Pandas / Matplotlib 等外部資料容器與視覺化框架