這是一份專為開發團隊與利益關係人（Stakeholders）準備的 **使用者故事與驗收標準清單（User Stories & Acceptance Criteria Checklist）**。
在敏捷開發（Agile）與軟體工程實務中，這份清單將作為結案前的 **「完成定義」（Definition of Done, DoD）**。我們依據收斂後的三層架構（Profiling → Export → Adapter），將其劃分為四個 Epic（史詩/主題）。在結案審查（Sprint Review / Final Sign-off）時，團隊必須逐一展示並打勾確認。

# **系統結案驗收清單 (Final Sign-off Checklist)**

## **Epic 1: 資料輪廓與品質引擎 (Data Profiling & Quality Engine)**

**目標：確保系統能安全、精準地在本地端處理巨量原始資料，提供可靠的統計特徵與資料品質指標。**

### **US 1.1: 數值型全量特徵掃描**

**User Story:** 身為一名資料工程師，我希望套件能在本地記憶體中完整掃描一維數值陣列（不進行隨機抽樣），以便獲得絕對精準的基礎統計量。

* **[ ] AC 1.1.1:** 給定一個包含 100 萬筆 Float64 的 NumPy Array，呼叫 `NumericProfiler.fit()` 必須在合理時間內（如 1 秒內）回傳結果。
* **[ ] AC 1.1.2:** 系統不能在底層偷偷使用抽樣（Sampling），必須 100% 掃過所有資料。
* **[ ] AC 1.1.3:** 回傳的物件必須是嚴格定義的 `DistributionProfile` Pydantic Model，包含 `mean`, `variance`, `std`, `skewness`, `kurtosis`, `median`, `min`, `max`, `q25`, `q75` 等屬性。
* **[ ] AC 1.1.4:** `DistributionProfile` 必須包含 `sem`（平均數標準誤）欄位，計算公式為 $SEM = \sigma / \sqrt{N}$。
* **[ ] AC 1.1.5:** `DistributionProfile` 必須包含 `ci_lower` 與 `ci_upper`（95% 信賴區間）欄位。
* **[ ] AC 1.1.6:** `DistributionProfile` 必須包含 `histogram_bin_edges` 與 `histogram_counts`，且**不得**將原始陣列儲存於合約物件中。

### **US 1.2: 極端值防禦與警告**

**User Story:** 身為一名資料科學家，我希望在掃描含有 NaN 或 Inf 等髒資料時，系統能主動防禦並給出警告，而不是默默計算出錯誤的數值。

* **[ ] AC 1.2.1:** 給定一個含有 NaN 或 `np.inf` 的陣列，Profiler 必須依據 `ignore_nan` 參數拋出 `DataQualityError` 或安全跳過。
* **[ ] AC 1.2.2:** 給定一個全部為 NaN 的陣列，Profiler 必須拋出 `DataQualityError`，不得回傳包含錯誤數值的 Profile。
* **[ ] AC 1.2.3:** `DistributionProfile` 必須包含 `inf_count` 欄位，精確記錄 Inf 值的數量。

### **US 1.3: 統計分佈檢定 (K-S Test)**

**User Story:** 身為一名資料科學家，我希望對感測器數值進行常態分配檢定，以便決定後續要使用何種統計模型。

* **[ ] AC 1.3.1:** 呼叫 `DistributionTester.test(data, dist="norm")` 時，必須回傳包含 `statistic` 與 `p_value` 的字典。
* **[ ] AC 1.3.2:** 單元測試中，該檢定結果必須與 `scipy.stats.kstest` 的結果進行比對，且絕對誤差 (atol) 需小於 $10^{-7}$。

### **US 1.4: 類別型資料比例與誤差推估**

**User Story:** 身為一名資料分析師，我希望系統能針對類別型或字串特徵進行全量掃描，並提供帶有統計誤差的比例，以準確反映類別分佈的不確定性。

* **[ ] AC 1.4.1:** 系統能精準計算陣列中各獨立類別的出現次數與比例。
* **[ ] AC 1.4.2:** 系統必須自動套用二項式分佈標準誤公式 $\sigma = \sqrt{p(1-p)/N}$ 來計算各類別的誤差。
* **[ ] AC 1.4.3:** 回傳的 `CategoricalProfile` 必須包含 `n_unique` 欄位。

### **US 1.5: 高基數防禦 (High Cardinality Defense)**

