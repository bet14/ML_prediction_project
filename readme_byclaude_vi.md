# Dự án Dự đoán Hướng GBP/USD (Machine Learning)

Dự án dự đoán hướng giá GBP/USD ngày kế tiếp (tăng/giảm) sử dụng các mô hình ensemble
(XGBoost, LightGBM, CatBoost + meta-stacking). Đặc trưng gồm các chỉ số macro UK/US
(GDP, CPI, lãi suất, tài khoản vãng lai, PMI), 13 cặp tiền tệ tương quan, và các chỉ
số kỹ thuật. Phát triển dựa trên phương pháp của Guyard & Deriaz (2024) với cửa sổ thời
gian rộng hơn và cập nhật hơn.

Phương pháp đầy đủ: `working_plan.html` (mở bằng trình duyệt).
Theo dõi tiến độ: `checklist.html` (tiếng Việt) / `checklist_en.html` (tiếng Anh).
Đặc tả dữ liệu: `References/GBPUSD_ML_data_requirements_spec.md`.

---

## Khởi động nhanh

**Yêu cầu:** Python ≥ 3.9 (code dùng cú pháp `list[dict]`), các package trong `requirements.txt`.

```bash
# Cài đặt trên máy cá nhân — KHÔNG chạy trong Cowork sandbox (không có internet)
pip install -r requirements.txt

# Chạy full macro pipeline (cần internet để gọi FRED API)
python run_fred_pipeline.py --start 2014-01-01 --end 2024-12-31

# Chỉ chạy lại processing (raw CSVs đã có, không cần internet)
python run_fred_pipeline.py --skip-fetch --start 2014-01-01 --end 2024-12-31

# Kiểm tra series IDs mà không fetch hay process
python run_fred_pipeline.py --verify-only
```

Sau khi có raw CSVs, chạy các script WIP cho forex và equity trên máy cá nhân:
```bash
run_forex_wip.bat --pair GBPUSD --source yfinance
run_equity_wip.bat --index FTAS --append
```

---

## Cửa sổ thu thập dữ liệu

**Tất cả dữ liệu thô được thu thập cho giai đoạn 2014-01-01 → 2024-12-31** (≈ 11 năm dữ liệu ngày).

> **Lưu ý về `--end`:** `--start` mặc định là `2014-01-01` (cố định). `--end` mặc định là
> `None` — nếu không truyền, pipeline sẽ fetch đến ngày hiện tại. Luôn truyền `--end`
> tường minh để đảm bảo tái lập được kết quả:

```
python run_fred_pipeline.py --start 2014-01-01 --end 2024-12-31
```

(`src/features/build_macro_panel.py` là script tổng hợp cũ hơn — không được gọi bởi
`run_fred_pipeline.py` hay bất kỳ thứ gì khác; xem bảng `src/features/` bên dưới.)

Ghi chú về cửa sổ thời gian:

- Bài báo gốc (Guyard & Deriaz, 2024) dùng 2013-04-30 → 2022-12-31. Cửa sổ 2014→2024
  ở đây rộng hơn và cập nhật hơn, bao gồm Brexit, COVID, và chu kỳ tăng lãi suất 2022–2023.
- FRED API trả về mọi bản sửa đổi đến ngày gọi, nên một số CSV thô có các dòng sau năm 2024
  (ví dụ `USA_central_bank_rate.csv` chạy đến giữa 2026). Cửa sổ mô hình vẫn là 2014→2024
  và bước build panel sẽ cắt bớt theo `--end`.
- Series ngày (Fed Funds Rate) có một dòng mỗi ngày lịch; series quý/tháng (GDP, CPI,
  tài khoản vãng lai) có một dòng mỗi lần công bố. `realtime_start` ghi lại ngày công bố
  thực tế — dùng để forward-fill không có look-ahead bias.

---

## Trạng thái dự án (tính đến 2026-06-26)

| Tầng dữ liệu | Trạng thái |
|---|---|
| Dữ liệu macro thô (FRED) | Phần lớn OK — xem bảng macro bên dưới |
| Macro panels (`data/interim/`) | 4/5 panels đã build (thiếu `composite_pmi_panel`) |
| Dữ liệu forex thô | 13 CSVs placeholder (header-only) — chưa fetch |
| Dữ liệu equity thô | 9 CSVs placeholder (header-only) — chưa fetch |
| Dataset huấn luyện (`data/processed/`) | Chưa build |
| Huấn luyện mô hình | Chưa bắt đầu |
| Streamlit app | Chưa bắt đầu |

