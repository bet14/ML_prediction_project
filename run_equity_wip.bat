@echo off
cd /d %~dp0
python src\data\fetch_equity_wip.py %*
pause
