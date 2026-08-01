# **系統結案驗收清單 (Final Sign-off Checklist)**

## **Epic 1: 資料輪廓與檢定引擎 (Data Profiling & Testing)**

**目標：確保系統能安全、精準地在本地端處理巨量原始資料，提供可靠的統計特徵。**

### **US 1.1: 本地全量特徵掃描**

**User Story:** 身為一名資料工程師，我希望套件能在本地記憶體中完整掃描一維或二維陣列（不進行隨機抽樣），以便獲得絕對精準的基礎統計量。

* **\[ \] AC 1.1.1:** 給定一個包含 100 萬筆 Float64 的 NumPy Array，呼叫 NumericProfiler.fit() 必須在合理時間內（如 1 秒內）回傳結果。  
* **\[ \] AC 1.1.2:** 系統不能在底層偷偷使用抽樣（Sampling），必須 100% 掃過所有資料。  
* **\[ \] AC 1.1.3:** 回傳的物件必須是嚴格定義的 DistributionProfile Dataclass，包含 mean, variance, skewness 等屬性。

### **US 1.2: 極端值防禦與警告**

**User Story:** 身為一名資料科學家，我希望在掃描含有 NaN 或 Inf 等髒資料時，系統能主動防禦並給出警告，而不是默默計算出錯誤的數值。

* **\[ \] AC 1.2.1:** 給定一個含有 NaN 或 np.inf 的陣列，Profiler 必須拋出明確的 DataQualityWarning 或自定義 Exception。  
* **\[ \] AC 1.2.2:** 提供參數選項（如 ignore\_nan=True）讓使用者決定遇到極端值時的處理策略。

### **US 1.3: 統計分佈檢定 (K-S Test)**

**User Story:** 身為一名資料科學家，我希望對感測器數值進行常態分配檢定，以便決定後續要使用何種統計模型。

* **\[ \] AC 1.3.1:** 呼叫 DistributionTester.test(data, dist="norm") 時，必須回傳顯著性數值 (P-value) 與是否拒絕虛無假設的 Boolean 值。  
* **\[ \] AC 1.3.2:** 單元測試中，該檢定結果必須與 scipy.stats.kstest 的結果進行比對，且絕對誤差 (atol) 需小於 $10^{-7}$。

### **US 1.4: 類別型資料比例與誤差推估**

**User Story:** 身為一名資料分析師，我希望系統能針對類別型或字串特徵進行全量掃描，並提供帶有統計誤差的比例，以準確反映類別分佈的不確定性。

* **\[ \] AC 1.4.1:** 系統能精準計算陣列中各獨立類別的出現次數與比例。  
* **\[ \] AC 1.4.2:** 系統必須自動套用二項式分佈標準誤公式 σ=√p(1-p)/N 來計算各類別的誤差（其中 p 為比例，N 為總樣本數）。

## **Epic 2: 不確定性誤差推估引擎 (Uncertainty Propagation)**

**目標：確保數學引擎能正確執行誤差傳遞，且完全不依賴外部資料容器。**

### **US 2.1: 基於 Jacobian 的解析法傳遞**

**User Story:** 身為一名演算法工程師，我希望針對「線性或可微的特徵轉換公式」，使用解析法進行誤差傳遞，以獲得最高運算效能。

* **\[ \] AC 2.1.1:** 給定兩個 UncertaintyArray 物件（代表變數 A 與 B）與一個數學轉換函式 f(A, B)，AnalyticalPropagator 必須回傳一個新的 UncertaintyArray。  
* **\[ \] AC 2.1.2:** 內部實作必須採用 NumPy 向量化運算（Vectorization），嚴禁使用 Python 原生 for 迴圈迭代 Array。  
* **\[ \] AC 2.1.3:** 當公式導致數學無效操作（如對負數開根號或除以零）時，系統需拋出 NumericalInstabilityError。

### **US 2.2: 基於蒙地卡羅的抽樣傳遞**

**User Story:** 身為一名機器學習工程師，我希望針對「高度非線性或不可微的黑盒子公式」，使用蒙地卡羅法來推估最終的誤差範圍。

* **\[ \] AC 2.2.1:** 呼叫 MonteCarloPropagator 時，使用者可以自定義模擬次數 n\_simulations（預設為 10,000）。  
* **\[ \] AC 2.2.2:** 必須確保蒙地卡羅抽樣過程中使用的 Random Seed 是可以被固定的，以保證實驗的重現性 (Reproducibility)。