---

## Cấu trúc thư mục & danh sách file

```
ML_prediction_project/
├── data/
│   ├── raw/            # Dữ liệu thô, tải về nguyên trạng, không chỉnh tay
│   │   ├── forex/      # GBP/USD OHLCV + các cặp FX tương quan (Dukascopy)
│   │   ├── macro/      # Các chỉ số macro UK/US (FRED, ONS)
│   │   └── equity/     # Chỉ số chứng khoán (yfinance)
│   ├── interim/        # Macro panels theo từng chỉ số, ghép theo ngày
│   └── processed/      # 3 biến thể dataset cuối cho huấn luyện
├── notebooks/          # Notebooks khám phá, EDA (đánh số: 01_eda.ipynb, 02_...)
├── src/                # Code module, có thể import — không phải notebook
│   ├── data/           # Fetch scripts FRED (mỗi chỉ số một file) + helpers dùng chung
│   ├── features/       # Build macro panel + xử lý/biến đổi từng chỉ số
│   ├── models/         # Huấn luyện, Bayesian hyperparameter search, meta-stacking (chưa build)
│   ├── evaluation/     # Metrics, walk-forward CV, backtest (chưa build)
│   └── app/            # Giao diện Streamlit (chưa build)
├── models/
│   ├── trained/        # Mô hình đã huấn luyện (.joblib/.pkl)
│   └── search_results/ # Log/kết quả Bayesian search theo fold
├── reports/
│   ├── macro_data_status.html  # Dashboard trực tiếp: kiểm kê file, lỗi, nghiên cứu API thay thế
│   ├── forex_data_status.html  # Tương tự cho data/raw/forex/
│   ├── equity_data_status.html # Tương tự cho data/raw/equity/
│   ├── pipeline_run_log.jsonl  # Một dòng JSON cho mỗi lần chạy pipeline
│   ├── figures/        # Biểu đồ (feature importance, backtest, ...)
│   └── tables/         # Bảng kết quả (model_comparison.csv, ...)
├── configs/            # .env.example, config — không commit key thật
├── Key/                # fred_key.txt (FRED API key, gitignored)
├── References/         # Papers (PDFs), đặc tả dữ liệu, CLAUDE.md
├── run_fred_pipeline.py    # Pipeline driver chính (macro)
├── run_fred_pipeline.bat   # Batch wrapper
├── run_equity_wip.bat      # Wrapper cho fetch_equity_wip.py
├── run_forex_wip.bat       # Wrapper cho fetch_forex_wip.py
├── auto_push.py            # git add/commit/push + rebuild index.html
├── push.bat                # Batch wrapper cho auto_push.py
├── eurusd_data_pipeline_erd.html  # Sơ đồ ERD của data pipeline
├── working_plan.html
├── checklist.html / checklist_en.html
├── index.html          # Gallery deliverables (tự động tạo)
└── requirements.txt
```

### `data/raw/forex/` — Forex OHLCV (Dukascopy hoặc yfinance)

**13 CSVs placeholder chỉ có header** (`AUD_USD.csv`, `EUR_USD.csv`, `EUR_GBP.csv`,
`GBP_AUD.csv`, `GBP_CAD.csv`, `GBP_CHF.csv`, `GBP_JPY.csv`, `GBP_NZD.csv`, `GBP_USD.csv`,
`NZD_USD.csv`, `USD_CAD.csv`, `USD_CHF.csv`, `USD_JPY.csv` — cột `date, open, high, low,
close, volume`) được tạo ngày 2026-06-19. Chưa fetch dữ liệu — chạy `src/data/fetch_forex_wip.py`
trên máy cá nhân để điền dữ liệu. File `.gitkeep` vẫn còn tồn tại song song với các CSVs
(giữ cho thư mục được track bởi git nếu CSVs bị gitignore sau này).

GBP/USD vừa là nguồn đặc trưng vừa là **biến mục tiêu** (hướng close ngày kế tiếp). Mọi
cặp có liên quan đến GBP hoặc USD đều được đưa vào vì chúng có cùng driver macro và tương quan cao.

Spec (mục 7) khuyên dùng Dukascopy, nhưng đây là dữ liệu tick (một file nén mỗi giờ mỗi cặp —
backfill đầy đủ 13 cặp/11 năm cần ~800k-900k requests) và phải tổng hợp sang daily ở client;
yfinance nhẹ hơn nhiều nhưng volume FX trên Yahoo được báo cáo rộng rãi là không đáng tin.
`fetch_forex_wip.py` hỗ trợ cả hai qua `--source dukascopy|yfinance` — xem docstring và
`reports/forex_data_status.html` để biết đầy đủ ưu nhược điểm. Chưa chạy end-to-end.

