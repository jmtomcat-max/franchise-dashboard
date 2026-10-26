@echo off
chcp 65001 > nul
set "ROOT_DIR=%~dp0.."
if exist "%ROOT_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"
) else if exist "C:\Users\jongmin98\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=C:\Users\jongmin98\AppData\Local\Programs\Python\Python312\python.exe"
) else (
    set "PYTHON_EXE=py"
)
echo =================================================================
echo   Franchise Dashboard - 환경 사전점검 실행
echo   사용 Python: %PYTHON_EXE%
echo =================================================================
"%PYTHON_EXE%" "%ROOT_DIR%\scripts\preflight_check.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [경고] 사전점검에서 결함이 발견되었습니다. 위 조치 가이드를 확인하세요.
    exit /b %ERRORLEVEL%
)
echo.
echo [완료] 사전점검을 성공적으로 통과했습니다.
