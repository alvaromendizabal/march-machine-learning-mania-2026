@echo off
setlocal
cd /d "%~dp0\.."

where kaggle >nul 2>nul
if errorlevel 1 (
  echo ERROR: Kaggle CLI is not installed in the active environment.
  echo Run: python -m pip install --upgrade-strategy only-if-needed kaggle
  exit /b 1
)

if not exist "%USERPROFILE%\.kaggle\kaggle.json" (
  echo ERROR: Kaggle credentials were not found at:
  echo %USERPROFILE%\.kaggle\kaggle.json
  echo Generate an API token in Kaggle Settings, then copy kaggle.json there.
  exit /b 1
)

if not exist "data\raw" mkdir "data\raw"
if not exist "data\raw\march-machine-learning-mania-2026" mkdir "data\raw\march-machine-learning-mania-2026"

echo Downloading competition data...
kaggle competitions download -c march-machine-learning-mania-2026 -p "data\raw" --force
if errorlevel 1 (
  echo ERROR: Download failed. Confirm that you accepted the competition rules and that kaggle.json is valid.
  exit /b 1
)

set "ZIP_PATH=data\raw\march-machine-learning-mania-2026.zip"
if not exist "%ZIP_PATH%" (
  echo ERROR: Expected ZIP file was not found: %ZIP_PATH%
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ZIP_PATH%' -DestinationPath 'data\raw\march-machine-learning-mania-2026' -Force"
if errorlevel 1 exit /b 1

echo.
echo Download and extraction complete.
dir /b "data\raw\march-machine-learning-mania-2026\*.csv"
endlocal