### `data/raw/macro/` — Chỉ số macro (FRED / ONS)

Mỗi CSV là lịch sử công bố với các cột `date, realtime_start, value`.

| File | Khối | Chỉ số | Tần suất | Dòng | Phủ | Trạng thái |
|---|---|---|---|---|---|---|
| `USA_gdp.csv` | USA | GDP | Quý | 459 | 2014-01-01 → 2026-01-01 | OK |
| `USA_cpi.csv` | USA | CPI (mức chỉ số) | Tháng | 1012 | 2014-01-01 → 2026-05-01 | OK |
| `USA_central_bank_rate.csv` | USA | Fed Funds Rate | Ngày | 12609 | 2014-01-01 → 2026-06-17 | OK |
| `USA_current_account.csv` | USA | Tài khoản vãng lai | Quý | 409 | 2014-01-01 → 2025-10-01 | OK |
| `UK_gdp.csv` | UK | GDP | Quý | 274 | 2014-01-01 → 2020-07-01 | CŨ — nguồn Eurostat bị ngừng |
| `UK_cpi.csv` | UK | CPI (mức chỉ số) | Tháng | 587 | 2014-04-01 → 2025-03-01 | CŨ — chậm ~15 tháng so với USA |
| `UK_central_bank_rate.csv` | UK | BoE Bank Rate | Tháng | 499 | 2014-08-01 → 2026-05-01 | OK |
| `UK_current_account.csv` | UK | Tài khoản vãng lai | Quý | — | — | THIẾU — script ONS đã xác minh, chưa chạy |
| `USA_composite_pmi.csv` | USA | Composite PMI | — | — | — | THIẾU — không có trên FRED |
| `UK_composite_pmi.csv` | UK | Composite PMI | — | — | — | THIẾU — không có trên FRED |

Các vấn đề quan trọng:

- **UK GDP — cũ, không thể fix bằng re-fetch:** Series FRED `CLVMNACSCAB1GQUK` dừng ở
  2020-07-01 vì nguồn Eurostat bị ngừng cung cấp.
- **UK CPI — cũ:** Chậm ~15 tháng so với file USA. ONS v0 API đã nghỉ hưu; script thay thế
  dùng ONS v1 beta. `fetch_cpi_uk_alt_wip.py` ghi ra `UK_cpi_ons_alt.csv` (file riêng biệt,
  không ghi đè `UK_cpi.csv`) — xem docstring trước khi hoán đổi.
- **UK tài khoản vãng lai — không có trên FRED:** Series ONS `HBOP` (dataset `pnbp`) là
  nguồn thay thế; schema đã xác minh ngày 2026-06-19, chưa chạy.
- **Composite PMI — thiếu cho cả USA lẫn UK:** Bị xóa khỏi FRED từ tháng 6/2016. Scraper
  investing.com trong `fetch_composite_pmi_wip.py` chỉ giữ ~3-4 lần công bố gần nhất — đây
  là công cụ cập nhật tăng dần, không thể backfill 2014-2024. Xem docstring để biết quy
  trình thủ công cần thiết để xây dựng dữ liệu lịch sử.

Để xem snapshot kiểm kê file trực tiếp, mở `reports/macro_data_status.html` trong trình duyệt.

### `data/raw/equity/` — Chỉ số chứng khoán (yfinance)

**9 CSVs placeholder chỉ có header** được tạo ngày 2026-06-19 (cột `date, open, high, low, close, volume`).
Chưa fetch — chạy `src/data/fetch_equity_wip.py` trên máy cá nhân. File `.gitkeep` vẫn còn.
Theo đặc tả dữ liệu (mục 2.2):

```
US:  USA_DJI.csv (^DJI), USA_NASDAQ_COMPOSITE.csv (^IXIC), USA_NASDAQ100.csv (^NDX),
     USA_RUSSELL2000.csv (^RUT), USA_SP500.csv (^GSPC)
UK:  UK_FTSE100.csv (^FTSE), UK_FTSE250.csv (^FTMC), UK_FTSE350.csv (^FTLC),
     UK_FTSE_ALL_SHARE.csv (^FTAS)
```

`^FTAS` (FTSE All-Share) có độ tin cậy thấp nhất — kiểm tra cái này trước. Xem
`reports/equity_data_status.html` để biết bảng độ tin cậy đầy đủ.

