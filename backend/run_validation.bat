@echo off
REM BALAGH: unit tests + live validation. Results: test_results.txt, validation_report.md
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo === Unit tests ===
python -m pytest -q --tb=short > test_results.txt 2>&1
type test_results.txt
echo.
echo === Live validation (Supabase + AI providers + full workflow) ===
python -m scripts.validate_backend
echo.
echo Done. Tell Claude the run has finished.
pause
