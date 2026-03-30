@echo off
setlocal
pushd "%~dp0.."

echo === School Attendance: first setup ===
echo.

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  py -3 -m venv .venv
  if errorlevel 1 goto :fail
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

echo Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 goto :fail

echo Installing Playwright Chromium...
python -m playwright install chromium
if errorlevel 1 goto :fail

if not exist ".env" (
  echo Creating .env from template...
  copy ".env.example" ".env" >nul
  if errorlevel 1 goto :fail
)

if not exist "config\nz_selectors.json" (
  echo Creating nz selectors config from template...
  copy "config\nz_selectors.example.json" "config\nz_selectors.json" >nul
  if errorlevel 1 goto :fail
)

set PYTHONPATH=src

echo.
echo Setup complete.
echo If needed, review .env and config\nz_selectors.json after this step.
echo Browser login will open now to save session state.
echo.

python -m school_attendance.cli bootstrap-session --timeout-seconds 300
set EXIT_CODE=%ERRORLEVEL%

popd
echo.
pause
exit /b %EXIT_CODE%

:fail
set EXIT_CODE=%ERRORLEVEL%
echo.
echo First setup failed with code %EXIT_CODE%.
popd
echo.
pause
exit /b %EXIT_CODE%
