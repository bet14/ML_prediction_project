@echo off
title Project Status — GBP/USD ML
cd /d "%~dp0"
echo.
echo ========================================
echo  GBP/USD ML — Generating Status Report
echo ========================================
echo.
python project_status.py
echo.
echo Opening report in browser...
start "" "reports\project_status.html"
