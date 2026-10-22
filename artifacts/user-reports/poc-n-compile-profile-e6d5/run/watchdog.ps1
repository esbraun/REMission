$ErrorActionPreference = 'Stop'
$container = '47111f0e6cb1441d33191a87ae4aeb0e4fe935e45990548fa3f49c59bdd64533'
$deadline = [DateTimeOffset]::Parse('2026-10-22T18:45:36.3804216+00:00')
$events = 'C:/Users/erics/Documents/Projects/REMission-worktrees/poc-n-compile-repair-sol-261022/artifacts/user-reports/poc-n-compile-profile-e6d5/run/watchdog-events.jsonl'
function Record($kind, $state) {
  $row = [ordered]@{kind=$kind;utc=[DateTimeOffset]::UtcNow.ToString('o');container=$container;deadline_utc=$deadline.ToString('o');state=$state}
  [IO.File]::AppendAllText($events, (($row | ConvertTo-Json -Compress -Depth 8) + [Environment]::NewLine))
}
Record 'watchdog-armed' $null
while ($true) {
  $stateText = docker inspect --format '{{json .State}}' $container
  if ($LASTEXITCODE -ne 0) { Record 'inspect-error' $null; exit 2 }
  $state = $stateText | ConvertFrom-Json
  if ($state.Status -notin @('created', 'running')) { Record 'terminal-observed' $state; exit 0 }
  if ([DateTimeOffset]::UtcNow -ge $deadline) {
    Record 'deadline-kill' $state
    docker kill $container | Out-Null
    $terminal = docker inspect --format '{{json .State}}' $container
    Record 'terminal-after-kill' ($terminal | ConvertFrom-Json)
    exit 0
  }
  Start-Sleep -Milliseconds 250
}