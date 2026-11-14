@echo off
cd /d "%~dp0"
python -c "import flask, waitress" >nul 2>&1
if errorlevel 1 (
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
python launch_mobile.py
pause
