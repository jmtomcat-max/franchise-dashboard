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
echo   1단계: 실행환경 사전점검 (Preflight Check)
echo =================================================================
"%PYTHON_EXE%" "%ROOT_DIR%\scripts\preflight_check.py"
if %ERRORLEVEL% NEQ 0 (
    echo [오류] 환경 사전점검을 통과하지 못해 백엔드 서버를 기동할 수 없습니다.
    exit /b %ERRORLEVEL%
)

echo.
echo =================================================================
echo   2단계: Franchise Dashboard FastAPI 백엔드 기동
echo   로컬 주소: http://127.0.0.1:8000
echo   네트워크 주소: http://0.0.0.0:8000
echo   API 문서: http://127.0.0.1:8000/docs
echo   종료: Ctrl + C
echo =================================================================
cd /d "%ROOT_DIR%"
set "ALLOW_DEV_CORS=1"
"%PYTHON_EXE%" -m uvicorn src.stage4e.api.main:app --app-dir "%ROOT_DIR%" --host 0.0.0.0 --port 8000 --reload
