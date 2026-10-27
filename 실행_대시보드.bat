@echo off
chcp 65001 > nul
title Franchise Dashboard Launcher
set "ROOT_DIR=%~dp0"

echo =================================================================
echo   [1/2] Franchise Dashboard FastAPI 백엔드 기동 (포트: 8000)
echo =================================================================
start "Franchise Dashboard Backend (Port 8000)" "%ROOT_DIR%scripts\run_backend.bat"

echo.
echo =================================================================
echo   [2/2] Franchise Dashboard Frontend 개발 서버 기동 (포트: 5173)
echo   브라우저 접속 주소: http://localhost:5173
echo =================================================================
cd /d "%ROOT_DIR%frontend"
npm run dev
pause
