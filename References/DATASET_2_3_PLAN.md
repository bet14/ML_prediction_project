# Plan — Dataset 2 (90-Day Lookback) & Dataset 3 (Technical Indicators)

**Trạng thái:** Quyết định đã chốt (xem "QUYẾT ĐỊNH ĐÃ CHỐT — 2026-07-04" ngay bên dưới) — **chưa code gì**, session bị ngắt giữa chừng để đóng máy. Next session bắt đầu code luôn theo quyết định đã chốt, không cần hỏi lại.
**Ngày viết:** 2026-07-04
**Liên quan:** `References/GOAL3_PLAN.md` (kế hoạch tổng Goal 3, đã lỗi thời một phần — Dataset 1 + train.py/bayesian_search.py đã build xong), `References/GBPUSD_ML_data_requirements_spec.md` (spec gốc, mục 2.4 và mục 3).

---

## QUYẾT ĐỊNH ĐÃ CHỐT — 2026-07-04 (trả lời 4 điểm mở bên dưới, đọc trước khi code)

- **Q1 (lag date-encoding Dataset 2):** chốt theo đề xuất — **KHÔNG lag** 9 cột date-encoding. Dataset 2 ≈ 9.110 cột.
- **Q2 (90 dòng đầu thiếu lookback):** chốt theo đề xuất — **bỏ 90 dòng đầu** cho cả Dataset 2 và 3, còn lại ~2.778 dòng.
- **Q3 (hyperparameter train đầu tiên):** **chưa quyết** — user nói "tạo dataset trước, train sau" (`train sau`), nên câu hỏi này để lại cho session train, không chặn việc code Dataset 2/3.
- **Q4 (cách implement 16 họ chỉ báo Dataset 3):** **ĐỔI HƯỚNG so với đề xuất ban đầu của plan** — user chọn **dùng thư viện `ta` có sẵn thay vì viết tay toàn bộ**. Đã verify trực tiếp API `ta` cài trong project (`ta.trend`, `ta.momentum`, `ta.volume`), kết quả:
  - **12/16 họ có sẵn hàm trực tiếp trong `ta`, dùng ngay** (tất cả nhận tham số N tuỳ ý qua `window=`):
    | # | Họ | Hàm `ta` |
    |---|---|---|
    | 1 | Simple N-day MA (close) | `ta.trend.sma_indicator(close, window=N)` |
    | 2 | Weighted N-day MA (close) | `ta.trend.wma_indicator(close, window=N)` |
    | 3 | Simple N-day MA (volume, chỉ equity) | `ta.trend.sma_indicator(volume, window=N)` |
    | 4 | Weighted N-day MA (volume, chỉ equity) | `ta.trend.wma_indicator(volume, window=N)` |
    | 6 | Stochastic %K | `ta.momentum.stoch(high, low, close, window=N)` |
    | 7 | Stochastic %D | `ta.momentum.stoch_signal(high, low, close, window=N)` |
    | 8 | RSI | `ta.momentum.rsi(close, window=N)` |
    | 9 | Larry Williams %R | `ta.momentum.williams_r(high, low, close, lbp=N)` |
    | 11 | CCI | `ta.trend.cci(high, low, close, window=N)` |
    | 12 | ROC | `ta.momentum.roc(close, window=N)` |
    | 15 | MACD | `ta.trend.macd(close, window_fast=N, window_slow=M)` |
    | 16 | MACD signal | `ta.trend.macd_signal(close, window_fast=N, window_slow=M, window_sign=P)` |
  - **4/16 họ KHÔNG có trong `ta` → user chốt BỎ hẳn (không viết tay thay thế):** Momentum N-day (#5), A/D Oscillator (#10 — `ta.volume.acc_dist_index` bị loại vì là công thức Chaikin A/D Line khác hẳn Williams A/D Oscillator của paper, tên giống nhưng ý nghĩa khác), Disparity N-day (#13), OSCP N/M (#14).
  - **Cảnh báo quan trọng — lệch khỏi spec/paper:** một số hàm `ta` dùng công thức smoothing khác spec (VD RSI/Stochastic dùng Wilder's smoothing thay vì rolling mean đơn giản) — chấp nhận sai lệch nhẹ này, không phải blocking issue.
  - **Số cột Dataset 3 đã đổi:** do bỏ 4 họ (tổng 8+1+6+5=20 cột/instrument cho nhóm "Tất cả"), họ "Tất cả" còn 80−20=**60 cột/instrument** (thay vì 80). Equity = 60 + 12 (2 họ volume MA/WMA) = **72 cột/index**. Forex (không volume) = **60 cột/cặp**.
    | | Equity | Forex (13 cặp) | Tổng kỹ thuật | +110 Dataset 1 | **Tổng Dataset 3** |
    |---|---:|---:|---:|---:|---:|
    | Cũ (16 họ, viết tay) | 9 index × 92=828 | 13×80=1.040 | 1.868 | +110 | ≈1.978 |
    | Mới (12 họ, dùng `ta`), 9 index | 9×72=648 | 13×60=780 | 1.428 | +110 | ≈1.538 |
    | **Cập nhật 2026-07-06 — ĐÃ CHỐT: bỏ 5 equity index trùng lặp (đa cộng tuyến), còn 4 index** (`UK_FTSE100`, `USA_NASDAQ100`, `USA_RUSSELL2000`, `USA_SP500`) — cùng `REDUNDANT_INDICES` áp dụng cho Dataset 1 | 4×72=288 | 13×60=780 | 1.068 | +110 | **≈1.178** |

  > **Ghi chú (2026-07-06):** ban đầu `build_dataset_technical.py` tính chỉ báo kỹ thuật cho cả 9 equity index, quên áp dụng bộ lọc `REDUNDANT_INDICES` mà Dataset 1 đã dùng để loại 5 index đa cộng tuyến (`USA_DJI`, `USA_NASDAQ_COMPOSITE`, `UK_FTSE250`, `UK_FTSE350`, `UK_FTSE_ALL_SHARE`). Đã fix: import `REDUNDANT_INDICES` từ `build_dataset.py`, filter trước khi loop tính chỉ báo. Dataset 3 giảm từ ~1.538 xuống ~1.178 cột, đã rebuild + train lại 12 model × 6 fold.

---

---

## Bối cảnh / research đã làm

- `src/models/train.py` và `src/models/bayesian_search.py` **đã hỗ trợ sẵn đa-dataset** — dict `DATASET_FILES` đã có key `dataset_90day_lookback` và `dataset_technical` trỏ tới file CSV chưa tồn tại. Không cần sửa 2 file này, chỉ cần tạo đúng CSV đúng tên.
- 12 model đã train trên Dataset 1 = đúng nhóm `FAST_MODELS` trong `src/models/model_registry.py`: `LR, RF, XGB, LGBM, MLP, KNN, DT, ET, HGB, CatBoost, Bagging_DT, Bagging_LR`.
- Package `ta` đã có sẵn trong `requirements.txt` và đã cài, nhưng công thức trong spec (VD: A/D Oscillator, OSCP) là công thức riêng của paper Guyard & Deriaz, không trùng 100% với hàm mặc định của thư viện `ta`.
- `data/interim/forex_panel.csv` (13 cặp, chỉ open/high/low/close, không volume) và `data/interim/equity_panel.csv` (9 index, có thêm volume + volume_sqrt) đã đầy đủ, dùng trực tiếp để tính technical indicators cho Dataset 3.
- `data/processed/dataset_basic_daily.csv`: 2.868 dòng × 110 cột feature + cột `Direction` (target), 2014-01-02 → 2024-12-30.
- Tính thử số cột theo công thức spec mục 2.4 → khớp với ước tính của spec:
  - Equity (đủ 16 họ, có volume MA): 92 cột/index × 9 index = 828 cột
  - Forex (bỏ họ volume MA rows 3-4): 80 cột/cặp × 13 cặp = 1.040 cột
  - Tổng Dataset 3 ≈ 1.868 cột kỹ thuật + 110 cột Dataset 1 ≈ **~1.980 cột**
- Dataset 2: mỗi cột trong 110 cột Dataset 1 × 90 lag ≈ 9.900 cột lag + 110 gốc ≈ **~10.000 cột**

---

## Kế hoạch file (toàn bộ file mới, không sửa code cũ)

### 1. Dataset 2 — 90-Day Lookback
**File mới:** `src/features/build_dataset_90day.py`
- Load `data/processed/dataset_basic_daily.csv`
- Với mỗi feature column (trừ `Direction`), tạo `{col}_lag1` .. `{col}_lag90` bằng `.shift(1..90)`
- Bỏ N dòng đầu thiếu lookback (xem quyết định #2 bên dưới)
- Output: `data/processed/dataset_90day_lookback.csv`

### 2. Dataset 3 — Technical Indicators
**File mới:**
- `src/features/technical_indicators.py` — hàm thuần cho 16 họ chỉ báo theo đúng công thức mục 2.4 của spec (SMA, WMA, SMA/WMA volume, Momentum, Stochastic %K/%D, RSI, Williams %R, A/D Oscillator, CCI, ROC, Disparity, OSCP, MACD, MACD signal), nhận OHLC(V) của một instrument, trả về DataFrame các cột chỉ báo.
- `src/features/build_dataset_technical.py` — load `forex_panel.csv` + `equity_panel.csv`, gọi `technical_indicators.py` cho từng trong 22 instrument, gộp với `dataset_basic_daily.csv`.
- Output: `data/processed/dataset_technical.csv`

### 3. Train 12 model trên 2 dataset mới
```
python src/models/train.py --dataset dataset_90day_lookback --models LR RF XGB LGBM MLP KNN DT ET HGB CatBoost Bagging_DT Bagging_LR
python src/models/train.py --dataset dataset_technical         --models LR RF XGB LGBM MLP KNN DT ET HGB CatBoost Bagging_DT Bagging_LR
```
- Kết quả tự append vào `reports/tables/model_comparison.csv` (cơ chế merge theo key `dataset+model+fold` đã có sẵn trong `train.py`).
- Chạy được ở Cowork (không cần mạng).
- Khuyến nghị: test `--fold 0` một model trước để đo thời gian trước khi chạy full 6 fold × 12 model (Dataset 2 có ~10.000 cột nên sẽ chậm hơn nhiều so với Dataset 1).

### 4. Báo cáo so sánh riêng
**File mới:**
- `scripts/plot_dataset_comparison.py` — chart so sánh Dataset 1 vs 2 vs 3 trên cùng 12 model.
- `scripts/generate_dataset_comparison_report.py` → `reports/dataset_comparison.html`
- Metrics so sánh: accuracy, F1-macro, AUC-ROC, Sharpe proxy, max drawdown — cả CV (trung bình fold 1-5) lẫn Final (2024) + gap CV→Final (đo overfitting).

### 5. Cập nhật `map.md`
- Thay 2 dòng hiện đang ghi "NOT BUILT YET" cho Dataset 2/3 bằng tên file thật.
- Thêm dòng cho `reports/dataset_comparison.html` trong section Model & Evaluation.
- (map.md luôn viết tiếng Anh theo quy ước riêng của project.)

---

## Dataset 2 — vì sao lên tới ~9.000-10.000 cột? (breakdown theo group)

`dataset_basic_daily.csv` có 110 cột (109 feature + 1 target `Direction`, không lag target). Mỗi feature nhân với 90 lag (`_lag1`..`_lag90`) — nhóm nào nhiều cột gốc thì nhóm đó "nở" ra nhiều lag nhất:

| Group | Cột gốc (Dataset 1) | ×90 lag | Cột lag thêm | Ghi chú |
|---|---:|---:|---:|---|
| Forex OHLC (13 cặp × 4: open/high/low/close) | 52 | ×90 | 4.680 | **Nhóm lớn nhất** — chiếm hơn nửa số cột lag |
| Macro (GDP/CPI/rate/current-account, USA+UK, value + days_since_update + biến đổi) | 19 | ×90 | 1.710 | |
| Equity OHLC (4 index còn lại × 4: open/high/low/close) | 16 | ×90 | 1.440 | Sau khi đã bỏ 5 index trùng lặp (đa cộng tuyến) |
| Equity volume + volume_sqrt (4 index × 2) | 8 | ×90 | 720 | |
| Equity log-return (4 index × 1) | 4 | ×90 | 360 | |
| rate_differential | 1 | ×90 | 90 | |
| Date encoding (day/month/weekday + 6 sin/cos) | 9 | **không lag** | 0 | Theo đề xuất Q1 — xem lý do bên dưới |
| **Tổng lag** | **100** | | **9.000** | |
| + 109 cột gốc (feature) + 1 cột target | | | +110 | |
| **TỔNG Dataset 2** | | | **≈9.110 cột** | Nếu lag luôn cả date-encoding (bỏ qua Q1): +810 → **≈9.920 cột** |

Vì sao forex OHLC chiếm nhiều nhất: 13 cặp tiền × 4 giá × 90 ngày = con số lớn nhất trong toàn bộ pipeline, không phải do lỗi thiết kế — đây chính là cách "lookback 90 ngày" của paper gốc hoạt động (mỗi ngày quá khứ là 1 cột riêng, không phải rolling window).

**Về mối lo `p ≈ 9.000-10.000 >> n ≈ 2.700 dòng`:** đây là rủi ro thật (curse of dimensionality), đã ghi trong mục "Rủi ro" bên dưới. Cách giảm nếu sau khi có baseline thấy cần thiết:
- Không lag date-encoding (đã đề xuất ở Q1) → giảm 810 cột.
- Rút gọn phạm vi lag (VD chỉ lag 1-30 ngày thay vì 1-90) — lệch khỏi đúng nghĩa "90-day lookback" của spec nên **không làm ở bước đầu**, chỉ cân nhắc nếu baseline cho thấy overfit quá nặng.
- Feature selection sau khi có baseline (Bayesian/RF-importance) — đúng như cách paper gốc xử lý Dataset 3, có thể áp dụng tương tự cho Dataset 2 ở bước sau, không làm trước khi có số liệu baseline.

---

## Dataset 3 — 16 họ chỉ báo kỹ thuật là gì?

Theo spec mục 2.4, mỗi họ tính **độc lập cho từng instrument** (dùng OHLC(V) riêng của nó), N là số ngày trong cửa sổ:

| # | Tên | Ý nghĩa ngắn gọn | Số N (tham số) | Áp dụng cho |
|---|---|---|---:|---|
| 1 | Simple N-day MA (close) | Trung bình cộng giá đóng cửa N ngày | 6 (N=3,7,14,30,60,90) | Tất cả |
| 2 | Weighted N-day MA (close) | Trung bình có trọng số (ngày gần trọng số cao hơn) | 6 | Tất cả |
| 3 | Simple N-day MA (volume) | Trung bình cộng khối lượng giao dịch N ngày | 6 | **Chỉ equity** |
| 4 | Weighted N-day MA (volume) | Trung bình có trọng số của khối lượng | 6 | **Chỉ equity** |
| 5 | Momentum N-day | Chênh lệch giá đóng cửa so với N ngày trước | 8 (N=1,2,3,7,14,30,60,90) | Tất cả |
| 6 | Stochastic %K N-day | Vị trí giá hiện tại trong biên độ cao/thấp N ngày | 8 | Tất cả |
| 7 | Stochastic %D N-day | Trung bình N ngày của %K | 8 | Tất cả |
| 8 | RSI N-day | Chỉ số sức mạnh tương đối (tỷ lệ tăng/giảm) | 5 (N=7,14,30,60,90) | Tất cả |
| 9 | Larry Williams %R N-day | Tương tự Stochastic, đảo dấu | 8 | Tất cả |
| 10 | A/D Oscillator | Dao động tích lũy/phân phối (công thức riêng paper) | 1 (không tham số) | Tất cả |
| 11 | CCI N-day | Chỉ số kênh hàng hóa (độ lệch giá so với trung bình) | 5 | Tất cả |
| 12 | ROC close N-day | Tỷ lệ thay đổi giá so với N ngày trước (%) | 8 | Tất cả |
| 13 | Disparity N-day | Tỷ lệ giá hiện tại / trung bình N ngày (%) | 6 | Tất cả |
| 14 | OSCP N/M-day | Chênh lệch % giữa 2 tổng giá N-ngày và M-ngày | 5 cặp (N,M) | Tất cả |
| 15 | MACD N-fast/M-slow | Chênh lệch EMA nhanh − EMA chậm | 3 cặp | Tất cả |
| 16 | MACD signal N/M/P | EMA của chính MACD (đường tín hiệu) | 3 bộ ba | Tất cả |

**Tổng cột/instrument:**
- 14 họ "Tất cả" (1,2,5,6,7,8,9,10,11,12,13,14,15,16) = 6+6+8+8+8+5+8+1+5+8+6+5+3+3 = **80 cột**
- + 2 họ volume (3,4) chỉ dành cho equity = +12 cột → equity = **92 cột/index**
- Forex (không volume) = giữ nguyên **80 cột/cặp**

### Câu hỏi: forex không có volume thì có bớt được cột không? Còn lại bao nhiêu cột?

**Có — và thực ra kế hoạch hiện tại đã tự động bớt rồi**, vì họ #3 và #4 (volume MA/WMA) được đánh dấu "chỉ áp dụng equity" ngay từ spec — forex tự động **không có** 12 cột đó, không cần làm gì thêm:

| Kịch bản | Equity (9 index) | Forex (13 cặp) | Tổng cột kỹ thuật | + 110 cột Dataset 1 | Tổng Dataset 3 |
|---|---:|---:|---:|---:|---:|
| **Hiện tại (equity giữ volume, forex bỏ tự nhiên)** | 9 × 92 = 828 | 13 × 80 = 1.040 | **1.868** | +110 | **≈1.978 cột** |
| Nếu forex "giả lập" volume=0 và vẫn tính 2 họ volume (không nên làm) | 9 × 92 = 828 | 13 × 92 = 1.196 | 2.024 | +110 | 2.134 cột |
| Thay thế: bỏ luôn 2 họ volume cho **cả equity** (đồng nhất 80 cột/instrument mọi loại) | 9 × 80 = 720 | 13 × 80 = 1.040 | 1.760 | +110 | **≈1.870 cột** |

- Dòng 1 = kế hoạch đang đề xuất (Q4 ở trên) — tận dụng volume thật của equity vì dữ liệu có sẵn và có ý nghĩa, forex tự động gọn hơn vì thiếu volume.
- Dòng 3 = phương án thay thế nếu muốn đơn giản hoá tuyệt đối (bỏ hẳn tín hiệu volume để 22 instrument đồng nhất công thức) — giảm thêm 108 cột, nhưng mất thông tin volume của equity (vốn có thật và hữu ích). **Không khuyến nghị** trừ khi ưu tiên đơn giản hơn là giữ thông tin.
- → Trả lời ngắn gọn: **không cần làm gì thêm để "bớt" cột do thiếu volume ở forex** — điều đó đã nằm sẵn trong công thức spec (forex chỉ 80 cột thay vì 92). Tổng Dataset 3 dự kiến **≈1.978 cột**.

---

## Nếu chỉ train thử 2 model/dataset trước — nên chọn model nào?

| Dataset | Model 1 | Vì sao | Model 2 | Vì sao |
|---|---|---|---|---|
| **Dataset 2** (90-day lookback, ~9.000-10.000 cột, p≫n) | `LR` | Baseline tuyến tính đã có kết quả Dataset 1 để so sánh trực tiếp; nhưng dự kiến sẽ overfit nặng hơn nữa ở Dataset 2 (p≫n cực đoan) — phép thử tốt để đo mức độ overfit tăng thêm | `LGBM` | Cây gradient-boost xây theo histogram, xử lý native hàng nghìn cột mà không cần scale, có regularization cấu trúc (num_leaves/depth) — mô hình "chịu được" chiều cao dữ liệu tốt nhất trong nhóm fast |
| **Dataset 3** (technical indicators, ~1.978 cột) | `XGB` | Chính bảng "Expected results" trong `GOAL3_PLAN.md` (dựa trên paper Guyard & Deriaz) dự đoán XGB đạt kết quả tốt nhất **đúng với Dataset 3** | `LGBM` | Cùng lý do — paper dự đoán "XGB/LGBM: 54–57%, best with Dataset 3 + Bayesian search", nên đây là 2 model có cơ sở lý thuyết mạnh nhất để thử trước |

→ Nếu muốn tối giản hơn nữa (chỉ 1 lệnh, 2 model, cả 2 dataset): `LGBM` xuất hiện ở cả hai vì vừa chịu được chiều cao dữ liệu (Dataset 2) vừa được paper dự đoán mạnh trên chỉ báo kỹ thuật (Dataset 3) — có thể coi là "model bắt buộc phải thử", còn LR/XGB là model đối chứng thêm cho từng dataset.

---

## Q&A: Vì sao lookback 90 ngày, không phải 30 hay 180?

**Đã kiểm tra trực tiếp paper gốc** (`References/10_FX_EURUSD_ML_Direction_Prediction.pdf`, Guyard & Deriaz 2024) — paper **không giải thích lý do chọn đúng số 90**. Nguyên văn chỉ có một câu: "Dataset 2 combined daily data with the preceding 90 days' data" (mục 4.3) — không có ablation study so sánh 30/60/90/180 ngày.

Tuy nhiên có 2 bằng chứng gián tiếp trong chính paper giúp suy luận có căn cứ:

1. **90 không phải số riêng của Dataset 2 — nó là biên trên của một "thang cửa sổ" dùng xuyên suốt cả 16 họ chỉ báo kỹ thuật (Table 1 của paper, = mục 2.4 trong spec của project này).** Tất cả các N-day indicator (SMA, Momentum, RSI, CCI, ROC, Stochastic, Williams %R, Disparity...) đều dùng cùng một tập N ∈ {3, 7, 14, 30, 60, 90} — tức 1 ngày, ~1 tuần, 2 tuần, ~1 tháng, ~2 tháng, ~1 quý. Đây là thang "ngày → tuần → tháng → quý" khá phổ biến trong phân tích kỹ thuật tài chính (nhiều khung thời gian chuẩn: ngắn/trung/dài hạn), không phải con số paper tự nghĩ ra riêng cho Dataset 2 — họ chỉ lấy đúng biên trên (90) của thang đó làm độ dài lookback cho Dataset 2, cho **đồng bộ với Dataset 3**.
2. **90 ngày ≈ 1 quý tài chính** — trùng với chu kỳ công bố GDP hàng quý (một trong các chỉ số macro đã đưa vào Dataset 1). Nói cách khác, lookback 90 ngày đủ dài để "nhìn thấy" trọn 1 chu kỳ công bố macro chậm nhất trong dữ liệu, không phải con số ngẫu nhiên.

**Về hiệu quả thực tế — paper không chứng minh 90 ngày là tối ưu.** Tra bảng kết quả (Table 2, "Results of models without PCA") trong chính paper: Dataset 2 (90-day) **không** vượt trội rõ rệt so với Dataset 1 ở nhiều model — VD Logistic Regression: Dataset 1 monthly acc=53.7% / annually=51.4%, Dataset 2 monthly=53.3% / annually=51.1% (gần như ngang nhau, thậm chí hơi thấp hơn). Một số model khác (KNN) thì Dataset 2 annually cao hơn Dataset 1 nhưng monthly lại thấp hơn — kết quả lẫn lộn, không có xu hướng rõ "wider = better". Điều này khớp với phần "Rủi ro" đã ghi ở trên: bản thân paper gốc cũng gặp vấn đề p≫n với Dataset 2/3, và lý do họ làm tiếp PCA + feature selection ở phần sau của paper chính là để xử lý việc thêm cột không tự động cải thiện kết quả.

**Đánh đổi nếu chọn 30 hoặc 180 thay vì 90 (suy luận của tôi, không phải paper):**

| Lựa chọn | Số cột lag (≈100 feature lag-eligible) | Ưu điểm | Nhược điểm |
|---|---:|---|---|
| 30 ngày | 100×30 = 3.000 lag cột (~3.100 tổng) | p≫n đỡ cực đoan hơn nhiều, train nhanh hơn nhiều | Có thể bỏ lỡ pattern theo chu kỳ quý (GDP, một số chỉ báo kỹ thuật N=60/90 cũng cần dữ liệu xa hơn) |
| **90 ngày (theo spec/paper)** | 100×90 = 9.000 lag cột (~9.110 tổng) | Đồng bộ với biên N=90 của Dataset 3, đủ dài để phủ 1 chu kỳ macro quý | p≫n rất cực đoan, train chậm, rủi ro overfit cao (paper cũng gặp) |
| 180 ngày | 100×180 = 18.000 lag cột (~18.110 tổng) | Phủ được pattern nửa năm | Gấp đôi cột của phương án 90 mà tự tương quan giá FX hàng ngày thường suy giảm nhanh sau vài tuần — biên lợi ích thêm rất thấp so với chi phí (cột, thời gian train, overfit) tăng thêm |

→ **Kết luận:** giữ 90 ngày theo đúng spec/paper (để so sánh nhất quán với Dataset 3 và với chính nghiên cứu gốc), nhưng ghi nhận rõ đây là lựa chọn kế thừa từ paper (theo "thang thời gian ngày/tuần/tháng/quý"), không phải con số đã được paper chứng minh tối ưu bằng thực nghiệm — nên nếu baseline Dataset 2 cho kết quả kém/overfit nặng, việc thử lại với lookback ngắn hơn (30 hoặc 60 ngày) là một hướng điều chỉnh hợp lý ở bước sau, không đi ngược lại spec một cách tuỳ tiện.

---

## Q&A: Dataset 3 (technical indicators) có cải thiện đáng kể theo paper gốc không?

**Có, nhưng có điều kiện — cải thiện tập trung ở một số model, không phải đồng loạt.** Trích trực tiếp mục "6 Results" của paper:

> "In this study, **histogram gradient boosting achieved the highest prediction accuracy, scoring 58.52%**." ... "Whether for models with PCA, without PCA or meta estimators, **dataset 3 reached the best accuracy**. This highlights the fact that feature engineering with domain knowledge enhances the models' understanding of the problem."

Đối chiếu với Table 2 (không PCA) trong paper: **58.52%** chính là kết quả của **Histogram Gradient Boosting trên Dataset 3 (annually)** — con số cao nhất trong toàn bộ 21 model × 3 dataset × 2 kỳ đánh giá của cả bài báo. Kết luận "dataset 3 luôn đạt accuracy tốt nhất" được paper lặp lại ở **cả 3 điều kiện**: không PCA, có PCA, và meta-estimator.

**Nhưng khi tôi tính trung bình cộng cả 21 model trên Table 2 (không PCA) thì bức tranh phức tạp hơn — không phải cải thiện đồng loạt:**

| | Dataset 1 | Dataset 2 | Dataset 3 |
|---|---:|---:|---:|
| Accuracy trung bình — Monthly | 51.97% | 50.77% | 50.85% |
| Accuracy trung bình — Annually | 50.94% | 51.24% | 50.73% |
| Số model có annual acc > Dataset 1 | — | 10/21 | 9/21 |
| Kết quả tốt nhất (1 model) | Bagging SVM linear: 54.0% (annually) | Bagging KNN: 55.9% (annually) | **HistGB: 58.5% (annually) ← cao nhất toàn bài** |

→ **Tính trung bình trên toàn bộ 21 model, Dataset 3 (raw, chưa xử lý gì thêm) không vượt trội hơn Dataset 1** — thậm chí nhỉnh hơn hay kém hơn tùy model, giống hệt tình trạng mà Dataset 2 gặp (đã nói ở câu hỏi trước). **Cải thiện thực sự chỉ xuất hiện rõ ở một nhóm nhỏ model** — đặc biệt các gradient-boosting dựa trên histogram (HistGB) — và **rõ nét nhất sau khi paper áp dụng Bayesian search + feature selection** (phần sau của paper, xem thêm `References/bayesian-search.html`), không phải ngay từ dữ liệu thô.

**Một nuance quan trọng khác — accuracy tốt nhất và profit tốt nhất đến từ 2 dataset khác nhau:**
- Accuracy tốt nhất toàn bài (58.52%) → Dataset 3, HistGB.
- Profit/annual-return tốt nhất trong Table 2 (29.54%) → **Dataset 1**, Logistic Regression (không phải Dataset 3).
- Paper tự nhận xét: "accuracy and profit do not necessarily correlate" — một model đoán đúng nhiều ngày hơn (accuracy cao) không chắc sinh lời nhiều hơn (có thể đoán đúng các ngày biến động nhỏ, sai các ngày biến động lớn).

**Áp dụng cho GBP/USD project này:** kỳ vọng hợp lý là Dataset 3 (technical indicators) **có tiềm năng đạt kết quả tốt nhất nhưng không chắc chắn cải thiện mọi model** — nên khi so sánh, báo cáo cần nhìn cả accuracy lẫn Sharpe proxy (tương đương "profit" của paper) cho từng model, không chỉ nhìn accuracy trung bình. Đây cũng là lý do ở câu trả lời trước tôi đề xuất thử `XGB`/`LGBM` trước cho Dataset 3 — cùng họ gradient-boosting với HistGB, model duy nhất paper gốc ghi nhận cải thiện rõ rệt.

---

## Q&A: Project có dùng PCA không? PCA có phải để xem feature nào ảnh hưởng nhất?

**Xác nhận: project hiện tại KHÔNG dùng PCA ở đâu cả.** Pipeline trong `train.py` (`build_pipeline()`) chỉ có 3-4 bước: `InfinityToNaNTransformer → SimpleImputer(median) → [RobustScaler nếu scale=True] → model`. Không có bước PCA.

**Nhưng PCA không phải công cụ để xem feature gốc nào ảnh hưởng nhất — đây là hiểu nhầm phổ biến.** PCA (Principal Component Analysis) làm việc khác hẳn:

- PCA tạo ra các **trục mới** (principal component 1, 2, 3...) — mỗi trục là **tổ hợp tuyến tính của TẤT CẢ feature gốc** (VD: PC1 = 0.3×GBP_USD_close + 0.1×USA_gdp − 0.05×UK_cpi_yoy + ... cộng hết ~110/1.980/9.110 cột lại), sắp xếp theo lượng phương sai (variance) mà mỗi trục giải thích được.
- Mục đích chính: **giảm số chiều** (nhiều cột tương quan cao → gộp thành ít trục độc lập hơn) và **decorrelate** (loại tương quan giữa các feature) — không phải để "chấm điểm" xem cột gốc nào quan trọng.
- Hệ quả: sau PCA, bạn **mất khả năng diễn giải** — không thể nói "PC1 quan trọng nhất" rồi suy ra "vậy GBP_USD_close là feature quan trọng nhất", vì PC1 đã trộn lẫn thông tin của mọi cột theo trọng số khác nhau.

**Công cụ đúng để trả lời "feature nào ảnh hưởng nhất" — và project này đã có sẵn, không cần PCA:**
1. **`feature_importances_` của model dạng cây** — `src/app/app.py` dòng 142-146 đã làm sẵn: sau khi train xong, nếu model có thuộc tính này (RF/XGB/LGBM/ET/CatBoost/HGB/DT/Bagging_DT đều có), Streamlit tự vẽ bar chart top-15 feature quan trọng nhất. Cơ chế này áp dụng được ngay cho Dataset 2/3 sau khi train xong, không cần code thêm.
2. **Phân tích tương quan (correlation)** — notebook `03_feature_analysis.ipynb` đã dùng cách này để tìm và loại 5 equity index trùng lặp (đa cộng tuyến) khi build Dataset 1 (xem `CPI_LEVEL_COLS`/`REDUNDANT_INDICES` trong `build_dataset.py`).
3. **Bayesian-search feature selection** — cách chính paper gốc dùng cho Dataset 3 (đã nêu trong "Rủi ro" ở trên và trong `References/bayesian-search.html`) — chọn feature bằng cách để Optuna thử bớt/giữ feature và đo hiệu quả thực tế, không suy diễn qua trục PCA.

**Bằng chứng từ chính paper gốc: PCA làm kết quả TỆ HƠN, không phải tốt hơn.** Trích mục "6 Results": *"Using PCA prior to model input resulted in lower accuracy and profit. Indeed, when using PCA, the highest achieved accuracy was 54.98%, and the greatest profit was 24.05%"* — so với 58.52% accuracy tốt nhất khi KHÔNG dùng PCA. Paper tự đưa giả thuyết: *"application of PCA prior to model input leads to a less effective representation of temporal relationships in the data"* — tức PCA phá vỡ cấu trúc thời gian (chuỗi lag 90 ngày, chỉ báo kỹ thuật theo N-ngày) mà chính Dataset 2/3 được thiết kế để khai thác.

**Kết luận cho project này:** không cần thêm PCA — vừa không phải công cụ đúng để trả lời câu hỏi "feature nào quan trọng" (đã có `feature_importances_` + correlation analysis làm việc này tốt hơn và dễ diễn giải hơn), vừa có bằng chứng thực nghiệm từ chính paper gốc là PCA làm giảm accuracy trên đúng loại bài toán time-series này.

---

## Rủi ro / lưu ý

- **Dataset 2 có p≈10.000 >> n≈2.700 dòng** ở fold đầu (train 2014-2018) → nguy cơ overfit rất cao cho LR/KNN; model cây (RF/ET/XGB/LGBM/CatBoost/HGB) đỡ hơn nhờ feature-subsampling per split. Đây cũng chính là lý do paper gốc dùng Bayesian-search feature selection thay vì đưa hết feature vào một lượt — sẽ ghi rõ caveat này trong báo cáo, **không tự ý cắt feature trước khi có baseline**.
- Train trên ~10.000 cột sẽ chậm hơn đáng kể so với Dataset 1 (110 cột).

---

## 4 điểm mở — cần user quyết định trước khi code

### Q1. Dataset 2 có nên lag cả cột date-encoding (day/month/weekday, sin/cos) không?
- **Đề xuất: KHÔNG lag** — loại 3 cột int (day/month/weekday) + 6 cột sin/cos khỏi lag stack. Lý do: giá trị ngày trong quá khứ suy ra được trực tiếp từ ngày hiện tại (không random), lag không thêm thông tin, giảm ~540 cột thừa vô nghĩa.
- Lựa chọn khác: lag tất cả kể cả date-encoding — đúng sát nghĩa đen "mỗi feature đều có 90 lag" của spec, nhưng thêm cột không có giá trị thông tin.

### Q2. Xử lý 90 dòng đầu tiên thiếu dữ liệu lookback (lag/rolling window 90 ngày chưa đủ)?
- **Đề xuất: bỏ 90 dòng đầu** cho cả Dataset 2 và Dataset 3, còn lại ~2.778 dòng. Tránh việc `SimpleImputer(median)` trong pipeline tự bịa giá trị lag/indicator cho giai đoạn đầu, tránh làm méo kết quả fold 1 (train 2014-2018).
- Lựa chọn khác: giữ nguyên 2.868 dòng, để median imputer xử lý — đơn giản hơn nhưng 90 dòng đầu sẽ có giá trị lag/indicator không phản ánh đúng thực tế.

### Q3. Lượt train đầu tiên trên Dataset 2/3 nên dùng hyperparameter nào?
- **Đề xuất: dùng default params** trong `model_registry.py` (nhanh, chỉ để xem baseline Dataset 2/3 so với Dataset 1 có khá hơn không). Nếu kết quả có tiềm năng, chạy Bayesian search riêng sau.
- Lựa chọn khác: chạy Bayesian search riêng cho từng dataset trước khi train — chính xác hơn nhưng rất tốn thời gian (50 trials × 4 fold × 12 model × 2 dataset, đặc biệt chậm với Dataset 2 ~10.000 cột).

### Q4. Cách implement 16 họ chỉ báo kỹ thuật (Dataset 3)?
- **Đề xuất: viết tay theo đúng công thức trong spec** (mục 2.4) — khớp chính xác công thức paper gốc (A/D Oscillator, OSCP là công thức riêng, không phải chuẩn TA-Lib), kiểm soát được số cột chính xác (~92/equity, ~80/forex).
- Lựa chọn khác: dùng thư viện `ta` có sẵn — code nhanh hơn nhưng một số công thức (A/D Oscillator, OSCP, Stochastic %D) sẽ khác spec, kết quả không khớp paper gốc.

---

## Next steps (cập nhật 2026-07-04 — quyết định đã chốt, bắt đầu code ngay, không hỏi lại)
1. `src/features/technical_indicators.py` — viết hàm dùng `ta` cho 12 họ có sẵn (xem bảng hàm ở mục "QUYẾT ĐỊNH ĐÃ CHỐT" đầu file), bỏ hẳn 4 họ #5/#10/#13/#14. Nhận OHLC(V) một instrument, trả DataFrame cột chỉ báo (~60 cột/instrument, +12 nếu có volume).
2. `src/features/build_dataset_technical.py` — load `forex_panel.csv` (13 cặp) + `equity_panel.csv` (9 index, lọc bỏ 5 index trùng lặp qua `REDUNDANT_INDICES` → còn 4 index — fix 2026-07-06), gọi hàm ở bước 1 cho từng instrument, gộp với `dataset_basic_daily.csv`, bỏ 90 dòng đầu (Q2), output `data/processed/dataset_technical.csv` (~1.178 cột).
3. `src/features/build_dataset_90day.py` — load `dataset_basic_daily.csv`, lag mỗi feature (trừ 9 cột date-encoding theo Q1 và trừ `Direction`) từ lag1-lag90, bỏ 90 dòng đầu (Q2), output `data/processed/dataset_90day_lookback.csv` (~9.110 cột).
4. Cập nhật `map.md` (tiếng Anh) — thay 2 dòng "NOT BUILT YET" bằng tên file thật.
5. **Chỉ tạo dataset, KHÔNG train** ở bước này theo yêu cầu user ("tạo dataset trước, train sau") — Q3 (hyperparameter train đầu tiên) để quyết ở session train riêng.
6. Khi user quay lại yêu cầu train: dùng lệnh mẫu ở mục "3. Train 12 model trên 2 dataset mới" phía trên, khuyến nghị test `--fold 0` một model trước để đo thời gian (Dataset 2 ~9.110 cột sẽ chậm hơn nhiều so với Dataset 1).
