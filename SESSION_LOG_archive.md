# Session Log — Archive

> Entries older than the 2 most recent sessions are moved here.
> Read this file when looking up history; no need to read regularly.

---

## 2026-06-27 — Split macro fetch scripts per block, add StepLogger

**What was done:**
- Split 4 combined scripts (fetch_gdp/cpi/central_bank_rate/current_account) into 8 separate scripts for USA and UK
- Created `StepLogger` class in `pipeline_log_common.py` — console print + JSON log per script
- Updated `fred_common.py`: added `log_fn` callback so chunk-level messages route through the logger
- Updated `run_fred_pipeline.py`: calls the 8 new scripts, added `--block USA|UK` filter flag
- Promoted `fetch_current_account_uk_wip.py` → `fetch_uk_current_account.py` (removed _wip suffix)
- Saved logging convention to global memory + project memory

**New files created (8 scripts):**
- `src/data/fetch_usa_gdp.py`
- `src/data/fetch_uk_gdp.py`
- `src/data/fetch_usa_cpi.py`
- `src/data/fetch_uk_cpi.py`
- `src/data/fetch_usa_central_bank_rate.py`
- `src/data/fetch_uk_central_bank_rate.py`
- `src/data/fetch_usa_current_account.py`
- `src/data/fetch_uk_current_account.py`

**Files modified:**
- `src/data/pipeline_log_common.py` — added `StepLogger` class
- `src/data/fred_common.py` — added `log_fn` param
- `run_fred_pipeline.py` — refactored to use 8 new scripts, added `--block` flag

**Old scripts (fetch_gdp.py, fetch_cpi.py, fetch_central_bank_rate.py, fetch_current_account.py):**
Still in repo, not deleted, but no longer called by the pipeline.
