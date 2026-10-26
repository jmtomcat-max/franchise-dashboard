@echo off
chcp 65001 > nul
echo =======================================================================
echo Franchise Dashboard - Phase 4 Stage 4B Brand Candidate Pipeline Runner
echo =======================================================================

echo [*] Step 1: Running Automated Tests...
python -m unittest tests/test_phase4_stage4b.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Stage 4B automated tests failed! Aborting pipeline.
    exit /b %ERRORLEVEL%
)

echo [*] Step 2: Executing Nationwide Brand Candidate Pipeline (735,185 stores)...
python src/stage4b/pipeline.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Nationwide pipeline execution failed!
    exit /b %ERRORLEVEL%
)

echo [*] Step 3: Running Quality Evaluator on Gold Standard Sample...
python src/stage4b/evaluator.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Evaluator execution failed!
    exit /b %ERRORLEVEL%
)

echo =======================================================================
echo [SUCCESS] Phase 4 Stage 4B Execution Successfully Completed!
echo =======================================================================
