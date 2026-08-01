# **高階系統設計文件 (High-Level Design Document)**

**專案代號：** ds-data-miner
**文件版本：** v3.0
**文件狀態：** Approved for Development

## **1. 系統架構總覽 (Architecture Overview)**

本套件採用六角架構（Hexagonal Architecture）的精神進行模組化設計。核心設計理念為：「數學運算與 I/O 徹底解耦」，且**職責嚴格限縮於探索式資料分析 (EDA) 的計算核心**。

### **1.1 三部曲架構願景**

`ds-data-miner` 是三部曲系統的第一部，負責計算核心。視覺化（`ds-data-miner-vis`）與報告產出（`ds-data-miner-reporter`）將作為獨立套件，透過本套件匯出的標準化 JSON 進行串接。

### **1.2 分層架構**

* **內核層 (Inner Core)：** `core` 模組。定義全域共用的不可變資料結構（Pydantic Models）。依賴限制：僅 `pydantic`。
* **領域層 (Domain Layer)：** `profiling` 模組。實作全量掃描統計運算、資料品質檢驗與統計誤差計算。**依賴限制：僅允許使用 `numpy`、`scipy` 與 Python 內建函式庫。**
* **匯出層 (Export Layer)：** `export` 模組。負責將 Profile 合約序列化為標準化 JSON 檔案，並產出 JSON Schema。依賴限制：`core`。
* **轉接層 (Adapter Layer)：** `pandas_ext` 模組。負責與外部資料容器（Pandas）互動，作為核心層的防腐層（ACL）。依賴限制：`pandas`, `core`, `profiling`。

## **2. 專案實體目錄結構 (Physical Directory Structure)**

團隊在建立 Repo 時，請嚴格遵守以下目錄與模組邊界規劃。任何跨越邊界的 import（例如在 `profiling` 內引入 `pandas`）將在 CI/CD 階段被阻擋。

```
ds-data-miner/
├── pyproject.toml              # 套件依賴與 metadata (PEP 621)
├── src/
│   └── ds_data_miner/
│       ├── __init__.py         # 暴露對外 API (Facade)
│       ├── core/               # 【內核層】
│       │   ├── __init__.py
│       │   ├── contracts.py    # Pydantic Models: DistributionProfile,
│       │   │                   #   CategoricalProfile, DatetimeProfile,
│       │   │                   #   DatasetReport, CategoryStats
│       │   └── exceptions.py   # 自定義例外 (DataQualityError 等)
│       ├── profiling/          # 【領域層：統計與品質檢驗】
│       │   ├── __init__.py
│       │   ├── base.py         # 定義 BaseProfiler (ABC)
│       │   ├── numeric.py      # NumericProfiler: 數值型全量掃描
│       │   ├── categorical.py  # CategoricalProfiler: 類別型 + 高基數防禦
│       │   ├── datetime.py     # DatetimeProfiler: 時序型特徵分析
│       │   ├── engine.py       # ProfilingEngine: 型別路由 + 全表掃描排程
│       │   └── tests.py        # DistributionTester: K-S Test 等檢定實作
│       ├── export/             # 【匯出層：JSON 序列化】
│       │   ├── __init__.py
│       │   ├── serializer.py   # ReportExporter: JSON 匯出 + NaN/Inf 處理
│       │   └── schema.py       # JSON Schema 自動產出
│       └── pandas_ext/         # 【轉接層：Pandas 擴充】
│           ├── __init__.py
│           └── accessor.py     # 註冊 df.miner Accessor
└── tests/                      # 單元測試與整合測試
    ├── test_core/
    ├── test_profiling/
    ├── test_export/
    └── test_adapters/
```

## **3. 核心介面與合約定義 (Core Interfaces & Contracts)**

工程團隊在實作時，必須遵守以下核心類別的 Input/Output 定義。

### **3.1 資料合約 (Data Contracts)**

位於 `core/contracts.py`。使用 **Pydantic v2 BaseModel** 確保不可變性、JSON 序列化與型別強制轉換。

```python
from pydantic import BaseModel, ConfigDict


class CategoryStats(BaseModel):
    """單一類別的統計數據。"""

    model_config = ConfigDict(frozen=True)

    category: str
    count: int
    proportion: float
    std_error: float  # 二項式分佈標準誤: sqrt(p*(1-p)/N)


class DistributionProfile(BaseModel):
    """描述數值型資料統計特徵的合約。"""

    model_config = ConfigDict(frozen=True)

    # 基礎統計量
    mean: float
    variance: float
    std: float
    skewness: float
    kurtosis: float
    median: float
    min: float
    max: float
    q25: float
    q75: float

    # 統計誤差
    sem: float                     # 平均數標準誤 (Standard Error of Mean)
    ci_lower: float                # 信賴區間下界 (預設 95%)
    ci_upper: float                # 信賴區間上界

    # 直方圖（供下游繪圖，不存原始陣列）
    histogram_bin_edges: list[float]
    histogram_counts: list[int]

    # 樣本與品質資訊
    n_samples: int
    n_valid: int
    missing_count: int
    missing_ratio: float
    inf_count: int

    # 分佈檢定（由 DistributionTester 填入，可選）
    distribution_type: str | None = None
    ks_statistic: float | None = None
    ks_p_value: float | None = None


class CategoricalProfile(BaseModel):
    """描述類別型資料統計特徵的合約。"""

    model_config = ConfigDict(frozen=True)

    stats: list[CategoryStats]
    n_total: int
    n_unique: int
    missing_count: int
    missing_ratio: float

    # 高基數防禦
    is_high_cardinality: bool
    truncated_at: int | None = None  # 截斷閾值 (如 Top-100)


class DatetimeProfile(BaseModel):
    """描述時序型資料特徵的合約。"""

    model_config = ConfigDict(frozen=True)

    start: str                     # ISO 8601
    end: str                       # ISO 8601
    duration_seconds: float
    is_monotonic_increasing: bool
    gap_count: int
    gap_locations: list[dict]      # [{"from": ..., "to": ..., "duration_seconds": ...}]
    inferred_freq: str | None

    n_samples: int
    missing_count: int
    missing_ratio: float


class DatasetReport(BaseModel):
    """頂層資料集報告合約，聚合所有欄位的 Profile。"""

    model_config = ConfigDict(frozen=True)

    dataset_name: str
    created_at: str                # ISO 8601
    ds_data_miner_version: str
    total_rows: int
    total_columns: int

    # 全域品質指標
    duplicate_row_count: int
    duplicate_row_ratio: float

    # 各欄位 Profile
    columns: dict[str, DistributionProfile | CategoricalProfile | DatetimeProfile]
```

