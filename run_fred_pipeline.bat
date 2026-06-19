@echo off
cd /d %~dp0
python run_fred_pipeline.py %*
pause
