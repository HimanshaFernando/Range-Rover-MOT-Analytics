@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 goto failed
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe scripts\pipeline.py
if errorlevel 1 goto failed
.venv\Scripts\python.exe scripts\build_report.py
if errorlevel 1 goto failed
.venv\Scripts\python.exe scripts\briefing.py
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 goto failed
echo Rebuild complete.
pause
exit /b 0
:failed
echo Rebuild stopped. See the error above.
pause
exit /b 1
