@echo off
chcp 65001 > nul
cd /d D:\Franchise_Dashboard
echo ================================================================
echo   Franchise Dashboard - 전남광주통합특별시(12) 점포조회 실증 테스트
echo ================================================================
python test_integrated_special_city.py %*
pause
