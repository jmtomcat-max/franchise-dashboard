@echo off
title Franchise Dashboard Frontend Server
echo ========================================================
echo  Franchise Dashboard 풀 웹앱 개발 서버를 구동합니다...
echo  브라우저 주소: http://localhost:5173
echo ========================================================
cd /d "%~dp0frontend"
npm run dev
pause
