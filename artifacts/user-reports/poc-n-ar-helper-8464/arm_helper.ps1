$ErrorActionPreference = 'Stop'
$taskFolder = $PSScriptRoot
$runFolder = Join-Path $taskFolder 'run'
New-Item -ItemType Directory -Path $runFolder -ErrorAction Stop | Out-Null
$image = 'sha256:9d2e601f926ae644a041903b076fdb33ff3885be1a0f390137bc61ff461584e1'
$imageRecord = docker image inspect --format '{{.Id}} {{json .Config.User}} {{json .Config.WorkingDir}}' $image
if ($LASTEXITCODE -ne 0) { throw 'Selected image inspection failed' }
[IO.File]::WriteAllText((Join-Path $runFolder 'selected-image.txt'), $imageRecord)
$arguments = @('create', '--name', 'remission-n-ar-helper-8464-20261022', '--cpus', '2', '--memory', '2g', '--memory-swap', '2g', '--pids-limit', '256', '--network', 'none', '--read-only', '--user', '10002:10002', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,exec,nosuid,nodev,size=536870912,mode=1777', '--mount', "type=bind,source=$taskFolder/source,target=/source,readonly", '--mount', "type=bind,source=$taskFolder/helper_probe.py,target=/input/helper_probe.py,readonly", '--mount', "type=bind,source=$taskFolder/input-manifest.json,target=/input/input-manifest.json,readonly", '--mount', "type=bind,source=$runFolder,target=/output", '--env', 'PYTHONPATH=/source', '--env', 'PYTHONDONTWRITEBYTECODE=1', '--env', 'OPENBLAS_NUM_THREADS=1', '--env', 'OMP_NUM_THREADS=1', '--env', 'MKL_NUM_THREADS=1', '--env', 'NUMEXPR_NUM_THREADS=1', '--workdir', '/source', $image, 'python', '/input/helper_probe.py')
$containerId = (docker @arguments).Trim()
if ($LASTEXITCODE -ne 0 -or $containerId -notmatch '^[a-f0-9]{64}$') { throw 'Container create failed' }
$monitorStart = [DateTimeOffset]::UtcNow
$deadline = $monitorStart.AddSeconds(120)
$watcherPath = Join-Path $runFolder 'watchdog.ps1'
$eventsPath = Join-Path $runFolder 'watchdog-events.jsonl'
$oldFolder = Join-Path (Split-Path $taskFolder -Parent) 'poc-n-compile-profile-e6d5/run'
$oldLaunch = Get-Content -Raw (Join-Path $oldFolder 'launch.json') | ConvertFrom-Json
$watcher = Get-Content -Raw (Join-Path $oldFolder 'watchdog.ps1')
$watcher = $watcher.Replace($oldLaunch.container_id, $containerId).Replace($oldLaunch.deadline_utc, $deadline.ToString('o')).Replace((Join-Path $oldFolder 'watchdog-events.jsonl').Replace('\', '/'), $eventsPath.Replace('\', '/'))
[IO.File]::WriteAllText($watcherPath, $watcher)
$frozen = [ordered]@{source='8464c8f1d047be31fdb2ee3ec6767fcb477dca07'; image=$image; probe_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $taskFolder 'helper_probe.py')).Hash.ToLowerInvariant(); manifest_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $taskFolder 'input-manifest.json')).Hash.ToLowerInvariant(); watchdog_sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $watcherPath).Hash.ToLowerInvariant(); container_id=$containerId; monitor_start_utc=$monitorStart.ToString('o'); deadline_utc=$deadline.ToString('o'); cap_seconds=120; no_retry=$true; whole_model_build=$false; fit=$false}
[IO.File]::WriteAllText((Join-Path $runFolder 'frozen-helper.json'), ($frozen | ConvertTo-Json -Depth 8))
$watcherProcess = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $watcherPath) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runFolder 'watchdog.stdout') -RedirectStandardError (Join-Path $runFolder 'watchdog.stderr')
for ($i=0; $i -lt 50 -and -not (Test-Path -LiteralPath $eventsPath); $i++) { Start-Sleep -Milliseconds 100 }
if (-not (Test-Path -LiteralPath $eventsPath)) { throw 'Watchdog did not arm; do not start container' }
$frozen['watchdog_pid'] = $watcherProcess.Id
[IO.File]::WriteAllText((Join-Path $runFolder 'launch.json'), ($frozen | ConvertTo-Json -Depth 8))
$frozen | ConvertTo-Json -Compress -Depth 8
