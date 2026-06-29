@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title GBP/USD ML -- Task Runner

:: ============================================================
::  MENU LOOP
:: ============================================================
:MENU
cls
echo.
echo  +----------------------------------------------+
echo  ^|   GBP/USD ML Prediction  --  Task Runner    ^|
echo  +----------------------------------------------+
echo  ^|                                              ^|
echo  ^|   DATA                                       ^|
echo  ^|   1   Update index + project status          ^|
echo  ^|   2   FRED macro pipeline                    ^|
echo  ^|   3   Fetch equity data  (9 indices)         ^|
echo  ^|   4   Fetch forex data   (13 pairs)          ^|
echo  ^|   5   Git push                               ^|
echo  ^|                                              ^|
echo  ^|   EDA / NOTEBOOKS                            ^|
echo  ^|   6   Open JupyterLab  (notebooks/)          ^|
echo  ^|   7   Run notebook  (nbconvert, no browser)  ^|
echo  ^|                                              ^|
echo  ^|   A   Run all  (see notes below)             ^|
echo  ^|   0   Exit                                   ^|
echo  ^|                                              ^|
echo  +----------------------------------------------+
echo.
echo   Note: options 3 and 4 will ask for extra args.
echo         Add --append to actually write CSV files.
echo.

set "choice="
set /p choice=  Choice:
echo.

if /i "!choice!"=="1" goto TASK_UPDATE
if /i "!choice!"=="2" goto TASK_FRED
if /i "!choice!"=="3" goto TASK_EQUITY
if /i "!choice!"=="4" goto TASK_FOREX
if /i "!choice!"=="5" goto TASK_PUSH
if /i "!choice!"=="6" goto TASK_JUPYTER
if /i "!choice!"=="7" goto TASK_RUN_NB
if /i "!choice!"=="A" goto TASK_ALL
if    "!choice!"=="0" goto EXIT

echo  Unknown option. Try again.
timeout /t 1 /nobreak >nul
goto MENU


:: ============================================================
::  TASK 1 -- Update index + project status
:: ============================================================
:TASK_UPDATE
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo   [1] Update index + project status
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo.
echo  Generating project status report...
python scripts\project_status.py
echo.
echo  Building file index (reads fresh project_status.html)...
python scripts\build_index.py
echo.
echo  Opening index.html in browser...
start "" "index.html"
echo.
pause
goto MENU


:: ============================================================
::  TASK 2 -- FRED macro pipeline
:: ============================================================
:TASK_FRED
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo   [2] FRED macro pipeline
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo.
echo  Common args:
echo    (none)         full fetch + process, all blocks
echo    --skip-fetch   process only (no network)
echo    --block USA    USA block only
echo    --block UK     UK block only
echo.
set "args="
set /p args=  Extra args (Enter = run all):
echo.
python scripts\run_fred_pipeline.py !args!
echo.
pause
goto MENU


:: ============================================================
::  TASK 3 -- Fetch equity data
:: ============================================================
:TASK_EQUITY
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo   [3] Fetch equity data  (9 indices, yfinance)
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo.
echo  Common args:
echo    (none)             dry-run, fetch only, do NOT write
echo    --append           fetch and WRITE CSVs to data/raw/equity/
echo    --index SP500      single index only
echo    --start 2020-01-01 custom start date
echo.
set "args="
set /p args=  Extra args (Enter = dry-run):
echo.
python src\data\fetch_equity_wip.py !args!
echo.
pause
goto MENU


:: ============================================================
::  TASK 4 -- Fetch forex data
:: ============================================================
:TASK_FOREX
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo   [4] Fetch forex data  (13 pairs, yfinance)
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo.
echo  Common args:
echo    (none)             dry-run, fetch only, do NOT write
echo    --append           fetch and WRITE CSVs to data/raw/forex/
echo    --pair GBPUSD      single pair only
echo    --source dukascopy use Dukascopy (heavy, ~800k requests)
echo.
set "args="
set /p args=  Extra args (Enter = dry-run):
echo.
python src\data\fetch_forex_wip.py --source yfinance !args!
echo.
pause
goto MENU


