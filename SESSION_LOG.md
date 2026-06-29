# Session Log — GBP/USD ML Prediction Project

> **Append-only.** Add one new entry at the top of this file each session (most recent on top).
> Goal: reading the 2–3 most recent days is enough to know what's happening, where work stopped, and what comes next.

---

## 2026-06-29 21:00 — Fix notebook 01 errors, create notebook 03

**Branch:** branch_lee

**Done:**

### notebooks/01_eda_macro.ipynb — 3 bugs fixed
- **Bug 1 — statsmodels cascade failure:** `from statsmodels.tsa.stattools import adfuller` was in the shared imports cell; when it raised `ModuleNotFoundError`, `DATA = '../data/interim/'` was never assigned → all downstream cells failed with NameError. Fix: moved statsmodels import into the ADF section cell only, wrapped in `try/except ImportError` with `_statsmodels_ok` flag for graceful degradation.
- **Bug 2 — column filter over-match:** `'value' in c` matched `_value_sqrt` cols; `'yoy' in c` matched `_yoy_days_since_update` and `_yoy_log` cols. Fix: replaced with `c.endswith('_value')` and `c.endswith('_yoy')` throughout the missingness heatmap cell.
- **Bug 3 — pandas 2.x resample API:** `mask.resample('ME').any()` raised `AttributeError: 'DatetimeIndexResampler' object has no attribute 'any'` (removed in pandas 2.x). Fix: replaced with `resample('ME').max()` — equivalent for boolean masks since `max(True, False) = True`.
- Installed `statsmodels 0.14.6` via pip (now available for ADF tests).

### notebooks/02_eda_forex_equity.ipynb — verified clean
- No statsmodels import, no substring column filters, no resample issues. All cells have outputs. No changes needed.

### notebooks/03_feature_analysis.ipynb — created (10 sections)
- Section 1: Load & merge all 6 interim panels into one feature matrix (~130 cols)
- Section 2: Define target (GBP/USD direction, `shift(-1)`)
- Section 3: NaN summary by feature group
- Section 4: Correlation heatmap — macro value/YoY features
- Section 5: Correlation heatmap — forex close returns
- Section 6: Highly correlated pairs (`|r| ≥ 0.85`)
- Section 7: VIF — Variance Inflation Factor (statsmodels, `try/except`)
- Section 8: Random Forest feature importance (sklearn, `try/except`)
- Section 9: Feature clustering dendrogram (scipy, `try/except`)
- Section 10: Key takeaways & selection decisions template
- Applied all 3 notebook rules: optional imports in own cells, `endswith()` for column filters, `.max()` not `.any()` on resampler
- `map.md` updated: removed "CHƯA CÓ" tag for notebook 03

### Memory saved
- `feedback_notebook_import_patterns.md` — 3 rules: (1) optional imports in own `try/except` cell, (2) `endswith()` not `'str' in col`, (3) `resample().max()` not `resample().any()` on pandas 2.x

**Stopped at:** SESSION_LOG update

**Next steps:**
1. Run notebook 03 in JupyterLab, fill in Key Takeaways (sections 01, 02, 03)
2. Begin Goal 3 — build `data/processed/`: start with Dataset 1 Basic Daily (~130 cols)
3. Write `src/features/build_dataset.py` — merge all interim panels, encode date features, add target

---

## 2026-06-29 19:00 — Fix checklist tab % logic

**Branch:** branch_lee

**Done:**

### scripts/project_status.py — checklist tab overall %
- Vấn đề: tab Checklist hiển thị ~21% (đếm checkbox được tick / 19 methodology items) trong khi tab Status hiển thị 73% (file checks) — hai con số đo khác nhau, gây nhầm lẫn
- Đã bỏ thanh Overall dựa trên checkbox count
- Đưa lại thanh Overall nhưng đổi logic: dùng `total_ok / total_countable` từ file checks (cùng nguồn với Status tab)
- `_checklist_tab_html()` nhận thêm 2 param: `total_ok`, `total_countable`
- `generate_html()` truyền 2 param đó vào
- Thanh màu theo ngưỡng: xanh ≥70%, vàng ≥40%, đỏ <40%
- Label đổi thành "Files done: X% (N/M)" để rõ ý nghĩa
- Backup: `scripts/project_status.py.bak`

**Stopped at:** SESSION_LOG update

**Next steps:**
1. Mở JupyterLab (menu option 6), chạy notebook 01 & 02, điền Key Takeaways
2. Tạo `notebooks/03_feature_analysis.ipynb`
3. Goal 3A: build `data/processed/` — Dataset 1 Basic Daily trước

