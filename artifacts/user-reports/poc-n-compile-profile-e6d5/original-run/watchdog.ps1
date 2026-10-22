$ErrorActionPreference = 'Stop'
$targetContainer = '9a487739721563386cfd5f2cd7b9f12b5153b2e3a2a471d37079d73cbcf7c7f3'
$targetDeadline = [DateTimeOffset]::Parse('2026-10-22T17:54:07.3400446+00:00')
$reportPath = 'C:/Users/erics/Documents/Projects/REMission-worktrees/poc-n-source-review-astra-261022/artifacts/user-reports/poc-n-symbolic-e6d5-run1/watchdog-events.jsonl'
function Record-Watch($kind,$state) { [ordered]@{kind=$kind;at=[DateTimeOffset]::UtcNow.ToString('o');container_id=$targetContainer;state=$state} | ConvertTo-Json -Compress -Depth 5 | Add-Content -LiteralPath $reportPath }
Record-Watch 'watchdog-start' $null
while ($true) {
    $stateText = docker inspect $targetContainer --format '{{json .State}}'
    if ($LASTEXITCODE -ne 0) { throw 'Selected container inspect failed' }
    $state = $stateText | ConvertFrom-Json
    if ($state.Status -in @('exited','dead')) { Record-Watch 'terminal-observed' $state; exit 0 }
    if ([DateTimeOffset]::UtcNow -ge $targetDeadline) {
        Record-Watch 'deadline-kill' $state
        docker kill $targetContainer | Out-Null
        $terminal = docker inspect $targetContainer --format '{{json .State}}' | ConvertFrom-Json
        Record-Watch 'after-kill' $terminal
        exit 124
    }
    Start-Sleep -Milliseconds 500
}
