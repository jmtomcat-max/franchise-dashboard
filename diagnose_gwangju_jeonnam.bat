@echo off
chcp 65001 > nul
cd /d D:\Franchise_Dashboard
echo ================================================================
echo   Franchise Dashboard - 광주·전남 API 조회 실패 원인 집중 분석
echo ================================================================
python diagnose_gwangju_jeonnam.py %*
pause
