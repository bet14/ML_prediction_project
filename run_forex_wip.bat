@echo off
cd /d %~dp0
python src\data\fetch_forex_wip.py %*
pause
