@echo off
cd /d %~dp0
python scripts\auto_push.py %*
pause
