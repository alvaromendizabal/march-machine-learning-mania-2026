@echo off
setlocal
cd /d "%~dp0\.."
echo Environment: %CONDA_DEFAULT_ENV%
python -c "import sys; print('Python:', sys.executable)"
python -m pip check
python -m pytest
python -m ruff check src tests
jupyter kernelspec list
endlocal
