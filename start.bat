@echo off
cd /d "%~dp0"
python -c "import flask, waitress" >nul 2>&1
if errorlevel 1 (
    echo Installing app dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        pause
        exit /b 1
    )
)
set PORT=8000
echo Open http://127.0.0.1:8000 in your browser.
echo Keep this window open while using the app.
python run.py
pause