### `data/interim/` — Macro panels đã ghép

Panels được index theo ngày làm việc (một dòng mỗi ngày, 2014→…, ~3.254 dòng mỗi file):

| File | Các cột chính |
|---|---|
| `central_bank_rate_panel.csv` | Lãi suất USA/UK + days_since_update + `*_value_sqrt` |
| `cpi_panel.csv` | CPI USA/UK + days_since_update + `*_cpi_yoy` + `UK_cpi_yoy_log` |
| `current_account_panel.csv` | Tài khoản vãng lai USA + days_since_update |
| `gdp_panel.csv` | GDP USA/UK + days_since_update |

`composite_pmi_panel.csv` sẽ được thêm khi có raw CSV cho ít nhất một khối.
Đây là kết quả trung gian (để debug pipeline), không phải ma trận huấn luyện cuối cùng.

### `data/processed/` — Dataset huấn luyện cuối

Placeholder (`.gitkeep`). Ba biến thể sẽ được build (spec mục 3):

- **Dataset 1 — Basic Daily:** macro panel + OHLCV index/forex, mã hóa ngày.
- **Dataset 2 — 90-Day Lookback:** Dataset 1 + mỗi đặc trưng trễ 90 ngày.
- **Dataset 3 — Technical Indicators:** Dataset 1 + 16 họ chỉ số kỹ thuật (~2.000 cột,
  chọn lọc bằng Bayesian feature selection).

### `src/data/` — Fetch scripts (cần internet; chạy ngoài Cowork)

| File | Vai trò |
|---|---|
| `fred_common.py` | FRED client dùng chung + paths |
| `fetch_fred.py` | Fetch một series đơn lẻ — công cụ tra cứu thủ công, không dùng trong pipeline |
| `fetch_gdp.py` | Fetch lịch sử công bố GDP USA/UK |
| `fetch_cpi.py` | Fetch lịch sử công bố CPI USA/UK |
| `fetch_central_bank_rate.py` | Fetch Fed Funds Rate / BoE Bank Rate |
| `fetch_current_account.py` | Fetch tài khoản vãng lai USA (UK cố ý bỏ qua — xem docstring) |
| `fetch_current_account_uk_wip.py` | **WIP** — Tài khoản vãng lai UK từ ONS v1 beta API; schema xác minh 2026-06-19 |
| `fetch_cpi_uk_alt_wip.py` | **WIP** — CPI UK thay thế từ ONS v1 beta; ghi ra `UK_cpi_ons_alt.csv` |
| `fetch_composite_pmi_wip.py` | **WIP** — Scraper investing.com; chỉ cập nhật tăng dần, không backfill |
| `fetch_forex_wip.py` | **WIP** — 13 cặp forex, `--source dukascopy|yfinance`; chưa chạy |
| `fetch_equity_wip.py` | **WIP** — 9 chỉ số via yfinance; chưa chạy |
| `pipeline_log_common.py` | Helpers logging dùng chung (`append_run_log`, `run_script`) |
| `__init__.py` | Package marker |

### `src/features/` — Build panel & biến đổi (pandas thuần; chạy được trong Cowork)

| File | Vai trò |
|---|---|
| `build_macro_panel.py` | **Không dùng** — script tổng hợp cũ, không được gọi bởi pipeline nào |
| `panel_common.py` | Helpers panel dùng chung |
| `process_gdp.py` | → `data/interim/gdp_panel.csv` |
| `process_cpi.py` | → `cpi_panel.csv` (thêm CPI YoY, log transform) |
| `process_central_bank_rate.py` | → `central_bank_rate_panel.csv` (sqrt transform) |
| `process_current_account.py` | → `current_account_panel.csv` (chỉ USA cho đến khi có CSV UK) |
| `process_composite_pmi.py` | **WIP** — thoát không ghi gì cho đến khi có raw CSV |
| `__init__.py` | Package marker |

`src/models/` và `src/evaluation/` đã scaffold (có `__init__.py` rỗng), chưa build.
`src/app/` chỉ có `.gitkeep` (chưa có `__init__.py`).

### Scripts & file ở thư mục gốc

