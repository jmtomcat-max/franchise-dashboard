@echo off
chcp 65001 > nul
cd /d D:\Franchise_Dashboard
echo ================================================================
echo   Franchise Dashboard - 전남광주통합특별시(12) 27개 시군구 전수 검증
echo ================================================================
python verify_integrated_city_mapping.py %*
pause
