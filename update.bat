@echo off
title Update — GBP/USD ML Project
cd /d "%~dp0"
echo.
echo  [1/2] Building file index...
python build_index.py
echo.
echo  [2/2] Updating project status...
python project_status.py
echo.
echo  Opening index.html in browser...
start "" "index.html"
echo  Done.