| File | Vai trò |
|---|---|
| `run_fred_pipeline.py` / `run_fred_pipeline.bat` | Driver pipeline macro. `--start` mặc định `2014-01-01`; `--end` mặc định `None` (fetch đến hôm nay) — luôn truyền `--end` tường minh |
| `auto_push.py` / `push.bat` | git add/commit/push + rebuild `index.html` (chỉ trên máy cá nhân) |
| `index.html` | Gallery deliverables (tự động tạo) |
| `eurusd_data_pipeline_erd.html` | Sơ đồ ERD của data pipeline |
| `requirements.txt` | Phụ thuộc Python (cần Python ≥ 3.9) |
| `run_equity_wip.bat` | Wrapper cho `fetch_equity_wip.py`; truyền qua mọi argument |
| `run_forex_wip.bat` | Wrapper cho `fetch_forex_wip.py`; truyền qua mọi argument |

### `reports/`

| File | Vai trò |
|---|---|
| `macro_data_status.html` | Dashboard trực tiếp — kiểm kê raw/interim, lỗi, nghiên cứu ONS/PMI |
| `forex_data_status.html` | Kiểm kê 13 cặp placeholder + so sánh Dukascopy vs yfinance |
| `equity_data_status.html` | Kiểm kê 9 chỉ số placeholder + bảng độ tin cậy |
| `pipeline_run_log.jsonl` | Log append-only; được tạo khi chạy pipeline lần đầu |
| `README.md` | Mô tả ngắn về thư mục reports |
| `figures/`, `tables/` | Trống cho đến khi huấn luyện mô hình |

### `References/`

11 bài báo PDF (`01_…`–`11_…`), `GBPUSD_ML_data_requirements_spec.md`,
`eurusd-forex-prediction.html`, và `CLAUDE.md`.

### `configs/` & `Key/`

`configs/.env.example` (copy thành `.env`; chứa `FRED_API_KEY`, tùy chọn `ONS_API_KEY`).
`Key/fred_key.txt` chứa FRED API key (gitignored).

---

## Lưu ý quan trọng (môi trường thực thi)

Cowork sandbox không có internet — không gọi được FRED/ONS/Dukascopy/yfinance, không `pip install`
được. Vì vậy:

- **Thu thập dữ liệu** (`src/data/`) phải chạy trên máy cá nhân, Colab, hoặc Kaggle. Copy
  kết quả dưới dạng CSV vào `data/raw/`.
- **Xử lý và huấn luyện** (`src/features/`, `src/models/`) chạy ổn trong Cowork khi đã có
  raw CSVs — không cần internet.
- **`auto_push.py`/`push.bat`** cần SSH key cá nhân; chỉ chạy trên máy cá nhân.

---

## Ghi chú về `auto_push.py`

Script chỉ scan file trực tiếp trong `References/`, `data/`, `notebooks/`, `models/`, `reports/`
(không đệ quy) để build `index.html`. File trong các thư mục con như `data/raw/forex/` hay
`models/trained/` sẽ không xuất hiện trong gallery — đây là hạn chế đã biết, không phải lỗi.

---

## requirements.txt

**Cần Python ≥ 3.9.** Chỉ cài và chạy trên máy cá nhân/Colab.

> Comment trong `requirements.txt` cho `yfinance` có đề cập "DAX, VIX" — các ticker này
> **không** nằm trong data plan hiện tại. Chỉ 9 chỉ số trong `data/raw/equity/` là trong
> phạm vi. Comment đó đã lỗi thời, có thể bỏ qua.

---

## Tổng hợp các điểm chỉnh sửa so với README gốc

| # | README gốc | Đã sửa |
|---|---|---|
| 1 | Cây thư mục thiếu `run_fred_pipeline.py/.bat`, `auto_push.py`, `push.bat`, `eurusd_data_pipeline_erd.html` | Đã bổ sung đầy đủ |
| 2 | Nói CSVs forex/equity "replacing" `.gitkeep` — nhưng `.gitkeep` vẫn còn | Làm rõ: `.gitkeep` vẫn tồn tại, cố ý |
| 3 | `src/app/` được mô tả có `__init__.py` + `.gitkeep` | `src/app/` chỉ có `.gitkeep`; chưa có `__init__.py` |
| 4 | `--end` mô tả là "hard-wired" | Chỉ `--start` là cố định; `--end` mặc định `None` |
| 5 | `reports/README.md` không được nhắc đến | Đã thêm vào bảng reports |
| 6 | Thiếu mô tả dự án, Quick Start, Project Status | Đã thêm cả 3 section |
| 7 | Không đề cập Python version | Đã ghi rõ: cần Python ≥ 3.9 |
| 8 | Comment trong `requirements.txt` đề cập DAX/VIX (không có trong data plan) | Đã ghi chú là lỗi thời |
