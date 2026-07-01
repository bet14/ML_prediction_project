# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# GBP/USD ML Prediction Project

**Dự án:** Dự đoán chiều hướng GBP/USD ngày tiếp theo (binary: tăng/không tăng), ML, dữ liệu 2014–2024. Adapted từ paper Guyard & Deriaz (2024) về EUR/USD.
**Khóa học — 4 goals:** (1) Thu thập data nhiều nguồn (FRED/ONS/yfinance) · (2) EDA + define target · (3) Model pipeline + metrics · (4) Streamlit UI
**Branch:** `branch_lee` · Spec đầy đủ: `References/GBPUSD_ML_data_requirements_spec.md`

---

## Common Commands

```bash
# Check project data status (always run first)
python scripts\project_status.py

# Run full macro pipeline (fetch + process) — requires network
python run_fred_pipeline.py --start 2014-01-01 --end 2024-12-31
python run_fred_pipeline.py --skip-fetch          # process only, no network needed
python run_fred_pipeline.py --verify-only         # check series IDs only

# Fetch forex / equity (requires network — personal machine only)
run_forex_wip.bat --pair GBPUSD --source yfinance
run_equity_wip.bat --index FTAS --append

# Build Dataset 1 (Basic Daily) — runs in Cowork
python src/features/build_dataset.py

# Train models
python src/models/train.py --models LR RF XGB --fold 0   # one fold
python src/models/train.py --models LR RF XGB             # all folds

# Bayesian hyperparameter search
python src/models/bayesian_search.py --models RF --trials 50

# Streamlit UI
streamlit run src/app/app.py

# Git push (personal machine only, needs SSH key)
push.bat
```

---

## Architecture

### Data flow (linear, no cycles)

```
src/data/fetch_*.py          (needs network)
    -> data/raw/macro/       CSV per indicator, columns: date, realtime_start, value
    -> data/raw/forex/       13 pairs, OHLCV daily
    -> data/raw/equity/      9 indices, OHLCV daily

src/features/process_*.py   (runs in Cowork, pure pandas)
    -> data/interim/         one panel CSV per indicator group, daily-indexed, forward-filled

src/features/build_dataset.py
    -> data/processed/dataset_basic_daily.csv   (2868 rows × 110 cols, 2014-01-02 to 2024-12-30)
    -> data/processed/dataset_90day.csv         (not built yet)
    -> data/processed/dataset_technical.csv     (not built yet)

src/models/train.py  +  src/models/bayesian_search.py
    -> models/trained/*.joblib                  (one Pipeline per model×fold)
    -> models/search_results/*_best_params.json
    -> reports/tables/model_comparison.csv

src/app/app.py
    -> loads models/trained/  ->  Streamlit UI
```

### Key design decisions

**No-look-ahead bias:** Every macro CSV carries a `realtime_start` column (the date the value was first published, not the period it describes). The panel build step forward-fills using `realtime_start`, not the period date. This prevents leakage of future macro releases into past training rows.

**Walk-forward CV (expanding window):** 6 folds. Training always starts at 2014 and expands by one year. Test is always the year immediately after the last training year. 2024 is a true held-out set. See `src/evaluation/walk_forward_cv.py`.

**Model registry pattern:** All 22 models are defined in `src/models/model_registry.py` only — one `_build_X(params)` function + one `_suggest_X(trial)` Optuna function + one entry in `REGISTRY`. `train.py` and `bayesian_search.py` never change when adding models.

**Pipeline order (inside each sklearn Pipeline):** `InfinityToNaNTransformer` → `SimpleImputer(median)` → `[RobustScaler if scale=True]` → model. The custom transformer lives in `src/models/preprocessing.py` (separate file to avoid joblib pickling issues from `__main__`).

### What is and is not built yet

Built and working:
- Macro interim panels (gdp / cpi / rate / current_account) for USA; UK has gaps (see README)
- Forex and equity raw CSVs: placeholder headers only — run fetch scripts on personal machine
- Dataset 1 (Basic Daily): `data/processed/dataset_basic_daily.csv`, 2868 rows × 110 cols
- All 22 models in registry; 12 fast models trained (72 .joblib files in models/trained/)
- Walk-forward CV, metrics, Bayesian search — all functional
- EDA notebooks 01-03 (check notebooks/ directory for current state)

Not yet built:
- Dataset 2 (90-day lookback) and Dataset 3 (Technical indicators)
- `src/evaluation/backtest.py` — long strategy simulation
- `src/app/app.py` — Streamlit interface
- UK GDP replacement from ONS (script exists as WIP, not yet run)
- Composite PMI historical data (no free source found)

---

## Khi bắt đầu session mới

1. Auto chạy `python scripts\project_status.py` → in ra trạng thái từng file data (luôn đọc file thật, không bao giờ lỗi thời)
2. Hỏi có phải log gần đây nhất là như thế này, đọc **entry đầu tiên** `SESSION_LOG.md` → biết đang dừng ở đâu + bước tiếp theo
3. Tra `map.md` → "muốn làm X → dùng file nào" (lookup nhanh)
4. Đọc `PROJECT_GUIDE.md` nếu cần hiểu sâu: conventions đặt tên, flags pipeline, logic xử lý data

## Khi sửa code (bắt buộc)

Trước khi thay đổi bất kỳ file `.py` nào: copy file gốc sang `file_name.py.bak` cùng thư mục, rồi mới edit.
Ví dụ: sửa `src/features/process_gdp.py` → tạo `src/features/process_gdp.py.bak` trước.

## Output các file đầu ra, các file code với comment, output của print... tất cả đều bằng tiếng anh vì dự án này được đọc chung bởi nhiều người. 
Còn khi tôi(uer) hỏi tiếng việt, anh pháp lẫn lộn thì vẫn trả lời default bang tiếng Việt trừ phi có yêu cầu khác.

## Khi tạo file mới

Cập nhật `map.md` ngay lập tức — thêm dòng vào đúng section task tương ứng.
Kiểm tra: file đó có trong `scripts/project_status.py` CHECKLIST chưa? Nếu chưa → thêm luôn.

## Khi kết thúc session (làm thủ công trước khi đóng)

Thêm entry mới vào **đầu** `SESSION_LOG.md` theo template cuối file. Giữ tối đa **2 ngày** — entry ngày thứ 3 trở đi chuyển sang `SESSION_LOG_archive.md`.

## Cảnh báo môi trường

- **Cowork (không mạng):** không chạy `fetch_*.py` — chỉ xử lý data đã có, train model, chỉnh script
- **Máy cá nhân (có mạng):** fetch data → copy CSV vào repo → `push.bat`
