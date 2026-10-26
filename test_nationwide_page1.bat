@echo off
chcp 65001 > nul
cd /d D:\Franchise_Dashboard
echo ================================================================
echo   [전국 수집기 테스트] 서울 외 지역(부산 해운대구 26350) 1페이지 시험
echo   - 대상 DB: data\test_nationwide_page1.sqlite3 (운영 DB 분리 격리)
echo   - 대상 지역: 부산 해운대구 (26350) 1페이지 (최대 1,000건)
echo ================================================================
python collector_nationwide.py --district 26350 --test-single-page --db data\test_nationwide_page1.sqlite3 --report reports\test_nationwide_page1_report.json --summary reports\test_nationwide_page1_summary.md
pause
