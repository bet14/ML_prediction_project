# Session Log — GBP/USD ML Prediction Project

> **Append-only.** Mỗi session thêm 1 entry mới vào đầu file (mới nhất ở trên cùng).
> Mục đích: đọc 2-3 entry gần nhất là biết ngay đang làm gì, dừng ở đâu, bước tiếp theo là gì.

---

## 2026-06-29 — Review trạng thái, cập nhật SESSION_LOG, tạo CLAUDE.md

**Branch:** branch_lee

**project_status.py kết quả (chạy lúc 10:11):** Overall 74% — 32/43 items OK

**Những thay đổi đã xảy ra từ log trước (2026-06-27) nhưng chưa được ghi:**

### Phase 1B — Forex (hoàn tất)
Tất cả 13 cặp FX đã fetch thật bằng yfinance (`run_forex_wip.bat --source yfinance`):
| Pair | Rows | Coverage |
|---|---|---|
| GBP/USD (target) | 2,866 | 2014-01-01 → 2024-12-30 |
| EUR/USD, AUD/USD, NZD/USD, USD/CAD, USD/CHF, USD/JPY | 2,866 | 2014-01-01 → 2024-12-30 |
| EUR/GBP, GBP/AUD, GBP/CAD, GBP/CHF, GBP/NZD | 2,867 | 2014-01-01 → 2024-12-30 |
| GBP/JPY | 2,867 | 2014-01-01 → 2024-12-30 |

> Lưu ý: volume = 0 cho tất cả cặp FX trên yfinance — đây là giới hạn đã biết của nguồn này (ghi trong spec). OHLC tin được, volume không dùng được.

### Phase 1C — Equity (hoàn tất)
Tất cả 9 equity index đã fetch thật bằng yfinance (`run_equity_wip.bat`):
| Index | Rows | Coverage |
|---|---|---|
| S&P 500, Nasdaq Composite, Nasdaq 100, DJI, Russell 2000 | 2,767 | 2014-01-02 → 2024-12-30 |
| FTSE 100, FTSE 250, FTSE All-Share | 2,777–2,778 | 2014-01-02 → 2024-12-30 |
| FTSE 350 | 2,697 | 2014-01-02 → 2024-12-30 |

### Phase 1A — Macro (không đổi)
- USA: 4 indicators OK
- UK central bank rate: OK
- UK GDP: **WARN** — FRED discontinued Jul-2020, cần nguồn thay thế
- UK CPI: **WARN** — stale ~15 tháng; `UK_cpi_ons_alt.csv` (161 rows, ONS) đã có nhưng chưa swap vào pipeline
- UK Current Account: `UK_current_account.csv` (52 rows, ONS) đã có nhưng chưa tích hợp vào interim panel
- Composite PMI (USA + UK): **BLOCKED** — không có nguồn historical

### Phase 2 — Interim (một phần)
4 macro panels OK (`gdp`, `cpi`, `central_bank_rate`, `current_account` — mỗi panel 2,870 rows).
Forex panel và Equity panel **chưa có** — đây là bước tiếp theo ưu tiên cao nhất.

**Dừng ở:** review trạng thái + cập nhật SESSION_LOG + tạo CLAUDE.md root

**Bước tiếp theo (ưu tiên cao → thấp):**
1. Tạo `src/data/process_forex.py` → build `data/interim/forex_panel.csv` từ 13 forex CSVs
2. Tạo `src/data/process_equity.py` → build `data/interim/equity_panel.csv` từ 9 equity CSVs
3. Quyết định UK CPI: swap `UK_cpi_ons_alt.csv` vào `process_cpi.py` → rebuild `cpi_panel.csv`
4. Tích hợp `UK_current_account.csv` vào `process_current_account.py` → rebuild `current_account_panel.csv`
5. Tìm nguồn UK GDP thay thế (ONS trực tiếp)
6. Sau khi interim đủ → build `data/processed/` (3 dataset variants)
7. Xây dựng `src/models/` và `src/evaluation/`

---

## 2026-06-27 — Tách macro fetch scripts thành per-block, thêm StepLogger

**Session này làm gì:**
- Tách 4 combined scripts (fetch_gdp/cpi/central_bank_rate/current_account) thành 8 scripts riêng cho USA và UK
- Tạo `StepLogger` class trong `pipeline_log_common.py` — console print + JSON log per script
- Cập nhật `fred_common.py`: thêm `log_fn` callback để chunk-level messages đi qua logger
- Cập nhật `run_fred_pipeline.py`: gọi 8 scripts mới, thêm `--block USA|UK` filter flag
- Promote `fetch_current_account_uk_wip.py` → `fetch_uk_current_account.py` (bỏ _wip suffix)
- Lưu logging convention vào global memory + project memory

**Files mới tạo (8 scripts):**
- `src/data/fetch_usa_gdp.py`
- `src/data/fetch_uk_gdp.py`
- `src/data/fetch_usa_cpi.py`
- `src/data/fetch_uk_cpi.py`
- `src/data/fetch_usa_central_bank_rate.py`
- `src/data/fetch_uk_central_bank_rate.py`
- `src/data/fetch_usa_current_account.py`
- `src/data/fetch_uk_current_account.py`

**Files chỉnh sửa:**
- `src/data/pipeline_log_common.py` — thêm `StepLogger` class
- `src/data/fred_common.py` — thêm `log_fn` param
- `run_fred_pipeline.py` — refactor dùng 8 scripts mới, thêm `--block` flag

**Script cũ (fetch_gdp.py, fetch_cpi.py, fetch_central_bank_rate.py, fetch_current_account.py):**
Vẫn còn trong repo, không bị xóa, nhưng không còn được gọi bởi pipeline.

---

## Template cho session tiếp theo

```
## YYYY-MM-DD — [Tóm tắt ngắn session này làm gì]

**Branch:** branch_lee

**Đã làm:**
- [ ] ...

**Dừng ở:**
- ...

**Bước tiếp theo:**
1. ...
```
