@echo off
chcp 65001 > nul
echo ======================================================================
echo  Franchise Dashboard - Phase 4 Stage 4E 자동 검증 및 벤치마크 실행기
echo ======================================================================
echo.

echo [1/3] 데이터베이스 및 공간 분석 데이터 무결성 검증 (15개 핵심 불변식)...
python src\stage4e\validator.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 무결성 검증 실패! 실행을 중단합니다.
    exit /b %ERRORLEVEL%
)
echo.

echo [2/3] 실측 성능 벤치마크 측정 (SLA 및 대규모 공간 검색 속도)...
python src\stage4e\benchmark.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 벤치마크 테스트 실패!
    exit /b %ERRORLEVEL%
)
echo.

echo [3/3] Pytest 통합 자동화 테스트 실행 (15개 시나리오 전수 검증)...
python -m pytest tests\test_phase4_stage4e.py -v
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Pytest 테스트 스위트 실패!
    exit /b %ERRORLEVEL%
)
echo.

echo ======================================================================
echo  [SUCCESS] Stage 4E 전체 검증·벤치마크·테스트 100% 통과 완료!
echo ======================================================================
pause
