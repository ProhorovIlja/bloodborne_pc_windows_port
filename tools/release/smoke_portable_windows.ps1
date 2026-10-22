# Smoke-test the *extracted* Windows developer ZIP, not the build checkout.
# The path contains spaces and Cyrillic deliberately: the user's game folder may too.
param(
    [Parameter(Mandatory=$true)][string]$Archive
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$archivePath = (Resolve-Path $Archive).Path
$target = Join-Path $env:RUNNER_TEMP 'Seamless Hunt Проверка'
if (Test-Path $target) {
    throw "Refusing to overwrite an existing test folder: $target"
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($archivePath, $target)
try {
    $py = Join-Path $target 'python\python.exe'
    $gui = Join-Path $target 'launch_gui.bat'
    $engine = Join-Path $target 'out\bbport.exe'
    if (-not (Test-Path $py) -or -not (Test-Path $gui) -or -not (Test-Path $engine)) {
        throw 'Portable ZIP is missing a required executable'
    }
    if (Test-Path (Join-Path $target 'user')) {
        throw 'Portable ZIP unexpectedly includes private user data'
    }
    $env:PYTHONHOME = ''
    $env:PYTHONPATH = ''
    $env:PYTHONDONTWRITEBYTECODE = '1'
    Push-Location $target
    try {
        & $py -I -B -c @'
import sys, ssl, sqlite3, tkinter, zipfile
root = tkinter.Tk()
root.withdraw()
root.update_idletasks()
root.destroy()
assert sys.version_info[:2] == (3, 12)
print('Standalone Python 3.12 + Tcl/Tk GUI runtime: OK')
'@
        if ($LASTEXITCODE -ne 0) { throw 'Bundled Python/Tk cannot start' }
        # Imports launcher code but never creates its window or starts a game.
        & $py -I -B -c @'
import runpy
from pathlib import Path
app = runpy.run_path('launcher.py', run_name='portable_qa')
assert app['APP_DIR'].resolve() == Path.cwd().resolve()
assert Path('out/bbport.exe').is_file()
print('Portable launcher imports from extracted folder: OK')
'@
        if ($LASTEXITCODE -ne 0) { throw 'Portable launcher import failed' }
        # A real extracted ZIP must contain the manifest and exactly the
        # runtime binaries hashed at packaging time. Never scan user saves.
        & $py -I -B scripts/client_integrity.py --client-dir .
        if ($LASTEXITCODE -ne 0) { throw 'Extracted Windows package integrity mismatch' }
        $pathText = & cmd.exe /D /C ('call "' + $gui + '" --print-python')
        if ($LASTEXITCODE -ne 0) { throw 'Double-click launcher entrypoint failed' }
        if ((($pathText | Out-String).Trim()) -notmatch [regex]::Escape('python\pythonw.exe')) {
            throw "Launcher does not select bundled pythonw.exe: $pathText"
        }
        Write-Host 'Single-click Windows launcher selects bundled Python: OK'
    } finally {
        Pop-Location
    }
    Write-Host 'Portable extraction smoke: PASS'
} finally {
    # Clean CI test only; never touch an end user's save/settings folders.
    if (Test-Path $target) { Remove-Item -LiteralPath $target -Recurse -Force }
}