## **Epic 3: 生態系與介面整合 (Adapters: Pandas & Matplotlib)**

**目標：提供流暢的使用者體驗，同時保衛核心領域的乾淨度（六角架構防腐層）。**

### **US 3.1: Pandas DataFrame 無縫擴充**

**User Story:** 身為一名習慣使用 Pandas 的分析師，我希望可以直接在 DataFrame 上呼叫 Profiling 函式，而不需要手動把 DataFrame 轉成 NumPy Array。

* **\[ \] AC 3.1.1:** 必須成功註冊 Pandas Accessor。使用者可以合法執行 df.trust.profile(cols=\["sensor\_1"\])。  
* **\[ \] AC 3.1.2:** **架構驗證：** 檢查 src/scikit\_trust/profiling 與 src/scikit\_trust/core 目錄下的所有程式碼，**絕對不可**出現 import pandas。Pandas 的依賴必須完全限縮在 pandas\_ext 模組中。  
* **\[ \] AC 3.1.3:** **動態路由驗證：** 轉接層需確保能根據 DataFrame 的欄位型態（數值 vs 字串/類別）自動正確派發任務至對應的 NumericProfiler 或 CategoricalProfiler。

### **US 3.2: 誤差帶繪圖輔助工具 (Viz Helper)**

**User Story:** 身為一名分析師，我希望在推估完 Uncertainty 後，能輕易畫出帶有信心水準誤差帶（Confidence Band）的折線圖。

* **\[ \] AC 3.2.1:** viz.plot\_uncertainty\_trend(ax, x\_data, y\_uarray) 能夠正確讀取 UncertaintyArray 的數值與誤差，並在傳入的 matplotlib.axes.Axes 上渲染出折線與半透明的誤差帶 (fill\_between)。  
* **\[ \] AC 3.2.2:** **架構驗證：** 檢查核心領域層模組，**絕對不可**出現 import matplotlib。

## **Epic 4: 工程品質、交付與部署 (Engineering & Delivery)**

**目標：符合現代化 Python 套件標準，隨時可供團隊透過 Git 進行安裝。**

### **US 4.1: 現代化套件建置與安裝**

**User Story:** 身為一名 DevOps / MLOps 工程師，我希望這個套件採用現代化的打包標準，方便整合進 Docker Image 或 CI/CD 管線中。

* **\[ \] AC 4.1.1:** 專案根目錄必須使用 pyproject.toml（基於 PEP 621），並且**沒有** setup.py。  
* **\[ \] AC 4.1.2:** 在乾淨的 Python 虛擬環境中，執行 pip install git+https://\[repo\_url\] 必須能成功安裝。  
* **\[ \] AC 4.1.3:** 提供可選依賴（Optional Dependencies）設定。執行 pip install . 時不裝 matplotlib；執行 pip install .\[viz\] 時才會安裝 matplotlib。

### **US 4.2: 型別安全與程式碼檢驗**

**User Story:** 身為團隊的 Tech Lead，我希望套件的程式碼品質受到嚴格管控，確保未來其他工程師接手維護時不會破壞核心邏輯。

* **\[ \] AC 4.2.1:** 全專案必須 100% 加上 Type Hints（型別提示）。  
* **\[ \] AC 4.2.2:** 在 CI 流程中，執行 mypy \--strict src/ 必須達到 0 errors。  
* **\[ \] AC 4.2.3:** 單元測試覆蓋率（Test Coverage）必須達到 85% 以上，並且包含針對 core 合約物件的 Property-Based Testing（如使用 hypothesis 套件隨機生成邊界值進行破壞測試）。

### **結案驗收會議 (Sign-off Meeting) 建議流程：**

> 1. **Demo 階段：** 由開發者展示一份 Jupyter Notebook，從頭到尾（讀取 Pandas CSV \-\> 跑統計檢定 \-\> 做誤差推估 \-\> 畫出誤差帶圖）。  
> 2. **Code Review 階段：** 展示 core 資料夾，證明裡面完全沒有 Pandas/Matplotlib 的 imports。  
> 3. **CI/CD 階段：** 展示 GitHub Actions (或 GitLab CI) 綠燈狀態，證明 mypy \--strict 與所有測試皆通過。  
> 4. **安裝階段：** 現場開一個乾淨的 Terminal，示範透過 pip install git+... 安裝並成功 import。

全數打勾後，這套 scikit-trust 即可正式 Release 成為團隊內部的基礎建設套件！