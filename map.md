# map.md — File Registry theo Task

> Tra cứu nhanh: "tôi muốn làm X → tôi cần file nào"
> Không cần đọc PROJECT_GUIDE.md trừ khi cần hiểu sâu conventions.

---

## Xem trạng thái project

| Muốn làm gì | File/Lệnh |
|---|---|
| Xem status tất cả data (raw/interim/processed) | `python scripts\project_status.py` → in bảng + lưu `reports/project_status.html` |
| Mở Task Runner (menu tương tác) | `menu.bat` |
| Xem tiến độ toàn dự án (visual) | `reports/project_status.html` — tab "Status" (file checks) · tab "Checklist" (methodology tasks) |
| Xem lịch sử session | `SESSION_LOG.md` (2 entry gần nhất) · `SESSION_LOG_archive.md` (cũ hơn) |
| Xem spec đầy đủ: column list, data requirements | `References/GBPUSD_ML_data_requirements_spec.md` |
| Xem ERD pipeline | `eurusd_data_pipeline_erd.html` |

---

## Fetch dữ liệu thô (cần mạng — chạy trên máy cá nhân)

| Muốn làm gì | File/Lệnh |
|---|---|
| Fetch macro USA (GDP/CPI/rate/current_account) | `run_fred_pipeline.py` → gọi `src/data/fetch_usa_*.py` |
| Fetch macro UK (GDP/CPI/rate/current_account) | `run_fred_pipeline.py` → gọi `src/data/fetch_uk_*.py` |
| Fetch UK CPI từ ONS (alt source) | `src/data/fetch_cpi_uk_alt_wip.py` |
| Fetch UK current account từ ONS | `src/data/fetch_uk_current_account.py` |
| Fetch 13 cặp forex (yfinance/dukascopy) | `run_forex_wip.bat` → `src/data/fetch_forex_wip.py` |
| Fetch 9 equity index (yfinance) | `run_equity_wip.bat` → `src/data/fetch_equity_wip.py` |
| Fetch UK GDP từ ONS (parse manual download) | `src/data/fetch_uk_gdp_ons.py` — parse `UK_gdp_ons_raw.csv` |
| FRED API helpers | `src/data/fred_common.py` |
| Logging/StepLogger | `src/data/pipeline_log_common.py` |

---

## Build interim panels (chạy được trong Cowork, không cần mạng)

| Muốn làm gì | File/Lệnh |
|---|---|
| Build GDP panel → `data/interim/gdp_panel.csv` | `src/features/process_gdp.py` |
| Build CPI panel → `data/interim/cpi_panel.csv` | `src/features/process_cpi.py` |
| Build Central Bank Rate panel → `data/interim/central_bank_rate_panel.csv` | `src/features/process_central_bank_rate.py` |
| Build Current Account panel → `data/interim/current_account_panel.csv` | `src/features/process_current_account.py` |
| Build tất cả macro panels cùng lúc | `src/features/build_macro_panel.py` |
| Build Forex panel → `data/interim/forex_panel.csv` | `src/features/process_forex.py` |
| Build Equity panel → `data/interim/equity_panel.csv` | `src/features/process_equity.py` |
| Panel helpers chung | `src/features/panel_common.py` |

---

## EDA Notebooks (Goal 2)

| Muốn làm gì | File/Lệnh |
|---|---|
| EDA macro indicators (GDP, CPI, rates, CA) | `notebooks/01_eda_macro.ipynb` |
| EDA forex & equity (OHLC, target balance) | `notebooks/02_eda_forex_equity.ipynb` |
| Feature analysis (importance, multicollinearity) | `notebooks/03_feature_analysis.ipynb` |
| Tạo báo cáo HTML tổng kết EDA từ 3 notebooks | `python scripts/generate_eda_report.py --open` |
| Xem báo cáo EDA (3 tabs: Macro · Forex/Equity · Feature Analysis) | `reports/eda_summary.html` — mở trong browser |

---

## Build processed datasets (Phase 3 — chưa có)

| Muốn làm gì | File/Lệnh |
|---|---|
| Dataset 1 — Basic Daily (~130 cols) | **CHƯA CÓ** |
| Dataset 2 — 90-Day Lookback | **CHƯA CÓ** |
| Dataset 3 — Technical Indicators (~2000 cols) | **CHƯA CÓ** |

---

## Model & Evaluation (Phase 4-5 — chưa có)

| Muốn làm gì | File/Lệnh |
|---|---|
| Train models | `src/models/` (scaffold only) |
| Evaluation / backtest | `src/evaluation/` (scaffold only) |
| Xem model đã train | `models/trained/` |
| Xem kết quả hyperparameter search | `models/search_results/` |

---

## Git & Maintenance

| Muốn làm gì | File/Lệnh |
|---|---|
| Push lên git | `push.bat` hoặc `python scripts\auto_push.py` |
| Cập nhật session log | `SESSION_LOG.md` — prepend entry mới, giữ tối đa 2 entry; archive cũ → `SESSION_LOG_archive.md` |
| API keys | `Key/fred_key.txt` (gitignored) · `configs/.env.example` |
| Gotchas khi fetch (ONS/FRED/yfinance) | `References/CLAUDE.md` |
