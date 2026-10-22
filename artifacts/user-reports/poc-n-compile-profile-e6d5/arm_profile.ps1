$ErrorActionPreference = 'Stop'
$taskFolder = $PSScriptRoot
$runFolder = Join-Path $taskFolder 'run'
New-Item -ItemType Directory -Path $runFolder -ErrorAction Stop | Out-Null
$image = 'sha256:9d2e601f926ae644a041903b076fdb33ff3885be1a0f390137bc61ff461584e1'
$imageRecord = docker image inspect --format '{{.Id}} {{json .Config.User}} {{json .Config.WorkingDir}}' $image
if ($LASTEXITCODE -ne 0) { throw 'Selected image inspection failed' }
[IO.File]::WriteAllText((Join-Path $runFolder 'selected-image.txt'), $imageRecord)
$arguments = @('create', '--name', 'remission-n-original-compile-profile-20261022', '--cpus', '2', '--memory', '2g', '--memory-swap', '2g', '--pids-limit', '256', '--network', 'none', '--read-only', '--user', '10002:10002', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,exec,nosuid,nodev,size=536870912,mode=1777', '--mount', "type=bind,source=$taskFolder/source,target=/source,readonly", '--mount', "type=bind,source=$taskFolder/profile_probe.py,target=/input/profile_probe.py,readonly", '--mount', "type=bind,source=$runFolder,target=/output", '--env', 'NOF1_STAGE_SECONDS=300', '--env', 'PYTHONPATH=/source', '--env', 'PYTHONDONTWRITEBYTECODE=1', '--env', 'OPENBLAS_NUM_THREADS=1', '--env', 'OMP_NUM_THREADS=1', '--env', 'MKL_NUM_THREADS=1', '--env', 'NUMEXPR_NUM_THREADS=1', '--workdir', '/source', $image, 'python', '/input/profile_probe.py')
$containerId = (docker @arguments).Trim()
if ($LASTEXITCODE -ne 0 -or $containerId -notmatch '^[a-f0-9]{64}$') { throw 'Container create failed' }
$monitorStart = [DateTimeOffset]::UtcNow
$deadline = $monitorStart.AddSeconds(300)
$watcherPath = Join-Path $runFolder 'watchdog.ps1'
$eventsPath = Join-Path $runFolder 'watchdog-events.jsonl'
$watcher = @'
$ErrorActionPreference = 'Stop'
$container = '__CONTAINER__'
$deadline = [DateTimeOffset]::Parse('__DEADLINE__')
$events = '__EVENTS__'
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
'@
$watcher = $watcher.Replace('__CONTAINER__', $containerId).Replace('__DEADLINE__', $deadline.ToString('o')).Replace('__EVENTS__', $eventsPath.Replace('\', '/'))
[IO.File]::WriteAllText($watcherPath, $watcher)
$frozen = [ordered]@{source='e6d5f4ae94793e25e76f3ecf5368420849066916'; image=$image; original_probe_sha256='170795862e4a5892e88b1f24f380acbc899c2cadd57234f205fd3bc8a9dd2f33'; original_input_manifest_sha256='e400c6dba11fe887531f801f3e5089012142f1d4b022c382d614df17277cb4db'; profile_probe_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $taskFolder 'profile_probe.py')).Hash.ToLowerInvariant(); watchdog_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $watcherPath).Hash.ToLowerInvariant(); source_freeze_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $taskFolder 'source-freeze.json')).Hash.ToLowerInvariant(); container_id=$containerId; monitor_start_utc=$monitorStart.ToString('o'); deadline_utc=$deadline.ToString('o'); cap_seconds=300; no_retry=$true; mutations='transparent phase timing wrappers and readonly periodic Python stacks only'}
[IO.File]::WriteAllText((Join-Path $runFolder 'frozen-profile.json'), ($frozen | ConvertTo-Json -Depth 8))
$watcherProcess = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $watcherPath) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runFolder 'watchdog.stdout') -RedirectStandardError (Join-Path $runFolder 'watchdog.stderr')
for ($i=0; $i -lt 50 -and -not (Test-Path -LiteralPath $eventsPath); $i++) { Start-Sleep -Milliseconds 100 }
if (-not (Test-Path -LiteralPath $eventsPath)) { throw 'Watchdog did not arm; do not start container' }
$frozen['watchdog_pid'] = $watcherProcess.Id
[IO.File]::WriteAllText((Join-Path $runFolder 'launch.json'), ($frozen | ConvertTo-Json -Depth 8))
$frozen | ConvertTo-Json -Compress -Depth 8
