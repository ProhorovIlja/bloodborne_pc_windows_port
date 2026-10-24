# Sample host process memory while the player runs Bloodborne PC natively.
# Adapted from ProhorovIlja/tekken6-native-online-source (feature/long-session-process-memory-trace).
# Development-only diagnostics; not invoked by the player launcher.
# Does not attach to guest memory, modify the game, or read player credentials.
param(
    [string]$ProcessName = 'bb-probe',
    [int]$ProcessId = 0,
    [int]$Seconds = 1800,
    [int]$IntervalSeconds = 5,
    [string]$Output = 'runs/bloodborne_process_memory.csv'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if ($ProcessName -notmatch '^[A-Za-z0-9_-]{1,64}$') {
    throw 'ProcessName must be a simple executable name without a path or extension.'
}
if ($ProcessId -lt 0 -or $Seconds -lt 1 -or $IntervalSeconds -lt 1) {
    throw 'ProcessId must be nonnegative and Seconds and IntervalSeconds positive.'
}
$path = if ([IO.Path]::IsPathRooted($Output)) { $Output } else { Join-Path $root $Output }
$parent = Split-Path -Parent $path
if ($parent -and -not (Test-Path $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
$culture = [Globalization.CultureInfo]::InvariantCulture
$utf8 = New-Object System.Text.UTF8Encoding($false)
$writer = New-Object System.IO.StreamWriter($path, $false, $utf8)
$samples = 0
$clock = [Diagnostics.Stopwatch]::StartNew()
try {
    $writer.WriteLine('timestamp_utc,pid,process_start_utc,private_bytes,working_set_bytes,virtual_bytes,handles,threads')
    do {
        # A named-process query sees both native clients while they are alive.
        # Passing -ProcessId pins the diagnostic to one known process.
        $games = if ($ProcessId -gt 0) {
            @(Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
        } else {
            @(Get-Process -Name $ProcessName -ErrorAction SilentlyContinue)
        }
        $now = [DateTime]::UtcNow.ToString('o', $culture)
        foreach ($game in $games) {
            if (-not $game) { continue }
            try {
                # A process can exit in the middle of reading its properties.
                # Prefer skipping that sample to emitting partial/zero metrics.
                $start = $game.StartTime.ToUniversalTime().ToString('o', $culture)
                $values = @(
                    $now,
                    [string]$game.Id,
                    $start,
                    [string]$game.PrivateMemorySize64,
                    [string]$game.WorkingSet64,
                    [string]$game.VirtualMemorySize64,
                    [string]$game.HandleCount,
                    [string]$game.Threads.Count
                )
                $writer.WriteLine(($values -join ','))
                $samples++
            } catch [System.Exception] {
                # Process already exited, or memory counters could not be read.
            }
        }
        $writer.Flush()
        $remaining = $Seconds - $clock.Elapsed.TotalSeconds
        if ($remaining -gt 0) {
            $nap = [Math]::Min([double]$IntervalSeconds, $remaining)
            Start-Sleep -Milliseconds ([Math]::Max(1, [int]($nap * 1000)))
        }
    } while ($clock.Elapsed.TotalSeconds -lt $Seconds)
} finally {
    $writer.Dispose()
    $clock.Stop()
}
Write-Host "Captured $samples process-memory samples at $path"
if ($samples -eq 0) {
    Write-Warning 'No matching game processes were observed. Start the native game before or during sampling.'
    exit 3
}
# PowerShell child scripts may otherwise leave $LASTEXITCODE from an
# unrelated native command in the calling scope; explicitly signal success.
exit 0
