# Franchise Dashboard - 환경 사전점검 실행기 (PowerShell)
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
Write-Host "  Franchise Dashboard - 환경 사전점검 실행" -ForegroundColor Cyan
Write-Host "  사용 Python: $pythonExe" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

$scriptPath = Join-Path $PSScriptRoot "preflight_check.py"
& $pythonExe $scriptPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[경고] 사전점검에서 결함이 발견되었습니다. 위 조치 가이드를 확인하세요." -ForegroundColor Yellow
    exit $LASTEXITCODE
} else {
    Write-Host "`n[완료] 사전점검을 성공적으로 통과했습니다." -ForegroundColor Green
}
