@echo off
chcp 65001 > nul
cd /d D:\Franchise_Dashboard
echo ================================================================
echo   Franchise Dashboard - 서울 25개 자치구 외식업 자동 수집기
echo ================================================================
python collector_seoul.py %*
pause