---

## 2026-06-29 17:00 — EDA notebooks, menu.bat Jupyter, scripts/ refactor, checklist tab

**Branch:** branch_lee

**Done:**

### EDA Notebooks (Goal 2)
- Created `notebooks/01_eda_macro.ipynb` — 7 sections: load/overview, missing values heatmap, time series plots (GDP/CPI/rates/current account), ADF stationarity tests, Pearson correlation matrix, release lag distribution, key takeaways template
- Created `notebooks/02_eda_forex_equity.ipynb` — 11 sections: target class balance (~49% UP / ~51% DOWN → no SMOTE), GBP/USD price & returns, OHLC spread ranking, return distribution grid, forex correlation matrix, equity normalised performance, sqrt-volume transform, equity–forex cross-correlation, rolling volatility (Brexit spike annotated)
- `map.md` updated with EDA section

### menu.bat — Jupyter integration
- Added option **6**: `python -m jupyter lab --notebook-dir=notebooks` → opens JupyterLab in browser
- Added option **7**: `python -m jupyter nbconvert --execute --inplace` → runs chosen notebook headless (choice 1/2/3)
- Menu header restructured into DATA / EDA sections

### scripts/ refactor
- Created `scripts/` folder; moved `project_status.py`, `build_index.py`, `run_fred_pipeline.py`, `auto_push.py` from root
- Created `scripts_backup/` with originals (user to delete when ready)
- Fixed `Path(__file__).parent` → `Path(__file__).resolve().parent.parent` in all 4 files (5 occurrences)
- Updated all callers: `menu.bat` (8 refs), `push.bat` (1 ref), `CLAUDE.md` (2 refs), `map.md` (paths + added `menu.bat` entry)

### Checklist tab in project_status.html
- Read `1st_draft_checklist_en.html`, filtered out items already tracked by Phase Details, removed outdated items (Dukascopy, forex volume, PMI, DAX/VIX)
- Added to `scripts/project_status.py`:
  - `_csv_has_column()` helper
  - `DETAILED_CHECKLIST` — 6 stages × 19 items (methodology & procedural)
  - `run_checklist_auto()` — 6 auto-checks from filesystem
  - `_checklist_tab_html()` — generates Checklist tab HTML
  - Tab nav (📊 Status / ✅ Checklist) with localStorage persistence
  - CSS: tab nav, cl-stage, cl-item, auto badge (green)
  - JS: `switchTab()`, `clApplyState()`, localStorage for manual items
- Auto-ticked on run (6/19): FRED key, forex volume exclusion, look-ahead bias guard, class balance (EDA done), equity sqrt, CPI log
- Manual (13/19): bank holidays, stationarity decision, date encoding, PCA, stacking, CV folds, sensitivity analysis, high-vol flagging, rolling re-fit, slides, demo, APA refs
- `map.md`: removed reference to `checklist_en.html`, now points to `reports/project_status.html`
- `1st_draft_checklist_en.html` can be deleted by user

**Stopped at:** SESSION_LOG update

**Next steps:**
1. Run notebooks 01 & 02 in JupyterLab (menu option 6), fill in Key Takeaways sections
2. Create `notebooks/03_feature_analysis.ipynb`
3. Begin Goal 3: build `data/processed/` datasets (start with Dataset 1 — Basic Daily)

---

## 2026-06-29 13:00 — Build forex_panel and equity_panel → Phase 2 complete

**Branch:** branch_lee

**Done:**
- Created `src/features/process_forex.py` → `data/interim/forex_panel.csv`
  - 13 pairs × 4 OHLC cols = 52 columns, 2870 rows, 0 NaN
  - Volume excluded per spec (yfinance FX volume = 0)
  - Aligned to bdate_range via reindex + ffill
