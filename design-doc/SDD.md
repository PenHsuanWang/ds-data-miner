# **軟體設計文件 (Software Design Document - SDD)**
**專案名稱：** ds-data-miner（探索式資料分析與統計診斷核心引擎）  
**文件版本：** v4.0  
**設計原則：** 領域驅動設計 (DDD)、六角架構 (Hexagonal Architecture)、SOLID、Evidence-driven Statistical Diagnostics
---
# **1. 系統架構設計 (System Architecture Design)**
## **1.1 架構總覽**
ds-data-miner 是一個面向資料科學與製造資料分析場景的探索式資料分析與統計診斷核心引擎。
系統不僅提供傳統的 Data Profiling、Distribution Testing 與 Uncertainty Propagation，亦提供具備證據追蹤能力的 **Bivariate Diagnostic Engine**，用於根據資料型態、樣本結構、分佈特徵、變異數、缺失值、離群值、樣本相依性與時間相依性，推薦適當的統計效應量或關聯性指標。
系統的核心設計原則為：
> **The system provides statistical evidence and recommendations, not absolute truth.**
因此，統計診斷引擎不得僅根據單一統計檢定結果武斷選擇演算法，而必須：
1. 探索資料結構。
2. 收集統計證據。
3. 評估證據可靠程度。
4. 檢查樣本獨立性與時間相依性。
5. 評估資料品質與樣本平衡性。
6. 根據策略規則推薦統計指標。
7. 保存完整 Decision Trace。
8. 在證據不足時明確回傳 Warning / Insufficient Evidence。
整體採用六角架構（Ports and Adapters）。
核心 Domain Layer 不得依賴 Pandas、Matplotlib 或其他外部資料容器。
---
## **1.2 架構分層**
系統分為以下主要層級：
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
│                       Domain Layer                           │
│                                                             │
│  Profilers                                                  │
│  Statistical Tests                                          │
│  Evidence Collectors                                        │
│  MetricSelector                                             │
│  Strategy Registry                                          │
│  Effect Size Calculators                                    │
│  Dependency Diagnostics                                     │
│  Correlation Engine                                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       Core Contracts                         │
│                                                             │
│  DistributionProfile                                        │
│  DiagnosticEvidence                                         │
│  HypothesisTestResult                                       │
│  DynamicEffectSize                                          │
│  CorrelationResult                                          │
│  DecisionTrace                                              │
│  DatasetReport                                              │
└─────────────────────────────────────────────────────────────┘

⸻

1.3 依賴流向 (Dependency Flow)

依賴反轉原則（DIP）必須嚴格遵守。

pandas_ext
    │
    ├──────────────► core
    │
    └──────────────► application
                           │
                           ▼
                         domain
                           │
                           ▼
                         core
export ───────────────────► core

依賴規則：

* pandas_ext ➡️ 依賴 application / domain / core
* export ➡️ 依賴 core
* application ➡️ 依賴 domain / core
* domain ➡️ 依賴 core
* core ➡️ 不得依賴 Pandas / Matplotlib
* core ➡️ 不得依賴任何外部資料容器
* core 不得 import pandas
* core 不得 import matplotlib

⸻

1.4 Package Architecture

建議專案結構：

src/
└── ds_data_miner/
    │
    ├── core/
    │   ├── contracts.py
    │   ├── enums.py
    │   ├── exceptions.py
    │   └── types.py
    │
    ├── profiling/
    │   ├── base.py
    │   ├── numeric.py
    │   ├── categorical.py
    │   ├── datetime.py
    │   ├── distribution.py
    │   └── engine.py
    │
    ├── diagnostics/
    │   ├── engine.py
    │   │
    │   ├── evidence/
    │   │   ├── collector.py
    │   │   ├── normality.py
    │   │   ├── variance.py
    │   │   ├── outlier.py
    │   │   ├── dependency.py
    │   │   └── balance.py
    │   │
    │   ├── metrics/
    │   │   ├── base.py
    │   │   ├── cohens_d.py
    │   │   ├── hedges_g.py
    │   │   ├── glass_delta.py
    │   │   ├── cliffs_delta.py
    │   │   └── registry.py
    │   │
    │   ├── correlation/
    │   │   ├── pearson.py
    │   │   ├── multiple_testing.py
    │   │   └── engine.py
    │   │
    │   └── selection/
    │       ├── selector.py
    │       └── rules.py
    │
    ├── uncertainty/
    │   ├── analytical.py
    │   └── monte_carlo.py
    │
    ├── pandas_ext/
    │   └── accessor.py
    │
    ├── export/
    │   └── serializer.py
    │
    └── viz/
        └── uncertainty.py

