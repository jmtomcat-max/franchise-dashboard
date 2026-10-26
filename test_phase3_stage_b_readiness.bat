@echo off
chcp 65001 > nul
cd /d D:\Franchise_Dashboard
echo ================================================================
echo   Franchise Dashboard - Stage B 10대 실패·경계 조건 테스트
echo ================================================================
python test_phase3_stage_b_readiness.py %*
pause
