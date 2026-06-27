# Hướng dẫn Project: GBP/USD Direction Prediction

> **Đọc file này trước tiên** khi bắt đầu session mới.
> Sau đó đọc `SESSION_LOG.md` để biết đang làm đến đâu.

---

## Mục tiêu

Dự đoán chiều hướng GBP/USD ngày tiếp theo (tăng / không tăng) bằng Machine Learning.
Adaped từ paper Guyard & Deriaz (2024) về EUR/USD. Thay European Area → UK.

```
Direction(t) = 1  nếu close(t+1) > close(t)
Direction(t) = 0  nếu close(t+1) <= close(t)
```

**Dữ liệu:** 2014-01-01 → 2024-12-31 (≈ 11 năm, daily).

---

## Cấu trúc folder

```
ML_prediction_project/
│
├── data/
│   ├── raw/
│   │   ├── macro/          # Macro indicators (FRED, ONS) — CSV: date, realtime_start, value
│   │   ├── forex/          # 13 cặp FX, OHLCV daily — CSV: date, open, high, low, close, volume
│   │   └── equity/         # 9 equity indices (yfinance) — CSV: date, open, high, low, close, volume
│   ├── interim/            # Panel CSV trung gian: forward-filled theo ngày giao dịch
│   └── processed/          # (chưa có) Dataset cuối để train: Basic / 90-Day / Technical
│
├── src/
│   ├── data/               # Script fetch dữ liệu (cần mạng) + helper chung
│   ├── features/           # Script xử lý/transform raw → interim panel
│   ├── models/             # (scaffold) Training, Bayesian search, meta-stacking
│   ├── evaluation/         # (scaffold) Walk-forward CV, backtest, metrics
│   └── app/                # (scaffold) Streamlit interface
│
├── models/
│   ├── trained/            # Model đã train (.joblib/.pkl)
│   └── search_results/     # Kết quả Bayesian hyperparameter search
│
├── reports/
│   ├── macro_data_status.html   # Dashboard: raw/interim macro, lỗi, alternative API
│   ├── forex_data_status.html   # Dashboard: 13 cặp forex, Dukascopy vs yfinance
│   ├── equity_data_status.html  # Dashboard: 9 index, per-ticker confidence
│   ├── pipeline_run_log.jsonl   # Append-only: 1 dòng JSON / lần chạy pipeline
│   ├── figures/                 # Chart (feature importance, backtest)
│   └── tables/                  # model_comparison.csv, ...
│
├── notebooks/              # EDA (đánh số: 01_eda.ipynb, 02_...)
├── References/
│   ├── *.pdf               # 11 paper nghiên cứu (FX/AML/ML)
│   ├── GBPUSD_ML_data_requirements_spec.md   # Spec dữ liệu đầy đủ
│   ├── CLAUDE.md           # Kinh nghiệm rút ra, conventions (quan trọng!)
│   └── eurusd-forex-prediction.html
├── configs/                # .env.example (FRED_API_KEY, ONS_API_KEY)
├── Key/                    # fred_key.txt (gitignored — không commit)
│
├── run_fred_pipeline.py    # Chạy toàn bộ macro pipeline (fetch + process)
├── run_fred_pipeline.bat   # Wrapper bat cho run_fred_pipeline.py
├── run_equity_wip.bat      # Wrapper bat cho fetch_equity_wip.py
├── run_forex_wip.bat       # Wrapper bat cho fetch_forex_wip.py
├── auto_push.py / push.bat # Auto git add/commit/push + rebuild index.html
├── checklist.html          # Progress checklist (tiếng Việt)
├── checklist_en.html       # Progress checklist (tiếng Anh)
└── requirements.txt        # Python deps (cài trên máy cá nhân, không phải Cowork)
```

---

## Môi trường & Giới hạn

| Môi trường | Có mạng? | Có thể làm gì? |
|---|---|---|
| **Cowork sandbox** | KHÔNG | Đọc code, xử lý data đã có, train model, chỉnh sửa script |
| **Máy cá nhân** | CÓ | Fetch dữ liệu (`src/data/`), `pip install`, `push.bat` |
| **Google Colab / Kaggle** | CÓ | Fetch dữ liệu + train model nặng |

> Nếu dùng Claude Code trong Cowork: không thể chạy `fetch_*.py`, không thể `pip install`.
> Chạy xong trên máy cá nhân → copy CSV vào `data/raw/` → commit lại.

---

## Cách chạy pipeline chính

