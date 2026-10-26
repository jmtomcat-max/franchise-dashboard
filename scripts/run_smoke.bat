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
echo   Franchise Dashboard - 주요 API 스모크 테스트 실행
echo   사용 Python: %PYTHON_EXE%
echo =================================================================
"%PYTHON_EXE%" "%ROOT_DIR%\scripts\smoke_test_api.py" %*
