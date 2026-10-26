param(
    [ValidateSet('Start', 'Review', 'Status', 'Stop', 'SelfTest')]
    [string]$Action = 'Status',
    [string]$Workspace = (Split-Path -Parent $PSScriptRoot),
    [int]$PollSeconds = 5
)

$ErrorActionPreference = 'Stop'
$workflow = Join-Path $Workspace '.agent-workflow'
$statePath = Join-Path $workflow 'STATE.json'
$taskPath = Join-Path $workflow 'TASK.md'
$implementationPath = Join-Path $workflow 'IMPLEMENTATION.md'
$reviewPath = Join-Path $workflow 'REVIEW.md'
$resultPath = Join-Path $workflow 'review-result.json'
$reportPath = Join-Path $workflow 'REPORT.md'
$baselinePath = Join-Path $workflow 'BASELINE.json'
$stopPath = Join-Path $workflow 'STOP'
$errorPath = Join-Path $workflow 'ERROR.log'
$protected = @('collector.py', 'gangnam_food_stores.sqlite3', 'run_gangnam.bat')

function Read-State {
    if (-not (Test-Path -LiteralPath $statePath)) { throw "STATE.json이 없습니다: $statePath" }
    Get-Content -Raw -LiteralPath $statePath -Encoding UTF8 | ConvertFrom-Json
}

function Write-State([object]$State) {
    $State | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statePath -Encoding UTF8
}

function Get-ProtectedHashes {
    $hashes = [ordered]@{}
    foreach ($relative in $protected) {
        $path = Join-Path $Workspace $relative
        if (-not (Test-Path -LiteralPath $path)) { throw "보호 파일이 없습니다: $relative" }
        $hashes[$relative] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    }
    $hashes
}

function Assert-ProtectedFiles {
    $baseline = Get-Content -Raw -LiteralPath $baselinePath -Encoding UTF8 | ConvertFrom-Json
    $current = Get-ProtectedHashes
    foreach ($relative in $protected) {
        if ($baseline.$relative -ne $current[$relative]) {
            throw "보호 파일이 변경되었습니다: $relative"
        }
    }
}

function Assert-TaskReady {
    $task = Get-Content -Raw -LiteralPath $taskPath -Encoding UTF8
    if ($task -match '<!--' -or $task.Length -lt 120) {
        throw 'TASK.md의 목표, 허용 범위, 완료 조건을 먼저 작성하세요.'
    }
}

function Find-CodexCommand {
    $command = Get-Command 'codex.cmd' -ErrorAction SilentlyContinue
    if (-not $command) { throw 'codex.cmd를 찾을 수 없습니다.' }
    $command.Source
}

function Invoke-CodexReview([int]$Iteration) {
    $agentsPath = Join-Path $Workspace 'AGENTS.md'
    $prompt = @"
당신은 Franchise Dashboard의 검토 전용 에이전트다. 구현하지 말고 검토만 수행한다.
반드시 아래 세 파일을 직접 열어 내용을 확인한 뒤 판정하라. 사용자에게 검토 대상을 다시 묻지 마라.
- $agentsPath
- $taskPath
- $implementationPath
IMPLEMENTATION.md에 기록된 변경 파일과 검증 산출물을 직접 확인하라.
보호 파일은 수정되면 안 된다. TASK.md 범위, 정확성, 회귀 위험, 테스트 결과를 확인하라.
사소한 취향은 지적하지 말고 실제 결함, 누락, 검증 실패만 findings에 기록하라.
통과하면 verdict=pass, 수정이 필요하면 changes_requested, 환경/안전 문제로 진행 불가하면 blocked를 반환하라.
현재 반복: $Iteration
"@
    $codex = Find-CodexCommand
    $prompt | & $codex exec --skip-git-repo-check --ephemeral --sandbox read-only --output-schema (Join-Path $workflow 'review-schema.json') --output-last-message $resultPath -C $Workspace -
    if ($LASTEXITCODE -ne 0) { throw "Codex 검토 실패(exit=$LASTEXITCODE)" }
    Get-Content -Raw -LiteralPath $resultPath -Encoding UTF8 | ConvertFrom-Json
}

