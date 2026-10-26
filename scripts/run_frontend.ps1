# Franchise Dashboard - 프론트엔드 Vite 개발 서버 실행 PowerShell 스크립트
$ErrorActionPreference = 'Stop'
$rootDir = (Split-Path -Parent $PSScriptRoot)
$frontendDir = Join-Path $rootDir "frontend"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  Franchise Dashboard - 프론트엔드 Vite 개발 서버 실행" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    Write-Host "[*] frontend/node_modules 가 없어 패키지를 설치합니다..." -ForegroundColor Yellow
    Push-Location $frontendDir
    npm install
    Pop-Location
}

Push-Location $frontendDir
Write-Host "[*] Vite 개발 서버를 시작합니다..." -ForegroundColor Green
Write-Host "[*] 브라우저 접속 주소: http://localhost:5173" -ForegroundColor Green
Write-Host "[*] 종료하려면 Ctrl + C 를 누르세요.`n" -ForegroundColor DarkGray
npm run dev
Pop-Location
