# One-click setup. Uses Windows PowerShell 5.1; no player-side Git/Python.
[CmdletBinding()]
param([string]$Install,[string]$HostIPv4='199.195.193.131')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Payload=Join-Path $Root 'launcher-build'
$Target=Join-Path $env:LOCALAPPDATA 'SeamlessHunt-Yharnam-POC'
function IsYharnam([string]$p) {
    if (-not $p -or -not (Test-Path -LiteralPath $p -PathType Container)) {return $false}
    foreach ($file in @('BLauncher.exe','run.py','event-reference.json','bin\bb-probe.exe','tools\party_boss_events.py')) {
        if (-not (Test-Path -LiteralPath (Join-Path $p $file) -PathType Leaf)) {return $false}
    }
    return $true
}
function IsChild([string]$p,[string]$base) {
    return ([IO.Path]::GetFullPath($p).TrimEnd('\')+'\').StartsWith(
        [IO.Path]::GetFullPath($base).TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)
}
function LocateYharnam() {
    $options=New-Object System.Collections.Generic.List[string]
    if ($Install) {$options.Add($Install)}
    $options.Add($Root)
    $options.Add((Split-Path -Parent $Root))
    foreach ($drive in @('C','D','E','F','G')) {
        foreach ($leaf in @('Games\Yharnam Together','Games\YharnamTogether','Yharnam Together','YharnamTogether')) {
            $options.Add(($drive + ':\' + $leaf))
        }
    }
    foreach ($p in @($env:ProgramFiles,[Environment]::GetFolderPath('ProgramFilesX86'),$env:LOCALAPPDATA)) {
        if ($p) {
            $options.Add((Join-Path $p 'Yharnam Together'))
            $options.Add((Join-Path $p 'YharnamTogether'))
        }
    }
    foreach ($p in $options) {if (IsYharnam $p) {return [IO.Path]::GetFullPath($p)}}
    Add-Type -AssemblyName System.Windows.Forms
    $d=New-Object System.Windows.Forms.OpenFileDialog
    $d.Title='Choose BLauncher.exe from your installed Yharnam Together'
    $d.Filter='Yharnam Together (BLauncher.exe)|BLauncher.exe'
    $d.CheckFileExists=$true
    if ($d.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {throw 'Installation was not selected'}
    $p=Split-Path -Parent $d.FileName
    if (-not (IsYharnam $p)) {throw "That folder is not a full Yharnam Together install: $p"}
    return $p
}
try {
    $ip=[Net.IPAddress]::Parse($HostIPv4)
    if ($ip.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or
        $HostIPv4 -eq '0.0.0.0' -or $HostIPv4.StartsWith('127.')) {throw 'Invalid server IPv4'}
    if (-not (Test-Path -LiteralPath (Join-Path $Payload 'BLauncher.exe') -PathType Leaf) -or
        -not (Test-Path -LiteralPath (Join-Path $Payload '_internal') -PathType Container)) {
        throw 'Compiled BLauncher.exe missing. Download GitHub Actions artifact, not development sources.'
    }
    if (Test-Path -LiteralPath (Join-Path $Target 'SH-POC-MANIFEST.json')) {
        $exe=Join-Path $Target 'BLauncher.exe'
        if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {throw 'Existing PoC install is incomplete'}
        Write-Host 'Previous PoC found. Launching...' -ForegroundColor Green
        Start-Process -FilePath $exe -WorkingDirectory $Target
        exit 0
    }
    $Source=LocateYharnam
    if ($Source -ieq $Target -or (IsChild $Target $Source) -or (IsChild $Source $Target)) {
        throw 'Original and PoC paths cannot overlap'
    }
    if (Test-Path -LiteralPath $Target) {
        throw "PoC target already exists; preserving it to avoid deleting saved games: $Target"
    }
    Write-Host "Using installed Yharnam Together: $Source"
    New-Item -ItemType Directory -Path $Target -Force | Out-Null
    $exclude=@('user','coop-game','out','fsr4vk','mods','.git','logs') | ForEach-Object {Join-Path $Source $_}
    $rargs=@($Source,$Target,'/E','/XJ','/R:1','/W:1','/NFL','/NDL','/NJH','/NJS','/NP','/XD') + $exclude
    & robocopy.exe @rargs | Out-Null
    if ($LASTEXITCODE -ge 8) {throw "Cannot copy Yharnam Together ($LASTEXITCODE)"}
    & robocopy.exe $Payload $Target '/E' '/R:1' '/W:1' '/NFL' '/NDL' '/NJH' '/NJS' '/NP' | Out-Null
    if ($LASTEXITCODE -ge 8) {throw "Cannot copy frozen PoC launcher ($LASTEXITCODE)"}
    $user=Join-Path $Target 'user'
    New-Item -ItemType Directory -Path $user -Force | Out-Null
    $settings=@{game='';update='';role='guest';host_ip=$HostIPv4;account='';password='';
        p2p_port='auto';harder='off';prepared='';confirmed=''}
    [IO.File]::WriteAllText((Join-Path $user 'coop.json'),($settings|ConvertTo-Json),
        [Text.UTF8Encoding]::new($false))
    $manifest=@{source=$Source;server=$HostIPv4;protocol_revision='77e350743a7cb4524cfcc1782fb6e3af64e25b15';
        windows_game_runtime='existing_install_unverified';created=[DateTime]::UtcNow.ToString('o')}
    [IO.File]::WriteAllText((Join-Path $Target 'SH-POC-MANIFEST.json'),($manifest|ConvertTo-Json),
        [Text.UTF8Encoding]::new($false))
    Write-Host 'Checking Fornex server:'
    foreach ($port in @(32315,21443)) {
        try {
            $sock=New-Object Net.Sockets.TcpClient
            $pending=$sock.BeginConnect($HostIPv4,$port,$null,$null)
            $ok=$pending.AsyncWaitHandle.WaitOne(1200) -and $sock.Connected
            $sock.Close()
            Write-Host ("TCP {0}: {1}" -f $port, $(if($ok){'OK'}else{'BLOCKED'}))
        } catch { Write-Warning "TCP $port not reachable: check Fornex firewall" }
    }
    Write-Host 'Setup complete. Select Bloodborne in the launcher, if needed.' -ForegroundColor Green
    Start-Process -FilePath (Join-Path $Target 'BLauncher.exe') -WorkingDirectory $Target
} catch {
    Write-Host ('INSTALL ERROR: '+$_.Exception.Message) -ForegroundColor Red
    exit 1
}
