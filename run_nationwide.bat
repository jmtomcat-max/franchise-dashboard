@echo off
chcp 65001 > nul
cd /d D:\Franchise_Dashboard
echo ================================================================
echo   Franchise Dashboard - 대한민국 전국 17개 시도 외식업 자동 수집기
echo   - 대상 시도: 17개 시도 (250개 시군구)
echo   - 대상 DB: data\nationwide_food_stores.sqlite3
echo ================================================================
python collector_nationwide.py %*
pause
