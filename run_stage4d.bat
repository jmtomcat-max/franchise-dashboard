@echo off
chcp 65001 > nul
setlocal

echo ==============================================================================
echo [Phase 4 Stage 4D] 8대 대분류 및 48대 중분류 통합 분류 파이프라인
echo 프로젝트: D:\Franchise_Dashboard
echo ==============================================================================

echo.
echo [Step 1/4] 카테고리 마스터 DB 생성 및 전국 점포 분류 파이프라인 실행...
python src/stage4d/classifier.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] classifier.py 실행 실패 (Error code: %ERRORLEVEL%)
    exit /b %ERRORLEVEL%
)

echo.
echo [Step 2/4] 독립 품질 평가 및 신뢰구간 산출 (200건+ 독립 표본)...
python src/stage4d/evaluator.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] evaluator.py 실행 실패 (Error code: %ERRORLEVEL%)
    exit /b %ERRORLEVEL%
)

echo.
echo [Step 3/4] 데이터 무결성 및 집계 대사 종합 검증...
python src/stage4d/validator.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] validator.py 실행 실패 (Error code: %ERRORLEVEL%)
    exit /b %ERRORLEVEL%
)

echo.
echo [Step 4/4] 자동화 단위/통합 테스트 스위트 실행...
python tests/test_phase4_stage4d.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] test_phase4_stage4d.py 테스트 실패 (Error code: %ERRORLEVEL%)
    exit /b %ERRORLEVEL%
)

echo.
echo ==============================================================================
echo [SUCCESS] Stage 4D 8대 대분류 및 48대 중분류 체계 구축 및 검증이 완료되었습니다!
echo 산출물: data/food_category_master_v1.sqlite3
echo 검증결과: reports/phase4_stage4d_validation.json
echo ==============================================================================

endlocal
exit /b 0
