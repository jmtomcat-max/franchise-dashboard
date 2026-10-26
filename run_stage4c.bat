@echo off
chcp 65001 > nul
echo ==============================================================================
echo [Phase 4 Stage 4C] Brand Master Build and Nationwide Reconciliation Batch
echo Project: D:\Franchise_Dashboard
echo Date: 2026-10-13
echo ==============================================================================

echo.
echo [Step 1/5] Running Stage 4C Migration Pipeline (5,062 brands ^& 735,208 links)...
python -u src/stage4c/migration_pipeline.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Migration pipeline failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

echo.
echo [Step 2/5] Running Independent Quality Evaluation (520 stratified samples)...
python -u src/stage4c/evaluator.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Quality evaluation failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

echo.
echo [Step 3/5] Generating Local Review Dashboard HTML Report...
python -u src/stage4c/review_system.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Review report generation failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

echo.
echo [Step 4/5] Running Comprehensive Integrity Validation (JSON)...
python -u src/stage4c/validator.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Validation runner failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

echo.
echo [Step 5/5] Executing Automated Test Suite (11/11 tests)...
python tests/test_phase4_stage4c.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Test suite failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

echo.
echo ==============================================================================
echo [Stage 4C Complete] All steps succeeded. Brand master database and reports verified.
echo Master DB: data\brand_master_v1.sqlite3
echo Validation: reports\phase4_stage4c_validation.json
echo HTML Report: reports\stage4c_brand_review_dashboard.html
echo ==============================================================================
