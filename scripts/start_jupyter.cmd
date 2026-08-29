@echo off
setlocal
call "%USERPROFILE%\miniforge3\Scripts\activate.bat" ml-modeling
if errorlevel 1 exit /b 1
cd /d "%~dp0\.."
echo Active environment: %CONDA_DEFAULT_ENV%
python -c "import sys; print('Python:', sys.executable)"
jupyter lab
endlocal
