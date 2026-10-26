@echo off
chcp 65001 > nul
echo =================================================================
echo   Franchise Dashboard - 프론트엔드 Vite 개발 서버 실행
echo =================================================================

set FRONTEND_DIR=%~dp0..\frontend

if not exist "%FRONTEND_DIR%\node_modules" (
    echo [*] frontend/node_modules 가 없어 패키지를 설치합니다...
    cd /d "%FRONTEND_DIR%"
    call npm install
    if %ERRORLEVEL% NEQ 0 (
        echo [오류] npm install 실패
        pause
        exit /b %ERRORLEVEL%
    )
)

cd /d "%FRONTEND_DIR%"
echo [*] Vite 개발 서버를 시작합니다...
echo [*] 브라우저 접속 주소: http://localhost:5173
echo.
call npm run dev
