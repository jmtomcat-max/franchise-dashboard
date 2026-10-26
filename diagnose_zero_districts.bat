@echo off
chcp 65001 > nul
cd /d D:\Franchise_Dashboard
echo ================================================================
echo   Franchise Dashboard - 전국 누락 지역 코드 실증 검증 프로그램
echo ================================================================
python diagnose_zero_districts.py %*
pause
