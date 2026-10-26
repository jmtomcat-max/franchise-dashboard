@echo off
chcp 65001 > nul
cd /d D:\Franchise_Dashboard
echo ================================================================
echo   [테스트 모드] 강남구(11680) 첫 1페이지 실전 시험 호출
echo   - 대상 DB: data\test_gangnam_page1.sqlite3 (운영 DB 분리 격리)
echo   - 결과 리포트: reports\test_gangnam_page1_report.json
echo ================================================================
python collector_seoul.py --district 11680 --test-single-page --db data\test_gangnam_page1.sqlite3 --report reports\test_gangnam_page1_report.json
pause
