@echo off
REM Launches the Streamlit app (src/app/app.py) and opens it in the default browser.
REM Usage: double-click this file, or run it from a terminal.

cd /d %~dp0

echo Starting Streamlit app...
echo Project root: %cd%

streamlit run src\app\app.py

pause