### **3.2 領域層抽象介面 (Domain Abstract Base Classes)**

位於 `profiling/base.py`。

```python
from abc import ABC, abstractmethod

import numpy as np
from pydantic import BaseModel


class BaseProfiler(ABC):
    @abstractmethod
    def fit(self, data: np.ndarray) -> BaseModel:
        """
        架構強制規定：
        必須在本地 Python Runtime 中，針對傳入的 NumPy Array 進行「全量掃描」。
        嚴禁在內部實作預設抽樣邏輯，以保證 Data Quality Check 的絕對精準度。
        所有運算必須使用向量化操作，嚴禁 Python 原生 for 迴圈。
        """
        pass
```

## **4. 關鍵資料流向 (Data Flow / Sequence)**

以下是標準使用情境下，物件在各層級間的流轉順序，開發者需確保資料轉換的正確性：

> 1. **[Adapter In]** 使用者呼叫 `df.miner.profile()` 或 `df.miner.export_json(path)`。
> 2. **[Adapter In]** `pandas_ext` 將 `pandas.Series` 提取為底層純淨的 `numpy.ndarray`，並過濾掉 Pandas 特有的 metadata。
> 3. **[Domain: Routing]** 轉接層依據欄位 dtype 進行型別路由：
>    * `numeric` → `NumericProfiler.fit()`
>    * `object` / `category` → `CategoricalProfiler.fit()`
>    * `datetime64` → `DatetimeProfiler.fit()`
> 4. **[Domain: Profiling]** 各 Profiler 在本地記憶體中進行全量掃描，計算統計特徵、資料品質指標與統計誤差。
> 5. **[Core]** Profiler 產出對應的 Pydantic Profile 物件（`DistributionProfile` / `CategoricalProfile` / `DatetimeProfile`）。
> 6. **[Domain: Aggregation]** `ProfilingEngine` 聚合所有欄位的 Profile，加上全域品質指標（重複列偵測），封裝為 `DatasetReport`。
> 7. **[Export]** `ReportExporter` 將 `DatasetReport` 序列化為格式化 JSON 檔案，處理 NaN → null 等特殊轉換。

## **5. 工程實踐與開發規範 (Engineering Standards)**

為確保作為底層演算法套件的品質與效能，團隊需遵守以下技術決策：

### **5.1 效能與數值穩定性 (Performance & Stability)**

* **拒絕迴圈：** 在 `profiling` 模組中，處理 Array 等級的資料時，嚴禁使用 Python 原生的 `for` 迴圈。必須使用 NumPy 的向量化（Vectorization）操作（例如 `np.nanmean`, `np.nanstd`, `np.histogram`）。
* **極端值防禦：** 所有數學運算前，必須對 NaN 與 Inf 進行檢測。若偵測到異常且使用者未指定容錯策略，需拋出明確的自定義例外（如 `DataQualityError`）。
* **高基數防禦：** `CategoricalProfiler` 必須在計算前偵測 unique 值數量，若超過閾值則自動截斷並發出 `HighCardinalityWarning`，避免全量掃描高基數欄位時造成記憶體溢出。

### **5.2 測試策略 (Testing Strategy)**

* **Baseline 比對測試：** 在 CI 流程中，`profiling` 的計算結果必須與 `scipy.stats` 或 `statsmodels` 進行 Assertion，浮點數容差設定為 `atol=1e-7`。
* **Property-Based Testing：** 使用 `hypothesis` 套件自動生成各種形狀、帶有極端值的 NumPy Array，暴力測試套件是否會 Crash。
* **JSON Round-trip Testing：** 所有合約物件必須通過 `model → JSON → model` 的往返測試。

### **5.3 套件管理與發布 (Packaging)**

* 放棄 `setup.py` 與 `requirements.txt`。
* 使用 **Poetry** 或 **uv** 管理 `pyproject.toml`。
* 核心依賴：`numpy`, `scipy`, `pydantic`。
* 可選依賴：`pandas = ["pandas>=1.3.0"]`（供 `pandas_ext` 轉接層使用）。
* 開發依賴：`pytest`, `mypy`, `hypothesis`, `ruff`。

**核准人 (Tech Lead)：** [等待簽核]
**下一步：** 請工程團隊根據此 HLD，優先建立 `pyproject.toml` 與 `core` 模組的 Pydantic 資料合約，並發起第一個 Pull Request 進行架構 Review。