:: ============================================================
::  TASK 5 -- Git push
:: ============================================================
:TASK_PUSH
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo   [5] Git push
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo.
python scripts\auto_push.py
echo.
pause
goto MENU


:: ============================================================
::  TASK 6 -- Open JupyterLab
:: ============================================================
:TASK_JUPYTER
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo   [6] Open JupyterLab  (notebooks/ folder)
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo.
echo  Available notebooks:
echo    01_eda_macro.ipynb          -- macro indicators (GDP, CPI, rates, CA)
echo    02_eda_forex_equity.ipynb   -- forex pairs, equity indices, target var
echo    03_feature_analysis.ipynb   -- feature importance, multicollinearity
echo.
echo  Starting JupyterLab... (Ctrl+C in this window to stop the server)
echo  Browser will open automatically at http://localhost:8888/lab
echo.
python -m jupyter lab --notebook-dir=notebooks
echo.
pause
goto MENU


:: ============================================================
::  TASK 7 -- Run notebook (nbconvert, headless)
:: ============================================================
:TASK_RUN_NB
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo   [7] Run notebook  (nbconvert, no browser)
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo.
echo  Available notebooks:
echo    1  01_eda_macro.ipynb
echo    2  02_eda_forex_equity.ipynb
echo    3  03_feature_analysis.ipynb
echo.
set "nb_choice="
set /p nb_choice=  Which notebook? [1/2/3]:
echo.

if "!nb_choice!"=="1" set "nb_file=01_eda_macro.ipynb"
if "!nb_choice!"=="2" set "nb_file=02_eda_forex_equity.ipynb"
if "!nb_choice!"=="3" set "nb_file=03_feature_analysis.ipynb"

if not defined nb_file (
    echo  Unknown choice. Returning to menu.
    timeout /t 2 /nobreak >nul
    goto MENU
)

echo  Running notebooks\!nb_file! ...
echo  Output saved in-place (cells executed, outputs embedded).
echo.
python -m jupyter nbconvert --to notebook --execute --inplace "notebooks\!nb_file!" --ExecutePreprocessor.timeout=300
echo.
if !errorlevel! equ 0 (
    echo  Done. Open notebooks\!nb_file! in JupyterLab to view results.
) else (
    echo  ERROR: notebook execution failed. Check cell output for details.
)
echo.
pause
goto MENU


:: ============================================================
::  TASK A -- Run all
:: ============================================================
:TASK_ALL
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo   [A] Run all tasks
echo  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
echo.
echo   Step 1 and 2 run fully.
echo   Step 3 and 4 are DRY-RUN (no files written).
echo   To write equity/forex data, run options 3/4
echo   individually with --append.
echo.
set "confirm="
set /p confirm=  Proceed? [Y/N]:
if /i not "!confirm!"=="Y" goto MENU
echo.

echo  --- [1/5] Update index + project status ------
python scripts\build_index.py
python scripts\project_status.py
echo.

echo  --- [2/5] FRED macro pipeline ----------------
python scripts\run_fred_pipeline.py
echo.

echo  --- [3/5] Fetch equity  (dry-run) ------------
python src\data\fetch_equity_wip.py
echo.

echo  --- [4/5] Fetch forex   (dry-run) ------------
python src\data\fetch_forex_wip.py --source yfinance
echo.

echo  --- [5/5] Git push ---------------------------
python scripts\auto_push.py
echo.

echo  ==============================================
echo   All tasks complete.
echo  ==============================================
echo.
start "" "index.html"
pause
goto MENU


:: ============================================================
::  EXIT
:: ============================================================
:EXIT
echo  Goodbye.
echo.
endlocal
exit /b 0