**User Story:** 身為一名資料工程師，我希望系統在遇到高基數欄位（如 UUID）時不會崩潰或耗盡記憶體，而是自動截斷並通知我。

* **[ ] AC 1.5.1:** `CategoricalProfiler` 接受 `max_cardinality` 參數（預設 100）。
* **[ ] AC 1.5.2:** 當唯一值數量超過 `max_cardinality` 時，系統必須自動截斷至 Top-N（依出現次數排序），並將剩餘歸入 `_OTHER_` 桶。
* **[ ] AC 1.5.3:** 截斷時必須發出 `HighCardinalityWarning`。
* **[ ] AC 1.5.4:** `CategoricalProfile` 的 `is_high_cardinality` 為 `True`，`truncated_at` 記錄實際截斷閾值。

### **US 1.6: 時序型特徵分析 (Datetime Profiling)**

**User Story:** 身為一名時序資料分析師，我希望系統能驗證時間戳記的品質，包含是否單調遞增、有無斷層、以及推估採樣頻率。

* **[ ] AC 1.6.1:** `DatetimeProfiler.fit()` 回傳 `DatetimeProfile`，包含 `start`, `end`, `duration_seconds`。
* **[ ] AC 1.6.2:** `is_monotonic_increasing` 正確反映時間序列是否嚴格單調遞增。
* **[ ] AC 1.6.3:** `gap_count` 與 `gap_locations` 能正確識別時間斷層（以中位時間差的倍數作為閾值）。
* **[ ] AC 1.6.4:** `inferred_freq` 能推估出合理的採樣頻率（如 "1min", "1h"），若時間間隔不規則則回傳 `None`。

### **US 1.7: 缺失值與重複紀錄檢驗**

**User Story:** 身為一名 Data Quality 工程師，我希望系統能在掃描時自動統計缺失值比例與重複紀錄數，作為資料品質的基礎指標。

* **[ ] AC 1.7.1:** 所有 Profiler（Numeric, Categorical, Datetime）的回傳合約必須包含 `missing_count` 與 `missing_ratio` 欄位。
* **[ ] AC 1.7.2:** `DatasetReport` 必須包含 `duplicate_row_count` 與 `duplicate_row_ratio`，用於全表重複列偵測。
* **[ ] AC 1.7.3:** `missing_ratio` 的計算公式為 `missing_count / n_samples`，精確到小數點後六位。

---

## **Epic 2: JSON 匯出與資料合約 (JSON Export & Data Contracts)**

**目標：確保所有分析結果都能被序列化為高品質的標準化 JSON，作為下游系統的資料合約。**

### **US 2.1: JSON 序列化正確性**

**User Story:** 身為一名資料工程師，我希望所有 Profile 合約都能被序列化為有效的 JSON 字串，且不含任何會導致下游解析失敗的特殊值。

* **[ ] AC 2.1.1:** 呼叫 `model.model_dump_json()` 必須產出有效的 JSON 字串。
* **[ ] AC 2.1.2:** JSON 中不得出現 `NaN`、`Infinity` 或 `-Infinity` 字面量，必須轉換為 `null`。
* **[ ] AC 2.1.3:** NumPy 型別（`np.float64`, `np.int64`, `np.bool_` 等）必須正確轉換為 JSON 原生型別（`number`, `integer`, `boolean`）。
* **[ ] AC 2.1.4:** 所有合約必須通過 `model → JSON → model` 的往返測試（Round-trip Test）。

### **US 2.2: JSON 報告匯出**

**User Story:** 身為一名資料科學家，我希望能一鍵匯出完整的資料集分析報告為格式化的 JSON 檔案。

* **[ ] AC 2.2.1:** `ReportExporter.export(report, path)` 必須將 `DatasetReport` 寫入指定路徑的 JSON 檔案。
* **[ ] AC 2.2.2:** 匯出的 JSON 必須具備良好的人類可讀性（含縮排，預設 2 格）。
* **[ ] AC 2.2.3:** `ReportExporter.export_schema(path)` 必須能產出對應的 JSON Schema 定義檔。

---

## **Epic 3: 生態系與介面整合 (Adapter: Pandas Integration)**

**目標：提供流暢的使用者體驗，同時保衛核心領域的乾淨度（六角架構防腐層）。**

### **US 3.1: Pandas DataFrame 無縫擴充**

