@echo off
chcp 65001 > nul
title Franchise Dashboard [외부 인터넷 공유 모드 - Cloudflare Tunnel]
cd /d "%~dp0.."

echo.
echo ======================================================================
echo   Franchise Dashboard - 외부 인터넷 전용 공유 링크 실행 (Cloudflare Tunnel)
echo ======================================================================
echo   1. Cloudflare Tunnel 링크는 사내 방화벽/Wi-Fi 격리와 무관하게 누구나 접속 가능한 주소입니다.
echo   2. 사내망(CJ 보안망) 환경에서 '우회접속 차단정책'이 적용된 경우 모바일 핫스팟 환경에서 구동하십시오.
echo   3. 외부 공유를 종료하려면 이 창을 닫아 터널을 즉시 종료하십시오.
echo ======================================================================
echo.

if not exist "%~dp0..\cloudflared.exe" (
    echo [*] cloudflared.exe 가 없어 다운로드를 시도합니다...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%~dp0..\cloudflared.exe'"
)

echo [*] Cloudflare 보안 터널을 연결합니다...
echo (잠시 후 콘솔에 나타나는 https://....trycloudflare.com 링크를 팀원에게 전달하세요)
echo.
"%~dp0..\cloudflared.exe" tunnel --url http://localhost:5173
pause