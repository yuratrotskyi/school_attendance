@echo off
setlocal
pushd "%~dp0.."

if not exist ".venv\Scripts\activate.bat" (
  echo Virtual environment not found: .venv\Scripts\activate.bat
  echo Follow README-Windows.md setup first.
  echo.
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"
set PYTHONPATH=src

python -m school_attendance.cli run-daily
set EXIT_CODE=%ERRORLEVEL%

popd
echo.
pause
exit /b %EXIT_CODE%
