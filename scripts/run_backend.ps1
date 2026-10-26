# Franchise Dashboard - 백엔드 기동 스크립트 (PowerShell)
$rootDir = (Split-Path -Parent $PSScriptRoot)
$venvPython = Join-Path $rootDir ".venv\Scripts\python.exe"
$py312 = "C:\Users\jongmin98\AppData\Local\Programs\Python\Python312\python.exe"

if (Test-Path -LiteralPath $venvPython) {
    $pythonExe = $venvPython
} elseif (Test-Path -LiteralPath $py312) {
    $pythonExe = $py312
} else {
    $pythonExe = "py"
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  1단계: 실행환경 사전점검 (Preflight Check)" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$preflightScript = Join-Path $PSScriptRoot "preflight_check.py"
& $pythonExe $preflightScript

if ($LASTEXITCODE -ne 0) {
    Write-Host "[오류] 환경 사전점검을 통과하지 못해 백엔드 서버를 기동할 수 없습니다." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host "  2단계: Franchise Dashboard FastAPI 백엔드 기동" -ForegroundColor Green
Write-Host "  로컬 주소: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  네트워크 주소: http://0.0.0.0:8000" -ForegroundColor Green
Write-Host "  API 문서: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "  종료: Ctrl + C" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green

Set-Location -LiteralPath $rootDir
$env:ALLOW_DEV_CORS = "1"
& $pythonExe -m uvicorn src.stage4e.api.main:app --app-dir $rootDir --host 0.0.0.0 --port 8000 --reload