function Write-Review([object]$Result, [int]$Iteration) {
    $findings = if ($Result.findings.Count) { ($Result.findings | ForEach-Object { "- $_" }) -join "`n" } else { '- 없음' }
    $validation = if ($Result.validation.Count) { ($Result.validation | ForEach-Object { "- $_" }) -join "`n" } else { '- 없음' }
    @"
# Codex 검토 결과

- iteration: $Iteration
- verdict: $($Result.verdict)
- reviewed_at: $((Get-Date).ToString('o'))

## 요약

$($Result.summary)

## 수정 요구

$findings

## 검증 근거

$validation
"@ | Set-Content -LiteralPath $reviewPath -Encoding UTF8
}

function Invoke-ReviewStep {
    if (-not (Test-Path -LiteralPath $implementationPath)) { throw 'IMPLEMENTATION.md가 없습니다.' }
    $body = Get-Content -Raw -LiteralPath $implementationPath -Encoding UTF8
    $state = Read-State
    if ($body.TrimEnd().EndsWith('BLOCKED')) {
        $state.status = 'blocked'
        $state.message = 'Antigravity가 BLOCKED를 보고했습니다. IMPLEMENTATION.md를 확인하세요.'
        Write-State $state
        return
    }
    if (-not $body.TrimEnd().EndsWith('READY_FOR_REVIEW')) { throw 'IMPLEMENTATION.md가 READY_FOR_REVIEW로 끝나지 않습니다.' }
    Assert-ProtectedFiles
    $state.phase = 'review'
    $state.status = 'reviewing'
    $state.message = 'Codex가 구현을 검토하고 있습니다.'
    Write-State $state
    $result = Invoke-CodexReview $state.iteration
    Write-Review $result $state.iteration
    if ($result.verdict -eq 'pass') {
        $state.phase = 'approval'
        $state.status = 'awaiting_approval'
        $state.approval_required = $true
        $state.message = '검토를 통과했습니다. REPORT.md 확인 후 승인하세요.'
        Write-State $state
        Copy-Item -LiteralPath $reviewPath -Destination $reportPath -Force
        return
    }
    if ($result.verdict -eq 'blocked' -or $state.iteration -ge $state.max_iterations) {
        $state.status = 'blocked'
        $state.message = if ($result.verdict -eq 'blocked') { '검토 중 차단 조건이 발견되었습니다.' } else { '최대 수정 반복 횟수에 도달했습니다.' }
        Write-State $state
        return
    }
    $state.iteration++
    $state.phase = 'implementation'
    $state.status = 'changes_requested'
    $state.message = 'REVIEW.md 수정 요구를 Antigravity가 처리해야 합니다.'
    Write-State $state
}

function Start-Workflow {
    Assert-TaskReady
    New-Item -ItemType Directory -Path $workflow -Force | Out-Null
    Get-ProtectedHashes | ConvertTo-Json | Set-Content -LiteralPath $baselinePath -Encoding UTF8
    Remove-Item -LiteralPath $stopPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $implementationPath, $reviewPath, $resultPath, $reportPath -Force -ErrorAction SilentlyContinue
    $state = Read-State
    $state.phase = 'implementation'
    $state.iteration = 1
    $state.status = 'implementing'
    $state.approval_required = $false
    $state.message = 'Antigravity 구현 제출을 기다리는 중입니다.'
    Write-State $state

    $antigravity = "$env:LOCALAPPDATA\Programs\Antigravity\Antigravity.exe"
    if (Test-Path -LiteralPath $antigravity) {
        Start-Process -FilePath $antigravity
    }
}

try {
switch ($Action) {
    'Start' { Start-Workflow }
    'Review' { Invoke-ReviewStep }
    'Status' { Read-State | ConvertTo-Json -Depth 5 }
    'Stop' { New-Item -ItemType File -Path $stopPath -Force | Out-Null }
    'SelfTest' {
        $state = Read-State
        if ($state.max_iterations -lt 1) { throw 'max_iterations는 1 이상이어야 합니다.' }
        foreach ($required in @($taskPath, (Join-Path $workflow 'ANTIGRAVITY_PROMPT.md'), (Join-Path $workflow 'review-schema.json'))) {
            if (-not (Test-Path -LiteralPath $required)) { throw "필수 파일이 없습니다: $required" }
        }
        Get-ProtectedHashes | Out-Null
        Find-CodexCommand | Out-Null
        'SELF_TEST_OK'
    }
}
} catch {
    $_ | Out-String | Set-Content -LiteralPath $errorPath -Encoding UTF8
    if (Test-Path -LiteralPath $statePath) {
        $state = Read-State
        $state.status = 'blocked'
        $state.message = "자동 워크플로 오류: $($_.Exception.Message) — ERROR.log를 확인하세요."
        Write-State $state
    }
    throw
}
