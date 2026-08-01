# **軟體開發需求規格書 (Software Requirements Specification)**

**專案名稱：** ds-data-miner — 探索式資料分析 (EDA) 計算核心引擎
**文件版本：** v3.0
**目標受眾：** 資料科學家 (Data Scientists)、機器學習工程師 (ML Engineers)、資料工程師 (Data Engineers)

## **1. 產品概述 (Product Overview)**

### **1.1 專案背景與目的**

在資料工程與機器學習管線（Pipeline）中，確保輸入資料的品質（Data Quality）與量化原始統計特徵的可靠性，是建立高可信度模型的第一道關卡。

本專案（`ds-data-miner`）原名 `scikit-trust`，前身將資料探索（EDA）、多變數誤差傳遞（Uncertainty Propagation）與視覺化繪圖（Visualization）耦合於單一套件中。經過架構審查後，為符合 Unix 哲學（做一件事並做好），我們將系統拆分為**三個獨立的 Library**：

1. **`ds-data-miner`（本階段重點）：** 探索引擎計算核心。唯一職責是吞入原始資料，在**本地 Python Runtime 記憶體中進行嚴格的全表掃描運算**，並將包含統計特徵、資料品質指標與原生統計誤差的中介資料，統一匯出為標準化的 **JSON** 格式。
2. **`ds-data-miner-vis`（未來階段）：** 讀取前述 JSON 檔案，負責渲染視覺化與製圖（如 Matplotlib）。
3. **`ds-data-miner-reporter`（未來階段）：** 讀取前述 JSON 檔案，負責產出完整的 PDF/HTML 報告。

### **1.2 核心價值**

* **高可靠度：** 支援本地記憶體全量資料掃描，拒絕因抽樣造成的統計偏差。
* **工程解耦：** 採用六角架構（Hexagonal Architecture），核心數學運算不受外部框架（如 Pandas）改版影響。視覺化與報告產出完全解耦至獨立套件。
* **標準化輸出：** 所有分析結果以 JSON 格式匯出，作為下游視覺化與報告工具的標準資料合約。
* **無縫整合：** 透過轉接器（Adapters）提供流暢的 API，支援 `pip install git+...` 直接整合進企業現有專案。

## **2. 系統架構與領域驅動設計 (Architecture & DDD)**

本系統嚴格遵守單一職責原則（SRP）與依賴反轉原則（DIP），系統邊界劃分如下：

| 層級分類 | 模組名稱 | 權責定義 | 依賴限制 |
| :---- | :---- | :---- | :---- |
| **介面轉接層 (Adapter)** | my\_lib.pandas\_ext | 封裝 Pandas Accessor，將 DataFrame 轉換為核心合約物件 | 依賴 pandas, my\_lib.core |
| **匯出層 (Export)** | my\_lib.export | 將 Profile 合約物件序列化為標準化 JSON 檔案 | 依賴 my\_lib.core |
| **核心領域層 (Domain)** | my\_lib.profiling | 擔任「觀察者」，執行全量掃描、統計特徵萃取與資料品質檢驗 | **僅**依賴 numpy, scipy, my\_lib.core |
| **資料合約層 (Contract)** | my\_lib.core | 定義跨模組通用的不可變資料結構（Pydantic Models） | 僅依賴 pydantic |

## **3. 核心功能需求 (Functional Requirements)**

### **3.1 my\_lib.core (核心資料合約)**

* **[REQ-CORE-01] 數值型統計合約：** 必須定義 `DistributionProfile`（Pydantic Model），至少包含以下屬性：
    * 基礎統計量：`mean`, `variance`, `std`, `skewness`, `kurtosis`, `median`, `min`, `max`
    * 分位數：`q25`, `q75`（或 `percentiles` 字典）
    * 樣本資訊：`n_samples`, `n_valid`
    * 資料品質指標：`missing_count`, `missing_ratio`, `inf_count`
    * **統計誤差：** `sem`（平均數標準誤）, `ci_lower`, `ci_upper`（信賴區間，預設 95%）
    * **直方圖表示：** `histogram_bin_edges: list[float]`, `histogram_counts: list[int]`（供下游繪圖使用，不儲存原始陣列）
    * 分佈檢定：`distribution_type`, `ks_statistic`, `ks_p_value`

* **[REQ-CORE-02] 類別型統計合約：** 必須定義 `CategoricalProfile`（Pydantic Model），包含：
    * 各類別統計：`stats: list[CategoryStats]`，其中 `CategoryStats` 含 `category`, `count`, `proportion`, `std_error`（基於二項式分佈 $\sigma = \sqrt{p(1-p)/N}$）
    * 樣本資訊：`n_total`, `n_unique`
    * 資料品質：`missing_count`, `missing_ratio`
    * 高基數標記：`is_high_cardinality: bool`, `truncated_at: int | None`

