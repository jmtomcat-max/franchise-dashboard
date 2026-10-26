@echo off
chcp 65001 > nul
cd /d D:\Franchise_Dashboard
echo ================================================================
echo   Franchise Dashboard - Phase 3 Stage A 자동 검증 테스트
echo ================================================================
python test_phase3_stage_a.py %*
pause
