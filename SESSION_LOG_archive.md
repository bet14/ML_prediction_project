# Session Log — Archive

> Entries cũ hơn 2 session gần nhất được chuyển vào đây.
> Đọc file này khi cần tra cứu lịch sử, không cần đọc thường xuyên.

---

## 2026-06-27 — Tạo PROJECT_GUIDE + SESSION_LOG

**Session này làm gì:**
- Đọc hiểu toàn bộ cấu trúc project, trạng thái dữ liệu, script hiện có
- Tạo `PROJECT_GUIDE.md` (hướng dẫn folder + conventions)
- Tạo `SESSION_LOG.md` (file này)
- Lưu memory vào Claude Code memory system

**Branch đang làm việc:** `branch_lee`

**Tổng quan trạng thái hiện tại:**

### Dữ liệu đã có (committed hoặc untracked):
- [x] USA macro 4 indicators: GDP, CPI, central bank rate, current account — OK, trong `data/raw/macro/`
- [x] UK central bank rate — OK
- [x] `data/interim/` — 4 panel CSV: gdp, cpi, central_bank_rate, current_account (USA only trong current_account)
- [x] `UK_cpi_ons_alt.csv` — 161 rows từ ONS v1 beta API (untracked, chưa committed)
- [x] `UK_current_account.csv` — 52 rows từ ONS v1 beta API (untracked, chưa committed)

### Dữ liệu header-only (chưa có data thật):
- [ ] `data/raw/equity/*.csv` — 9 file, mỗi file 1 dòng header (dry-run 2026-06-26 ok nhưng không ghi file)
- [ ] `data/raw/forex/*.csv` — 13 file, mỗi file 1 dòng header (chưa fetch lần nào)

### Vấn đề còn mở:
- [ ] **UK GDP**: FRED series `CLVMNACSCAB1GQUK` discontinued từ 2020-07. Cần nguồn thay thế (ONS trực tiếp). Chưa có giải pháp.
- [ ] **UK CPI**: `UK_cpi.csv` hiện tại stale ~15 tháng. `UK_cpi_ons_alt.csv` đã fetch nhưng format/series khác `UK_cpi.csv` — xem docstring `fetch_cpi_uk_alt_wip.py` trước khi swap.
- [ ] **Composite PMI (USA + UK)**: Không có trên FRED. investing.com chỉ giữ ~3-4 release gần nhất. Cần tìm nguồn historical data thủ công cho 2014-2024. `fetch_composite_pmi_wip.py` chỉ dùng được làm incremental updater.

### Script _wip đã có nhưng chưa chạy thật:
| Script | STATUS |
|---|---|
| `src/data/fetch_cpi_uk_alt_wip.py` | Schema ONS verified 2026-06-19, đã chạy → `UK_cpi_ons_alt.csv` (161 rows) |
| `src/data/fetch_current_account_uk_wip.py` | Schema ONS verified 2026-06-19, đã chạy → `UK_current_account.csv` (52 rows) |
| `src/data/fetch_composite_pmi_wip.py` | Scraper verified 2026-06-19, CHỈ lấy được ~3-4 release gần nhất |
| `src/data/fetch_forex_wip.py` | Chưa chạy lần nào — cần mạng, cần chọn `--source dukascopy\|yfinance` |
| `src/data/fetch_equity_wip.py` | Dry-run OK 2026-06-26 (yfinance, 2767-2778 rows/index) — cần chạy thật để ghi file |

**Bước tiếp theo (ưu tiên cao → thấp):**
1. Chạy `run_equity_wip.bat` (không có `--dry-run`) trên máy cá nhân → ghi 9 equity CSVs
2. Quyết định forex source (yfinance vs Dukascopy) → chạy `run_forex_wip.bat` → ghi 13 forex CSVs
3. Xử lý UK CPI: quyết định có dùng `UK_cpi_ons_alt.csv` thay `UK_cpi.csv` không → cập nhật `process_cpi.py`
4. Cập nhật `process_current_account.py` để tích hợp `UK_current_account.csv` mới vào panel
5. Tìm nguồn Composite PMI lịch sử 2014-2024 (thủ công nếu cần)
6. Sau khi có đủ raw data → build `data/processed/` (3 dataset variants)
7. Xây dựng `src/models/` và `src/evaluation/`