### Macro pipeline (FRED)
```bash
python run_fred_pipeline.py --start 2014-01-01 --end 2024-12-31
# Flags:
#   --verify-only  # chỉ check series id, không fetch
#   --skip-fetch   # chỉ chạy process_*.py trên raw CSV đã có
```

### Equity pipeline (yfinance)
```bash
run_equity_wip.bat                    # fetch tất cả 9 index
run_equity_wip.bat --index FTAS       # fetch riêng 1 index
run_equity_wip.bat --append           # append vào file đang có
```

### Forex pipeline
```bash
run_forex_wip.bat --source yfinance                     # nhẹ, volume không tin được
run_forex_wip.bat --source dukascopy                    # nặng (~800k requests), volume thật
run_forex_wip.bat --pair GBPUSD --source yfinance --append
```

---

## Trạng thái dữ liệu (xem thêm SESSION_LOG.md)

### `data/raw/macro/`
| File | Trạng thái |
|---|---|
| `USA_gdp.csv` | OK |
| `USA_cpi.csv` | OK |
| `USA_central_bank_rate.csv` | OK |
| `USA_current_account.csv` | OK |
| `UK_central_bank_rate.csv` | OK |
| `UK_gdp.csv` | STALE — FRED series dừng ở 2020-07 (Eurostat discontinued), không re-fetch được |
| `UK_cpi.csv` | STALE — ~15 tháng sau `USA_cpi.csv` |
| `UK_cpi_ons_alt.csv` | MỚI — ONS v1 beta API, series D7BT (mm23), 161 rows, chưa committed |
| `UK_current_account.csv` | MỚI — ONS v1 beta API, series HBOP (pnbp), 52 rows, chưa committed |
| `USA_composite_pmi.csv` | THIẾU — không có trên FRED, chỉ có ~3-4 release gần nhất từ investing.com |
| `UK_composite_pmi.csv` | THIẾU — tương tự USA |

### `data/raw/equity/`
Tất cả 9 CSV: header-only (dry-run đã test thành công 2026-06-26, cần chạy thật để ghi data).

### `data/raw/forex/`
Tất cả 13 CSV: header-only (chưa fetch, chưa test).

### `data/interim/`
4 panel CSV đã có: `gdp_panel.csv`, `cpi_panel.csv`, `central_bank_rate_panel.csv`, `current_account_panel.csv`.
Lưu ý: `current_account_panel.csv` hiện chỉ có USA (UK current account mới được fetch).

---

## Conventions quan trọng

### Naming file
- `fetch_*.py` — script fetch ổn định, được gọi bởi `run_fred_pipeline.py`
- `fetch_*_wip.py` — Work In Progress: đã verify schema nhưng **chưa chạy thật** hoặc chưa được tích hợp vào pipeline chính
- `process_*.py` — script xử lý raw CSV → interim panel (chạy được trong Cowork)

### `_wip.py` cần làm gì trước khi dùng
1. Đọc docstring → xem STATUS dòng đầu
2. Chạy `--verify-only` hoặc `--raw-dump` để check response thô trước khi parse
3. Chạy thật → kiểm tra output → nếu OK, quyết định có tích hợp vào pipeline chính không

### `reports/pipeline_run_log.jsonl`
Mỗi lần chạy script append 1 dòng JSON gồm: timestamp, `pipeline` ("macro"/"forex"/"equity"), mode, per-step result. Đây là lịch sử chạy duy nhất được persist trong repo.

---

## 3 Dataset cuối cần build (chưa có)

Khi đã có đủ `data/raw/`, cần build `data/processed/`:

| Dataset | Mô tả | Cột ước tính |
|---|---|---|
| **Dataset 1 — Basic Daily** | macro panel + OHLCV index/forex + date encoding | ~130 cột |
| **Dataset 2 — 90-Day Lookback** | Dataset 1 + lag 90 ngày cho từng feature | nhiều |
| **Dataset 3 — Technical** | Dataset 1 + 16 nhóm technical indicator per instrument | ~2000 cột (Bayesian feature selection) |

---

## Files cần đọc để hiểu sâu hơn

| Mục đích | File |
|---|---|
| Spec đầy đủ: data requirements, column list, transforms | `References/GBPUSD_ML_data_requirements_spec.md` |
| Kinh nghiệm fetch dữ liệu, gotchas, Cowork workaround | `References/CLAUDE.md` |
| Tiến độ checklist (dạng visual) | `checklist_en.html` (mở trong browser) |
| Dashboard data inventory | `reports/macro_data_status.html`, `reports/forex_data_status.html`, `reports/equity_data_status.html` |
| ERD của data pipeline | `eurusd_data_pipeline_erd.html` |