- Created `src/features/process_equity.py` → `data/interim/equity_panel.csv`
  - 9 indices × 5 OHLCV cols + 9 sqrt(volume) cols = 54 columns, 2870 rows
  - 1 NaN row on 2014-01-01 (New Year's Day, no trading data — expected, will be dropped during final dataset build)
  - sqrt transform applied to volume columns per spec section 3
- Updated `map.md`: replaced "CHƯA CÓ" placeholders for both scripts
- Phase 2 now 6/6 panels complete
- Overall progress: 65% → 69% (36/52 items OK)

**Stopped at:** SESSION_LOG update

**Next steps:**
1. Begin **Goal 2 — EDA notebooks** (`notebooks/`)
   - `01_eda_macro.ipynb` — macro panel: missing values, stationarity, correlation matrix
   - `02_eda_forex_equity.ipynb` — OHLC distributions, GBP/USD target balance (class imbalance check)
   - `03_feature_analysis.ipynb` — feature importance, multicollinearity

---

## 2026-06-29 12:10 — Remove forex volume from project scope

**Branch:** branch_lee

**Done:**
- **Decision:** forex volume dropped from project scope — yfinance FX volume = 0 (spot FX has no consolidated tape); Dukascopy would provide real tick volume but ~800k requests for 13 pairs × 11 years; OHLC alone is sufficient for the model.
- Updated `References/GBPUSD_ML_data_requirements_spec.md`: forex OHLCV→OHLC, 65→52 cols; indicator rows 3–4 (volume MAs) marked "equity only"; sqrt transform note fixed; worked example forex table and transform examples updated
- Updated `PROJECT_GUIDE.md`: folder comment OHLCV→OHLC; removed dukascopy line from forex pipeline
- Updated `References/CLAUDE.md` item 7: replaced volume trade-off discussion with "decision made, yfinance OHLC is the operative choice"
- Updated `src/data/fetch_forex_wip.py` docstring: removed volume-reliability justification, clarified dukascopy path is kept as WIP reference only

**Stopped at:** session log update

**Next steps (unchanged):**
1. Create `src/features/process_forex.py` → `data/interim/forex_panel.csv` (OHLC only, no volume)
2. Create `src/features/process_equity.py` → `data/interim/equity_panel.csv`
3. Once both panels complete → Phase 2 fully done → begin Goal 2 (EDA notebooks)

---

## 2026-06-29 11:50 — Fill UK macro data gaps, drop Composite PMI

**Branch:** branch_lee

**Done:**

### UK GDP — replaced FRED discontinued series with ONS manual download
- Copied `D:\series-170626.csv` → `data/raw/macro/UK_gdp_ons_raw.csv` (ONS series ABMI, real GDP chained vol. £m, release 2026-05-14)
- Wrote `src/data/fetch_uk_gdp_ons.py` — parses ONS quarterly format, sets `realtime_start = end_of_quarter + 60 days` per row to approximate release lag
- Generated new `UK_gdp.csv`: 48 rows, 2013-01-01 → 2024-10-01 (old FRED version backed up as `UK_gdp.csv.bak`)
- Re-ran `process_gdp.py` → `gdp_panel.csv` rebuilt: UK_gdp_value 2870/2870 rows OK

### UK CPI — swapped in ONS source (replaces FRED series that was 15 months behind)
- `UK_cpi_ons_alt.csv` already fetched via `fetch_cpi_uk_alt_wip.py` (ONS series D7BT, 161 rows through 2026-05)
- Fixed `realtime_start`: was single snapshot 2026-06-16 → recomputed per row as `end_of_month + 42 days`
- Copied processed alt file → `UK_cpi.csv` (old FRED version backed up as `UK_cpi.csv.bak`)
- Re-ran `process_cpi.py` → `cpi_panel.csv` rebuilt: UK columns 2870/2870 rows OK

### UK Current Account — integrated into panel
- `UK_current_account.csv` already fetched via `fetch_uk_current_account.py` (ONS series HBOP, 52 rows)
- Fixed `realtime_start`: was single snapshot 2026-03-30 → recomputed per row as `end_of_quarter + 60 days`
- Re-ran `process_current_account.py` → `current_account_panel.csv` rebuilt: UK columns 2870/2870 rows OK
- Updated `build_macro_panel.py`: added `"current_account"` to UK INDICATORS

### Composite PMI — dropped permanently
- Investigated: S&P Global / CIPS Composite PMI is proprietary — not on FRED
- ISM Manufacturing PMI was removed from FRED by ISM in 2016
- investing.com only shows ~3-4 most recent releases, no historical data
- Scraper confirmed working (`fetch_composite_pmi_wip.py`) but cannot backfill 2014–2024
- **Decision: PMI dropped from project scope.** WIP scripts kept as documentation.
- Removed PMI entries from `project_status.py`, `map.md`, `build_macro_panel.py`

**Goal 1A result:** all 8 items now OK (no WARN, no BLOCKED)

**Stopped at:** SESSION_LOG update

**Next steps:**
1. Create `src/features/process_forex.py` → build `data/interim/forex_panel.csv` from 13 forex CSVs
2. Create `src/features/process_equity.py` → build `data/interim/equity_panel.csv` from 9 equity CSVs
3. Once both panels complete → Phase 2 fully done → begin Goal 2 (EDA notebooks)

---

## 2026-06-29 11:08 — Fix stale memory, remove status tracking, translate docs to English

**Branch:** branch_lee

**Done:**
- Diagnosed why memory was outdated: SESSION_LOG.md was updated each session but `data_status.md` memory and `PROJECT_GUIDE.md` were never synced → caused drift
- Updated memory file `data_status.md` to reflect 2026-06-29 reality (forex/equity have real data, not header-only)
- Removed status percentages/emojis from `CLAUDE.md` (4 goals line) and `PROJECT_GUIDE.md` (goals table + entire "Data Status" section) — SESSION_LOG.md is now the single source of truth for data status
- Translated `PROJECT_GUIDE.md` and `SESSION_LOG.md` fully to English (project is shared with multiple readers)

**Stopped at:** documentation cleanup before closing

**Next steps (unchanged from previous session — high → low priority):**
1. Create `src/features/process_forex.py` → build `data/interim/forex_panel.csv` from 13 forex CSVs
2. Create `src/features/process_equity.py` → build `data/interim/equity_panel.csv` from 9 equity CSVs
3. Decide on UK CPI: swap `UK_cpi_ons_alt.csv` into `process_cpi.py` → rebuild `cpi_panel.csv`
4. Integrate `UK_current_account.csv` into `process_current_account.py` → rebuild `current_account_panel.csv`
5. Find UK GDP alternative source (ONS direct)
6. Once interim is complete → build `data/processed/` (3 dataset variants)
7. Build `src/models/` and `src/evaluation/`

---

## 2026-06-29 10:11 — Status review, update SESSION_LOG, create CLAUDE.md

**Branch:** branch_lee

**project_status.py result (run at 10:11):** Overall 74% — 32/43 items OK

**Changes that happened since the previous log (2026-06-27) but were not recorded:**

### Phase 1B — Forex (complete)
All 13 FX pairs fetched for real via yfinance (`run_forex_wip.bat --source yfinance`):
| Pair | Rows | Coverage |
|---|---|---|
| GBP/USD (target) | 2,866 | 2014-01-01 → 2024-12-30 |
| EUR/USD, AUD/USD, NZD/USD, USD/CAD, USD/CHF, USD/JPY | 2,866 | 2014-01-01 → 2024-12-30 |
| EUR/GBP, GBP/AUD, GBP/CAD, GBP/CHF, GBP/NZD | 2,867 | 2014-01-01 → 2024-12-30 |
| GBP/JPY | 2,867 | 2014-01-01 → 2024-12-30 |

> Note: volume = 0 for all FX pairs on yfinance — known limitation (documented in spec). OHLC is reliable; volume is not usable.

### Phase 1C — Equity (complete)
All 9 equity indices fetched for real via yfinance (`run_equity_wip.bat`):
| Index | Rows | Coverage |
|---|---|---|
| S&P 500, Nasdaq Composite, Nasdaq 100, DJI, Russell 2000 | 2,767 | 2014-01-02 → 2024-12-30 |
| FTSE 100, FTSE 250, FTSE All-Share | 2,777–2,778 | 2014-01-02 → 2024-12-30 |
| FTSE 350 | 2,697 | 2014-01-02 → 2024-12-30 |

### Phase 1A — Macro (unchanged)
- USA: 4 indicators OK
- UK central bank rate: OK
- UK GDP: **WARN** — FRED discontinued Jul-2020, need alternative source
- UK CPI: **WARN** — stale ~15 months; `UK_cpi_ons_alt.csv` (161 rows, ONS) available but not yet swapped into pipeline
- UK Current Account: `UK_current_account.csv` (52 rows, ONS) available but not yet integrated into interim panel
- Composite PMI (USA + UK): **BLOCKED** — no historical source found

### Phase 2 — Interim (partial)
4 macro panels OK (`gdp`, `cpi`, `central_bank_rate`, `current_account` — 2,870 rows each).
Forex panel and Equity panel **not yet built** — highest priority next step.

**Stopped at:** status review + SESSION_LOG update + CLAUDE.md root creation

---

## Template for next session

```
## YYYY-MM-DD HH:MM — [Short summary of what this session did]

**Branch:** branch_lee

**Done:**
- [ ] ...

**Stopped at:**
- ...

**Next steps:**
1. ...
```