⸻

2. 核心資料合約設計 (Core Data Contracts Design)

所有跨模組資料交換均必須透過 Core Contracts。

所有 Contract：

* 必須為 immutable。
* 使用 Pydantic v2 BaseModel。
* 必須設定 frozen=True。
* 不得保存原始大型 NumPy Array。
* 必須可序列化為 JSON。
* 必須明確描述 statistical semantics。
* 不得將 p_value == 0.0 解讀為數學上的真正零機率。

⸻

2.1 Base Contract

from typing import Any
from pydantic import BaseModel, ConfigDict
class ProfileBaseModel(BaseModel):
    """所有核心資料合約的基礎類別。"""
    model_config = ConfigDict(
        frozen=True,
        ser_json_inf_nan="null",
    )

⸻

2.2 Evidence Level

統計診斷結果必須具有 Evidence Level。

from enum import Enum
class EvidenceLevel(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INSUFFICIENT = "insufficient"

Evidence Level 不代表統計假設「為真」，而代表目前資料對該判斷所提供的證據強度。

⸻

2.3 Data Type

class VariableType(str, Enum):
    CONTINUOUS = "continuous"
    CATEGORICAL = "categorical"
    DATETIME = "datetime"

⸻

2.4 Sample Structure

class SampleStructure(str, Enum):
    INDEPENDENT = "independent"
    PAIRED = "paired"
    REPEATED_MEASURES = "repeated_measurements"
    TIME_SERIES = "time_series"
    UNKNOWN = "unknown"

⸻

2.5 Missing Data Strategy

雙變數分析必須明確指定 Missing Data Policy。

class MissingDataStrategy(str, Enum):
    PAIRWISE_COMPLETE = "pairwise_complete"
    LISTWISE_COMPLETE = "listwise_complete"
    ERROR = "error"

MVP 預設：

PAIRWISE_COMPLETE

對於 Pearson correlation，每一個 feature pair 必須建立自己的 Boolean Mask。

禁止直接將包含 NaN 的原始矩陣傳入相關係數計算器。

⸻

2.6 HypothesisTestResult

class HypothesisTestResult(ProfileBaseModel):
    """統計假設檢定結果。"""
    test_name: str
    statistic: float | None
    p_value: float | None
    alpha: float
    reject_null: bool | None
    evidence_level: EvidenceLevel
    n_samples: int
    p_value_is_underflowed: bool = False
    p_value_display: str | None = None

P-value Underflow Policy

當統計套件因浮點數限制將極小的 p-value 回傳為：

0.0

系統不得將其解讀為：

p = 0

而應標記：

p_value_is_underflowed = true

並提供：

p_value_display = "< 1e-300"

或其他符合實際數值穩定性限制的表示。

⸻

2.7 DependencyEvidence

用於防禦 Pseudo-replication 與 Repeated Measurements。

class DependencyEvidence(ProfileBaseModel):
    """樣本獨立性與相依性診斷證據。"""
    sample_structure: SampleStructure
    dependency_detected: bool
    dependency_warning: bool
    grouping_columns: list[str]
    repeated_group_count: int
    max_observations_per_group: int
    autocorrelation_detected: bool
    autocorrelation_lag_1: float | None = None
    evidence_level: EvidenceLevel
    message: str

系統必須能識別下列常見 grouping keys：

Lot
Wafer
Chamber
Tool
Recipe
Batch
Timestamp

當同一個 Lot / Wafer / Chamber 包含多筆測量值時，不得直接視為完全獨立觀測值。

⸻

2.8 GroupBalanceEvidence

用於防禦嚴重不平衡的 A/B 組。

class GroupBalanceEvidence(ProfileBaseModel):
    """比較兩組樣本量平衡性的證據。"""
    reference_n: int
    target_n: int
    group_size_ratio: float
    is_imbalanced: bool
    warning_threshold: float = 10.0
    evidence_level: EvidenceLevel
    message: str

當：

max(n_a, n_b) / min(n_a, n_b) > 10

時，必須標記：

is_imbalanced = true

並產生：

ImbalancedSampleWarning

⸻

2.9 DiagnosticEvidence

class DiagnosticEvidence(ProfileBaseModel):
    """Bivariate Diagnostic Engine 的完整證據集合。"""
    data_type: VariableType
    sample_structure: SampleStructure
    sample_sizes: dict[str, int]
    group_size_ratio: float | None
    n_valid_pairs: int
    missing_data_strategy: MissingDataStrategy
    missing_count: int
    missing_ratio: float
    normality_evidence: dict[str, HypothesisTestResult] | None
    variance_evidence: HypothesisTestResult | None
    outlier_evidence: dict[str, bool]
    dependency_evidence: DependencyEvidence
    group_balance: GroupBalanceEvidence | None
    multiple_testing_evidence: HypothesisTestResult | None
    evidence_level: EvidenceLevel
    warnings: list[str]

⸻

2.10 DecisionTrace

Decision Trace 必須保存 Metric Selector 的決策依據。

class DecisionTrace(ProfileBaseModel):
    """統計指標選擇過程的可追溯決策軌跡。"""
    steps: list[str]
    assumptions_checked: list[str]
    assumptions_supported: list[str]
    assumptions_not_supported: list[str]
    warnings: list[str]
    final_reason: str

例如：

[
    "Variable X is continuous",
    "Variable Y is continuous",
    "Sample structure classified as independent",
    "Normality evidence is insufficient to reject normality",
    "Variance homogeneity rejected",
    "Reference group standard deviation is stable",
    "No dependency evidence detected",
    "Glass's Delta selected"
]

⸻

2.11 DynamicEffectSize

class DynamicEffectSize(ProfileBaseModel):
    """動態選擇後的效應量結果。"""
    metric: str
    estimate: float | None
    standard_error: float | None
    confidence_interval: tuple[float | None, float | None] | None
    sample_sizes: dict[str, int]
    diagnostic_evidence: DiagnosticEvidence
    decision_trace: DecisionTrace
    status: str
    warnings: list[str]

⸻

2.12 CorrelationResult

class CorrelationResult(ProfileBaseModel):
    """相關係數結果。"""
    method: str
    feature_names: list[str]
    correlation_matrix: list[list[float | None]] | None
    sparse_pairs: list[dict[str, str | float | None]] | None
    sample_size: int
    sample_size_matrix: list[list[int]] | None
    missing_data_strategy: MissingDataStrategy
    raw_p_values: list[list[float | None]] | None
    adjusted_p_values: list[list[float | None]] | None
    multiple_testing_method: str | None
    threshold: float | None
    warnings: list[str]

⸻

2.13 High-dimensional Correlation Policy

Correlation Matrix 屬於 $O(p^2)$ 資料結構。

例如：

p = 1,000

將產生：

1,000 × 1,000 = 1,000,000

個 correlation values。

因此：

* 不得無條件將大型 correlation matrix 放入 DatasetReport。
* 必須設定 feature dimension guard。
* 超過 threshold 時，必須啟動 high-dimensional policy。
* 支援 sparsification。
* 可以只保留：

|r| >= threshold

的 feature pairs。

例如：

CorrelationResult(
    sparsified=True,
    sparsification_threshold=0.3,
)

⸻

3. Existing Profiling Domain

3.1 NumericProfiler

維持既有 Full Scan 設計。

class NumericProfiler(BaseProfiler):
    def __init__(
        self,
        ignore_nan: bool = True,
        ci_level: float = 0.95,
        n_bins: int | str = "auto",
    ) -> None:
        self.ignore_nan = ignore_nan
        self.ci_level = ci_level
        self.n_bins = n_bins
    def fit(self, data: np.ndarray) -> DistributionProfile:
        ...

必要條件：

* 完整掃描。
* 禁止 sampling。
* NumPy vectorization。
* 不得保存原始 array。
* NaN / Inf 必須被明確處理。
* 全為 invalid values 時必須拋出 DataQualityError。

⸻

3.2 CategoricalProfiler

維持既有高基數防禦。

class CategoricalProfiler(BaseProfiler):
    def __init__(
        self,
        max_cardinality: int = 100,
    ) -> None:
        self.max_cardinality = max_cardinality
    def fit(self, data: np.ndarray) -> CategoricalProfile:
        ...

⸻

3.3 DatetimeProfiler

維持既有時序 Profiling，但必須增加：

autocorrelation risk
sampling frequency
time-series resolution

供 Bivariate Diagnostic Engine 判斷時間相依性。

⸻

3.4 DistributionTester

DistributionTester 必須回傳標準化的 HypothesisTestResult，而不是裸 dict。

class DistributionTester:
    def __init__(
        self,
        dist_name: str = "norm",
        alpha: float = 0.05,
    ) -> None:
        self.dist_name = dist_name
        self.alpha = alpha
    def test(
        self,
        data: np.ndarray,
    ) -> HypothesisTestResult:
        ...

統計語義：

禁止：

Normality = True
Data is normally distributed

允許：

Insufficient evidence to reject the normality assumption.

⸻

4. Bivariate Diagnostic Engine

4.1 Design Goal

BivariateDiagnosticEngine 是 v4.0 的核心新增模組。

其目的不是強制選擇單一統計方法，而是：

Input Data
    │
    ▼
Data Type Detection
    │
    ▼
Sample Structure Detection
    │
    ▼
Data Quality Assessment
    │
    ├── Missing Data
    ├── Outlier
    ├── Group Balance
    ├── Dependency
    └── Temporal Dependency
    │
    ▼
Statistical Evidence Collection
    │
    ├── Normality
    ├── Variance
    └── Dependency
    │
    ▼
MetricSelector
    │
    ▼
Strategy Registry
    │
    ▼
Recommended Metric
    │
    ▼
DynamicEffectSize

核心原則：

Evidence first, strategy second.

⸻

4.2 BivariateDiagnosticEngine

class BivariateDiagnosticEngine:
    """雙變數統計自動診斷引擎。"""
    def __init__(
        self,
        evidence_collector: EvidenceCollector,
        metric_selector: MetricSelector,
    ) -> None:
        self.evidence_collector = evidence_collector
        self.metric_selector = metric_selector
    def diagnose(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        variable_x_type: VariableType | None = None,
        variable_y_type: VariableType | None = None,
        grouping_columns: dict[str, np.ndarray] | None = None,
        timestamps: np.ndarray | None = None,
        missing_data_strategy: MissingDataStrategy = (
            MissingDataStrategy.PAIRWISE_COMPLETE
        ),
    ) -> DynamicEffectSize:
        ...

⸻

4.3 Data Type Detection

系統必須在診斷開始前辨識：

Continuous
Categorical
Datetime

Data Type Detection 必須是獨立策略。

class VariableTypeDetector:
    def detect(
        self,
        data: np.ndarray,
    ) -> VariableType:
        ...

⸻

4.4 Sample Structure Detection

class SampleStructureDetector:
    def detect(
        self,
        *,
        grouping_columns: dict[str, np.ndarray] | None,
        timestamps: np.ndarray | None,
    ) -> SampleStructure:
        ...

判斷優先順序：

Repeated Measurements
        ↓
Paired
        ↓
Time Series
        ↓
Independent
        ↓
Unknown

當無法證明獨立性時：

SampleStructure.UNKNOWN

不得默認為：

INDEPENDENT

⸻

5. Evidence Collection

5.1 EvidenceCollector

class EvidenceCollector:
    """收集 Bivariate Diagnostic 所需的統計證據。"""
    def collect(
        self,
        x: np.ndarray,
        y: np.ndarray,
        *,
        grouping_columns: dict[str, np.ndarray] | None = None,
        timestamps: np.ndarray | None = None,
        missing_data_strategy: MissingDataStrategy,
    ) -> DiagnosticEvidence:
        ...

EvidenceCollector 必須收集：

Data Type
Sample Structure
Sample Size
Normality
Variance
Outlier
Dependency
Group Balance
Missing Data
Temporal Dependency

⸻

5.2 Normality Evidence

Normality 檢定結果不得被解讀為「證明常態」。

例如：

p > α

只能產生：

Insufficient evidence against normality.

而不能產生：

Normality = True

⸻

5.3 Variance Evidence

MVP 使用：

Brown-Forsythe / median-centered Levene

作為兩組變異數差異診斷。

若：

p <= alpha

則：

Evidence of unequal variance

若：

p > alpha

則：

Insufficient evidence to reject equal variance

⸻

5.4 Dependency Evidence

系統必須主動檢查：

Lot
Wafer
Chamber
Tool
Batch
Recipe
Timestamp

是否造成：

Repeated Measurements
Pseudo-replication
Temporal Dependency

若存在 dependency：

dependency_warning = true

系統不得直接使用假設完全獨立的統計方法。

⸻

5.5 Time-series Autocorrelation

若資料仍維持：

Timestamp-level resolution

而未經：

Lot-level aggregation
Wafer-level aggregation
Batch-level aggregation

則 Bivariate Diagnostic Engine 必須：

Warning

或：

Block

直接 effect-size calculation。

系統不得將：

t1
t2
t3
t4
...

直接視為：

Independent Samples

⸻

6. Group Imbalance Detection

A/B comparison 必須檢查：

n_control
n_target

並計算：

group_size_ratio =
max(n_control, n_target)
/
min(n_control, n_target)

當：

ratio > 10

系統必須產生：

ImbalancedSampleWarning

在此情況下：

* 不得僅依賴 Levene / Brown-Forsythe 決定推薦結果。
* 必須降低 Evidence Level。
* MetricSelector 應傾向穩健方法。
* Cliff’s Delta 可以列入推薦清單。

⸻

7. Effect Size Strategy Registry

7.1 設計目的

MetricSelector 不應將統計方法寫死在：

if / elif / else

中。

使用 Strategy Registry。

class EffectSizeStrategy(ABC):
    @abstractmethod
    def calculate(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> float:
        ...

⸻

7.2 Metric Registry

class MetricRegistry:
    """Effect Size Strategy Registry。"""
    def register(
        self,
        name: str,
        strategy: EffectSizeStrategy,
    ) -> None:
        ...
    def get(
        self,
        name: str,
    ) -> EffectSizeStrategy:
        ...

⸻

7.3 MVP Supported Metrics

MVP 支援：

Cohen's d
Hedges' g
Glass's Δ
Cliff's δ
Pearson's r

⸻

7.4 Cohen’s d

適用條件：

Continuous vs Continuous
Independent samples
Approximately normal
No strong evidence of unequal variance

若樣本極度不平衡或存在強烈 outlier，不應自動優先選擇 Cohen’s d。

⸻

7.5 Glass’s Delta

若：

Continuous
Independent
Unequal variance
Reference / Control SD is stable

MetricSelector 優先推薦：

Glass's Δ

公式：

Δ =
(mean_target - mean_reference)
/
SD_reference

若：

SD_reference == 0

必須：

MetricCalculationError

不得產生：

inf
NaN

⸻

7.6 Cliff’s Delta

當資料：

Severely skewed
Outlier contaminated
Non-normal
Strongly imbalanced

且缺乏足夠證據支持 parametric assumptions 時：

Cliff's δ

應列為優先候選。

⸻

8. MetricSelector

class MetricSelector:
    def select(
        self,
        evidence: DiagnosticEvidence,
        registry: MetricRegistry,
    ) -> DynamicEffectSize:
        ...

決策邏輯：

                    ┌─ Dependency detected ──► Warning / Block
                    │
Input ─► Evidence ──┼─ Time-series dependency ─► Warning / Block
                    │
                    ├─ Severe imbalance ─► Robust metric
                    │
                    ├─ Non-normal + outliers ─► Cliff's Delta
                    │
                    ├─ Unequal variance + stable reference SD
                    │                       └─► Glass's Delta
                    │
                    └─ Normal + independent + stable variance
                                            └─► Cohen's d

⸻

9. Decision Trace

每一次推薦都必須記錄：

1. Variable Type
2. Sample Structure
3. Sample Size
4. Missing Data Strategy
5. Normality Evidence
6. Variance Evidence
7. Outlier Evidence
8. Dependency Evidence
9. Group Balance
10. Selected Metric
11. Rejected Alternatives
12. Final Reason

範例：

Variable X: continuous
Variable Y: continuous
Sample structure:
independent
Normality:
insufficient evidence against normality
Variance:
evidence of unequal variance
Group balance:
8.4:1
Dependency:
no dependency evidence detected
Reference SD:
stable
Selected metric:
Glass's Delta
Reason:
Unequal variance with stable reference-group
standard deviation supports Glass's Delta.

⸻

10. Correlation Engine

10.1 API

Pandas Adapter 提供：

df.trust.correlation(method="pearson")

Domain API：

class CorrelationEngine:
    def calculate(
        self,
        data: np.ndarray,
        feature_names: list[str],
        *,
        method: str = "pearson",
        missing_data_strategy: MissingDataStrategy = (
            MissingDataStrategy.PAIRWISE_COMPLETE
        ),
        multiple_testing_method: str | None = "fdr_bh",
    ) -> CorrelationResult:
        ...

⸻

10.2 Pearson MVP

MVP 支援：

Pearson's r

Architecture 必須預留：

Spearman's rho
Kendall's tau

未來版本可擴充：

Mutual Information
Distance Correlation

⸻

10.3 Non-linear Dependency Extension

Pearson / Spearman / Kendall 皆不足以完整捕捉任意非線性關係。

例如：

Y = X²

可能得到：

Pearson r ≈ 0

因此架構上必須保留：

class DependencyMetricStrategy(ABC):
    @abstractmethod
    def calculate(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> float:
        ...

未來可實作：

MutualInformationStrategy
DistanceCorrelationStrategy

MVP 不要求實作，但不得破壞 Registry Architecture。

⸻

11. Missing Data Handling

Correlation Engine 必須使用 Boolean Mask。

例如：

mask = np.isfinite(x) & np.isfinite(y)
x_valid = x[mask]
y_valid = y[mask]

禁止：

np.corrcoef(raw_matrix)

直接處理包含 NaN 的矩陣。

每一個 feature pair 必須明確知道：

n_valid_pairs
missing_count
missing_data_strategy

⸻

12. Multiple Testing Correction

Feature Screening 可能產生大量 pairwise hypothesis tests。

例如：

p = 500

pair count：

500 × 499 / 2
= 124,750

若直接使用：

alpha = 0.05

將產生嚴重 False Positive risk。

因此 Correlation Engine 必須支援 Multiple Testing Correction。

MVP：

Benjamini-Hochberg FDR

架構預留：

Bonferroni
Holm

⸻

12.1 MultipleTestingStrategy

class MultipleTestingStrategy(ABC):
    @abstractmethod
    def adjust(
        self,
        p_values: np.ndarray,
        alpha: float,
    ) -> np.ndarray:
        ...

Registry：

class MultipleTestingRegistry:
    ...

⸻

13. High Dimensionality Guard

Correlation Matrix 的 memory complexity：

O(p²)

系統必須設定：

DEFAULT_MAX_CORRELATION_FEATURES = 500

超過 threshold：

HighDimensionalityWarning

系統可採用：

Sparse Correlation Mode

只保存：

|r| >= threshold

例如：

correlation(
    method="pearson",
    sparsify=True,
    threshold=0.3,
)

⸻

13.1 Sparse Correlation Contract

大型資料集不得將完整：

p × p

matrix 無條件序列化進：

DatasetReport

Sparse mode 可使用：

class CorrelationPair(ProfileBaseModel):
    feature_x: str
    feature_y: str
    correlation: float
    p_value: float | None
    corrected_p_value: float | None
    n_valid: int

結果：

class SparseCorrelationResult(ProfileBaseModel):
    pairs: list[CorrelationPair]
    threshold: float
    n_features: int
    total_possible_pairs: int
    retained_pairs: int

⸻

14. DatasetReport Integration

DatasetReport 維持作為 Data Profiling 的頂層容器。

但 Bivariate Diagnostic 不應無條件塞入 DatasetReport。

推薦設計：

DatasetReport
    │
    ├── columns
    │
    ├── global_quality
    │
    └── optional diagnostics metadata

大型 Diagnostic Result 應獨立產生：

DiagnosticReport
CorrelationResult
DynamicEffectSize

避免：

DatasetReport
    └── 1,000 × 1,000 correlation matrix

造成：

JSON payload explosion

⸻

15. DiagnosticReport

class DiagnosticReport(ProfileBaseModel):
    created_at: str
    engine_version: str
    diagnostics: list[DynamicEffectSize]
    warnings: list[str]
    evidence_level: EvidenceLevel

Diagnostic Report 必須保持：

Evidence
Decision
Result
Warning

四個概念分離。

⸻

16. Exception Handling

新增例外：

class DataMinerBaseException(Exception):
    """所有自定義例外的基礎類別。"""
class DataQualityError(DataMinerBaseException):
    """資料品質不足。"""
class ShapeMismatchError(DataMinerBaseException):
    """資料維度不匹配。"""
class NumericalInstabilityError(DataMinerBaseException):
    """數值運算發生不穩定。"""
class MetricCalculationError(DataMinerBaseException):
    """效應量無法計算。"""
class InsufficientEvidenceError(DataMinerBaseException):
    """證據不足以支援統計推薦。"""
class DependencyDetectedError(DataMinerBaseException):
    """偵測到樣本相依性。"""
class HighDimensionalityError(DataMinerBaseException):
    """資料維度超過允許範圍。"""

Warnings：

class DataQualityWarning(UserWarning):
    pass
class DependencyWarning(UserWarning):
    pass
class ImbalancedSampleWarning(UserWarning):
    pass
class TemporalDependencyWarning(UserWarning):
    pass
class HighDimensionalityWarning(UserWarning):
    pass
class HighCardinalityWarning(UserWarning):
    pass

⸻

17. Defensive Numerical Operations

17.1 Zero Variance

任何需要：

division by SD

的統計量都必須先檢查：

if std == 0:
    raise MetricCalculationError(...)

禁止輸出：

inf
NaN

作為正常 effect size 結果。

⸻

17.2 P-value Underflow

系統必須避免將：

0.0

視為：

exact zero probability

應保存：

p_value_is_underflowed=True

並提供 human-readable representation。

⸻

17.3 Numerical Stability

統計運算必須優先使用：

SciPy
NumPy

提供的 numerical stable implementation。

不得自行重新實作已存在且經驗證的基礎統計演算法，除非有明確效能或架構需求。

⸻

18. Pandas Adapter

18.1 MinerAccessor

@pd.api.extensions.register_dataframe_accessor("trust")
class TrustAccessor:
    def __init__(self, pandas_obj: pd.DataFrame) -> None:
        self._obj = pandas_obj
    def profile(
        self,
    ) -> DatasetReport:
        ...
    def correlation(
        self,
        method: str = "pearson",
        missing_data_strategy: str = "pairwise_complete",
        multiple_testing_method: str | None = "fdr_bh",
    ) -> CorrelationResult:
        ...
    def diagnose(
        self,
        x: str,
        y: str,
        *,
        grouping_columns: list[str] | None = None,
        timestamp_column: str | None = None,
    ) -> DynamicEffectSize:
        ...

⸻

18.2 Adapter Boundary

Pandas Adapter 負責：

DataFrame
    ↓
NumPy Arrays
    ↓
Domain API

Domain Layer 不得接收：

pd.DataFrame
pd.Series

⸻

19. JSON Export

所有 Contract 必須可以：

model_dump(mode="json")

但：

Large Correlation Matrix

不得被默認寫入大型 DatasetReport。

Exporter 必須支援：

DatasetReport
DiagnosticReport
CorrelationResult
DynamicEffectSize

獨立輸出。

⸻

20. Visualization Adapter

Matplotlib 僅允許存在於：

viz/

或其他明確的 Adapter Layer。

Core / Domain：

不得 import matplotlib

提供：

viz.plot_uncertainty_trend(
    ax,
    x_data,
    y_uarray,
)

⸻

21. Performance Requirements

21.1 Profiling

對：

1,000,000 Float64

NumericProfiler：

* 必須 full scan。
* 禁止 sampling。
* 使用 vectorized operations。
* 禁止 list(data)。
* 禁止 deepcopy(data)。

⸻

21.2 Correlation

Correlation：

O(p²)

因此：

* 必須使用 NumPy vectorization。
* 禁止 Python nested loops 執行 numerical calculation。
* 必須有 high-dimensionality guard。
* 必須支援 sparsification。
* 不得保存原始 dataset。

⸻

21.3 Memory Budget

系統不得因建立：

p × p

大型矩陣而無限制增加 memory footprint。

當：

p > max_features

必須：

Warning

或：

Sparse Mode

⸻

22. Testing Strategy

測試分成：

Unit Test
Integration Test
Statistical Validation Test
Property-Based Test
Performance Test
Architecture Test

⸻

22.1 Statistical Validation

Effect Size：

Cohen's d
Glass's Delta
Cliff's Delta

必須與可信賴的 reference implementation 比較。

允許誤差：

atol <= 1e-7

依實際演算法數值穩定性調整。

⸻

22.2 Diagnostic Decision Tests

必須測試：

Normal + Equal Variance
    → Cohen's d
Normal + Unequal Variance
    → Glass's Delta
Non-normal + Outliers
    → Cliff's Delta
Repeated Measurements
    → Dependency Warning
Timestamp-level FDC
    → Temporal Dependency Warning
10:1+ Group Imbalance
    → ImbalancedSampleWarning
Insufficient Evidence
    → No forced recommendation

⸻

22.3 Correlation Tests

必須測試：

Pearson
NaN
Inf
Pairwise Complete
Listwise Complete
Constant Feature
High Dimensionality
Sparse Mode
Multiple Testing
FDR

⸻

22.4 Non-linear Dependency Tests

建立：

Y = X²

資料集。

驗證：

Pearson r ≈ 0

並確認 architecture 可以未來加入：

Mutual Information
Distance Correlation

而不需要修改既有 Correlation Engine Contract。

⸻

22.5 Dependency Tests

建立：

Lot A → 100 measurements
Lot B → 100 measurements
Lot C → 100 measurements

驗證系統：

不得視為 300 個獨立 samples

必須產生：

DependencyWarning

⸻

22.6 P-value Underflow Tests

建立極大樣本：

n >> 100,000

驗證：

p_value == 0.0

時：

p_value_is_underflowed == True

且：

p_value_display

不應宣稱：

p = 0

⸻

22.7 Architecture Tests

CI 必須檢查：

core/
    ❌ pandas
    ❌ matplotlib
domain/
    ❌ pandas
    ❌ matplotlib

Pandas 僅允許存在：

pandas_ext/

Matplotlib 僅允許存在：

viz/

⸻

23. Development & Deployment

23.1 pyproject.toml

[project]
name = "ds-data-miner"
version = "0.2.0"
description = "EDA profiling and evidence-driven statistical diagnostic engine."
requires-python = ">=3.10"
dependencies = [
    "numpy>=1.21.0",
    "scipy>=1.7.0",
    "pydantic>=2.0.0",
]
[project.optional-dependencies]
pandas = [
    "pandas>=1.3.0",
]
viz = [
    "matplotlib>=3.5.0",
]
dev = [
    "pytest>=7.0.0",
    "mypy>=1.0",
    "hypothesis>=6.0",
    "ruff>=0.1.0",
]
[tool.mypy]
strict = true
ignore_missing_imports = true

⸻

24. CI Quality Gate

CI 必須執行：

ruff
mypy --strict
pytest
coverage
architecture dependency checks

Acceptance：

mypy --strict src/
    → 0 errors
Test Coverage
    → >= 85%
Core Contract Property-Based Testing
    → Required
Architecture Dependency Test
    → Passed

⸻

25. Observability & Auditability

Bivariate Diagnostic Engine 的每一次推薦必須具有可追溯性。

至少記錄：

engine_version
created_at
input sample size
variable types
sample structure
missing data strategy
normality evidence
variance evidence
dependency evidence
group balance
selected metric
decision trace
warnings
evidence level

系統不得只記錄：

metric = "glass_delta"
value = 0.73

而必須能回答：

Why was Glass's Delta selected?
What evidence supported the decision?
What assumptions were checked?
What warnings existed?
What evidence was insufficient?

⸻

26. Statistical Semantic Rules

系統所有 UI、Log、JSON metadata 與 Exception message 必須遵守統計語義。

禁止：

p > alpha → H0 is true
p > alpha → Data is normally distributed
p > alpha → Equal variance = True
p < alpha → Alternative hypothesis is proven
Correlation = causation

應使用：

Insufficient evidence to reject H0.
Insufficient evidence against the normality assumption.
Insufficient evidence to reject equal variance.
Evidence against H0.
Observed association does not imply causation.

⸻

27. Evidence-driven Decision Policy

所有自動推薦必須遵循：

Data
 ↓
Evidence
 ↓
Evidence Quality
 ↓
Dependency Check
 ↓
Balance Check
 ↓
Statistical Assumptions
 ↓
Metric Strategy
 ↓
Recommendation

不得：

Data
 ↓
Hard-coded Metric

⸻

28. MVP Scope

v4.0 MVP 必須完成：

Profiling

NumericProfiler
CategoricalProfiler
DatetimeProfiler
DistributionTester
ProfilingEngine

Uncertainty

AnalyticalPropagator
MonteCarloPropagator

Bivariate Diagnostics

Variable Type Detection
Sample Structure Detection
Normality Evidence
Variance Evidence
Outlier Evidence
Dependency Evidence
Group Balance Evidence

Effect Size

Cohen's d
Hedges' g
Glass's Delta
Cliff's Delta

Correlation

Pearson
Pairwise Complete
FDR / Benjamini-Hochberg
High Dimensionality Guard
Sparse Correlation

Architecture

Metric Registry
Multiple Testing Registry
Dependency Strategy
Evidence Model
Decision Trace

⸻

29. Future Extension

以下能力不列入 MVP，但 architecture 必須預留：

Spearman's rho
Kendall's tau
Mutual Information
Distance Correlation
VIF
Bonferroni
Holm correction
Bootstrap Confidence Interval
Permutation Test
Mixed Effects Model
Cluster-aware statistics
Time-series adjusted inference

其中：

VIF

將於未來 Feature Screening Epic 中加入，用於補足單純 Pairwise Correlation 無法完整診斷 Multicollinearity 的限制。

⸻

30. Final Architecture Principle

ds-data-miner 的核心定位不是：

A collection of statistical formulas.

而是：

An evidence-driven statistical analysis and diagnostic engine.

系統的核心價值在於：

                    ┌───────────────────┐
                    │       Data        │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │     Profiling     │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │     Evidence      │
                    │    Collection     │
                    └─────────┬─────────┘
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
       Distribution      Dependency       Data Quality
         Evidence          Evidence          Evidence
             │                │                │
             └────────────────┼────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  Strategy Registry│
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │   MetricSelector  │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Recommended Metric│
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  Decision Trace   │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Statistical Result│
                    └───────────────────┘

最終設計原則：

The engine must provide evidence, quantify uncertainty, expose dependencies, and explain why a statistical metric was recommended.

而不是：

The engine must always return a statistical answer.

當資料不足、樣本相依、時間相依、樣本極度不平衡、數值不穩定或證據不足時，系統應優先選擇：

Warning
    ↓
Insufficient Evidence
    ↓
No Forced Recommendation

而不是產生一個看似精確、實際上缺乏統計依據的數值。

這項原則是 ds-data-miner 在半導體製造資料、FDC、MES、Lot/Wafer-level analytics 與後續 MLOps Feature Engineering 場景中的核心可靠性保證。