* **[REQ-CORE-03] 時序型統計合約：** 必須定義 `DatetimeProfile`（Pydantic Model），包含：
    * 時間範圍：`start`, `end`, `duration`
    * 單調性驗證：`is_monotonic_increasing: bool`
    * 斷層分析：`gap_count: int`, `gap_locations: list[dict]`（含斷層起止時間與持續時間）
    * 頻率推估：`inferred_freq: str | None`
    * 樣本資訊：`n_samples`, `missing_count`, `missing_ratio`

* **[REQ-CORE-04] 資料集報告合約：** 必須定義 `DatasetReport`（Pydantic Model），作為頂層聚合容器，包含：
    * 元資料：`dataset_name`, `created_at`, `ds_data_miner_version`, `total_rows`, `total_columns`
    * 全域品質指標：`duplicate_row_count`, `duplicate_row_ratio`
    * 各欄位的 Profile：`columns: dict[str, DistributionProfile | CategoricalProfile | DatetimeProfile]`

* **[REQ-CORE-05] JSON 序列化能力：** 所有合約必須滿足：
    * 支援 `model.model_dump_json()` 直接匯出為有效 JSON 字串。
    * 特殊浮點數處理：`NaN` → `null`, `Inf` / `-Inf` → `null`（或自定義標記）。
    * NumPy 原生型別（`np.float64`, `np.int64` 等）必須在序列化前自動轉換為 Python 原生型別。

### **3.2 my\_lib.profiling (資料統計與品質檢驗)**

* **[REQ-PROF-01] 全量掃描：** 必須具備在本地 Python Runtime 環境中，高效掃描記憶體內全量資料（1D NumPy Array / Pandas Series）的能力。**嚴禁任何形式的抽樣。**
* **[REQ-PROF-02] 數值型基礎統計量：** `NumericProfiler` 能夠計算平均數、變異數、標準差、偏度、峰度、中位數、分位數、最小值與最大值。
* **[REQ-PROF-03] 數值型統計誤差：** `NumericProfiler` 必須計算平均數標準誤 (SEM = $\sigma / \sqrt{N}$) 與信賴區間 (CI)，並將結果寫入合約。
* **[REQ-PROF-04] 數值型直方圖預計算：** `NumericProfiler` 必須在 fit 階段計算直方圖的 `bin_edges` 與 `counts`，並存入合約中，**不得儲存原始資料陣列**。
* **[REQ-PROF-05] 分佈檢定：** 必須實作統計檢定演算法（如 K-S Test），並輸出明確的 P-value 以檢驗資料是否符合特定機率分配（如常態分配）。
* **[REQ-PROF-06] 極端值防禦：** 掃描過程中若遭遇 NaN 或 Inf，必須具備安全的容錯機制（提供 `ignore_nan` 參數選項），或拋出明確的自定義例外。
* **[REQ-PROF-07] 類別型全量掃描：** `CategoricalProfiler` 必須在本地記憶體中完整掃描類別型資料，計算各類別的出現次數、比例與二項式標準誤。
* **[REQ-PROF-08] 高基數防禦：** `CategoricalProfiler` 遭遇高基數欄位（如 UUID）時，必須自動偵測（閾值可配置，預設 100），截斷至 Top-N 類別，並將剩餘類別歸入 `_OTHER_` 桶，同時發出 `HighCardinalityWarning`。
* **[REQ-PROF-09] 時序型特徵分析：** `DatetimeProfiler` 必須驗證時間戳記是否單調遞增、偵測時間斷層（Gaps），並推估採樣頻率。
* **[REQ-PROF-10] 缺失值比例：** 所有 Profiler 在掃描時，必須統計 missing（NaN / NaT / None）的筆數與比例，寫入對應合約的 `missing_count` 與 `missing_ratio` 欄位。
* **[REQ-PROF-11] 重複紀錄檢驗：** `DatasetReport` 層級必須支援全表重複列偵測，輸出 `duplicate_row_count` 與 `duplicate_row_ratio`。

### **3.3 my\_lib.export (JSON 匯出)**

* **[REQ-EXPORT-01] JSON 檔案匯出：** 提供 `ReportExporter` 類別，接收 `DatasetReport` 物件，匯出為格式化（縮排）、高可讀性的 JSON 檔案。
* **[REQ-EXPORT-02] JSON Schema 產出：** 支援透過 Pydantic `model_json_schema()` 自動產出對應的 JSON Schema 定義，供下游消費者（`ds-data-miner-vis`, `ds-data-miner-reporter`）進行欄位驗證。