**User Story:** 身為一名習慣使用 Pandas 的分析師，我希望可以直接在 DataFrame 上呼叫 Profiling 函式，而不需要手動把 DataFrame 轉成 NumPy Array。

* **[ ] AC 3.1.1:** 必須成功註冊 Pandas Accessor。使用者可以合法執行 `df.miner.profile()`。
* **[ ] AC 3.1.2:** **架構驗證：** 檢查 `src/ds_data_miner/profiling` 與 `src/ds_data_miner/core` 目錄下的所有程式碼，**絕對不可**出現 `import pandas`。Pandas 的依賴必須完全限縮在 `pandas_ext` 模組中。
* **[ ] AC 3.1.3:** **動態路由驗證：** 轉接層需確保能根據 DataFrame 的欄位型態自動正確派發任務：
    * `numeric` (int64, float64) → `NumericProfiler`
    * `object` / `category` → `CategoricalProfiler`
    * `datetime64` → `DatetimeProfiler`

### **US 3.2: 一站式 JSON 匯出**

**User Story:** 身為一名資料工程師，我希望能直接從 DataFrame 一步完成「掃描全表 + 匯出 JSON」，無需手動串接多個步驟。

* **[ ] AC 3.2.1:** `df.miner.export_json("output.json")` 必須完成全表掃描並匯出格式化 JSON 報告。
* **[ ] AC 3.2.2:** 匯出的 JSON 檔案必須符合 `DatasetReport` 的 JSON Schema 定義。

---

## **Epic 4: 工程品質、交付與部署 (Engineering & Delivery)**

**目標：符合現代化 Python 套件標準，隨時可供團隊透過 Git 進行安裝。**

### **US 4.1: 現代化套件建置與安裝**

**User Story:** 身為一名 DevOps / MLOps 工程師，我希望這個套件採用現代化的打包標準，方便整合進 Docker Image 或 CI/CD 管線中。

* **[ ] AC 4.1.1:** 專案根目錄必須使用 `pyproject.toml`（基於 PEP 621），並且**沒有** `setup.py`。
* **[ ] AC 4.1.2:** 在乾淨的 Python 虛擬環境中，執行 `pip install git+https://[repo_url]` 必須能成功安裝。
* **[ ] AC 4.1.3:** 核心安裝（`pip install .`）僅安裝 `numpy`, `scipy`, `pydantic`。Pandas 為可選依賴（`pip install .[pandas]`）。

### **US 4.2: 型別安全與程式碼檢驗**

**User Story:** 身為團隊的 Tech Lead，我希望套件的程式碼品質受到嚴格管控，確保未來其他工程師接手維護時不會破壞核心邏輯。

* **[ ] AC 4.2.1:** 全專案必須 100% 加上 Type Hints（型別提示）。
* **[ ] AC 4.2.2:** 在 CI 流程中，執行 `mypy --strict src/` 必須達到 0 errors。
* **[ ] AC 4.2.3:** 單元測試覆蓋率（Test Coverage）必須達到 85% 以上，並且包含：
    * 針對 `core` 合約物件的 Property-Based Testing（使用 `hypothesis` 套件）
    * JSON Round-trip Testing
    * 與 `scipy.stats` 的 Baseline 比對測試（`atol=1e-7`）

---

## **結案驗收會議 (Sign-off Meeting) 建議流程：**

> 1. **Demo 階段：** 由開發者展示一份範例腳本，從頭到尾演示：「讀取 Pandas CSV → 呼叫 `df.miner.profile()` 進行全表掃描 → 呼叫 `df.miner.export_json()` 匯出標準化 JSON → 以 JSON Schema 驗證輸出正確性」。
> 2. **JSON 驗收：** 打開匯出的 JSON 檔案，確認：(a) 格式化良好，(b) 不含 NaN/Infinity 字面量，(c) 包含所有欄位的 Profile 與品質指標。
> 3. **Code Review 階段：** 展示 `core` 與 `profiling` 資料夾，證明裡面完全沒有 `import pandas` 或 `import matplotlib`。
> 4. **CI/CD 階段：** 展示 GitHub Actions (或 GitLab CI) 綠燈狀態，證明 `mypy --strict` 與所有測試皆通過。
> 5. **安裝階段：** 現場開一個乾淨的 Terminal，示範透過 `pip install git+...` 安裝並成功 `import ds_data_miner`。

全數打勾後，這套 `ds-data-miner` 即可正式 Release 成為團隊內部的基礎建設套件！