### **3.4 介面轉接層 (Adapters)**

* **[REQ-ADPT-01] Pandas 整合：** 提供 Extension/Accessor（`df.miner`），讓使用者能執行如 `df.miner.profile()` 的直覺操作。
* **[REQ-ADPT-02] 動態型別路由：** 轉接層必須依據 DataFrame 欄位的 dtype 自動派發至對應的 Profiler（numeric → `NumericProfiler`、object/category → `CategoricalProfiler`、datetime64 → `DatetimeProfiler`）。
* **[REQ-ADPT-03] 全表掃描匯出：** 轉接層必須支援一次性掃描 DataFrame 全部欄位，聚合為 `DatasetReport`，並透過 `ReportExporter` 匯出 JSON。

## **4. 非功能性需求 (Non-Functional Requirements)**

### **4.1 效能與資源管理 (Performance)**

* **[NFR-PERF-01]** 核心數學運算必須全面採用 NumPy/Pandas C-extension 向量化操作（Vectorization）。嚴禁使用 Python 原生 `for` 迴圈處理 Array 等級資料。
* **[NFR-PERF-02]** Profiling 掃描記憶體資料時，不得產生不必要的 DataFrame 深拷貝（Deep Copy），以避免 OOM 異常。

### **4.2 序列化與型別安全 (Serialization)**

* **[NFR-SERIAL-01]** 所有核心資料合約必須使用 **Pydantic v2 BaseModel**，並搭配自定義 JSON Encoder 處理：
    * `float('nan')` → JSON `null`
    * `float('inf')` / `float('-inf')` → JSON `null`
    * `numpy.float64` / `numpy.int64` 等 → Python 原生 `float` / `int`
    * `numpy.bool_` → Python 原生 `bool`
    * `datetime` / `Timestamp` → ISO 8601 字串

### **4.3 封裝與部署 (Packaging & Deployment)**

* **[NFR-PKG-01] 現代化建置：** 必須廢棄傳統 `setup.py`，全面採用 PEP 621 標準的 `pyproject.toml` 進行依賴與元資料管理（推薦使用 Poetry 或 uv）。
* **[NFR-PKG-02] Git 安裝支援：** 套件目錄結構必須標準化，確保使用者可透過 `pip install git+https://[repository_url]` 順利安裝並解析依賴樹。
* **[NFR-PKG-03] 核心依賴最小化：** 核心安裝僅包含 `numpy`, `scipy`, `pydantic`。Pandas 為可選依賴（`pip install .[pandas]`）。

### **4.4 程式碼品質與測試 (Quality & Testing)**

* **[NFR-QA-01] 靜態型別：** 專案必須 100% 覆蓋 Type Hints，並通過 `mypy --strict` 檢驗。
* **[NFR-QA-02] 數值穩定度測試：** 必須針對浮點數溢位（Overflow/Underflow）與零除錯（Division by Zero）建立邊界測試。
* **[NFR-QA-03] 演算法驗證：** 統計計算結果必須在單元測試中與 `scipy` 或 `statsmodels` 等成熟套件的 Baseline 進行比對，容許誤差需小於 $10^{-7}$。
* **[NFR-QA-04] JSON 往返測試 (Round-trip)：** 所有合約物件必須通過 `model → JSON → model` 的往返測試，確保序列化/反序列化後資料完全一致。

## **5. 驗收標準 (Acceptance Criteria)**

> 1. **安裝驗收：** 能夠在乾淨的 Python 虛擬環境中，透過 Git URL 成功安裝，且 `import ds_data_miner` 過程無報錯。
> 2. **架構驗收：** 執行依賴檢查工具時，`core`, `profiling` 兩個核心模組內部，絕對不可出現 `import pandas` 或 `import matplotlib`。
> 3. **流程驗收（User Journey）：** 能夠提供一份完整的範例腳本，無縫演示「讀取 CSV (Pandas) → 全表資料統計掃描 (Profiling) → 匯出標準化 JSON 報告 → 驗證 JSON Schema 正確性」的端到端（End-to-End）分析流程。
> 4. **JSON 驗收：** 匯出的 JSON 檔案必須：(a) 為有效 JSON，(b) 不含 `NaN` 或 `Infinity` 字面量，(c) 可被 JSON Schema 驗證通過，(d) 具備良好的人類可讀性（含縮排格式化）。