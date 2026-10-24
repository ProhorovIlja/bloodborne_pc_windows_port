# Passive Windows CPU/RAM process sampler: NO game memory writes, no server changes.
# .\CAPTURE-LONG-SESSION.ps1 -Minutes 45 [-ProcessId 12345]
param(
 [ValidateRange(1,360)][int]$Minutes=45,
 [ValidateRange(2,30)][int]$IntervalSeconds=5,
 [string]$ProcessPattern='(?i)bbport|bloodborne',
 [ValidateRange(0,2147483647)][int]$ProcessId=0
)
$ErrorActionPreference='Stop'
$output=Join-Path $PSScriptRoot ("SH-PERF-{0}.csv" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
$deadline=(Get-Date).AddMinutes($Minutes)
$lastCpu=$null;$lastAt=$null;$chosen=$null;$samples=0
Write-Host "Recording to $output"
while((Get-Date)-lt $deadline){
 $now=Get-Date
 if($null -eq $chosen){
  $choices=@(Get-Process -ErrorAction SilentlyContinue | Where-Object {
   ($ProcessId -gt 0 -and $_.Id -eq $ProcessId) -or
   ($ProcessId -eq 0 -and $_.ProcessName -match $ProcessPattern)
  } | Sort-Object WorkingSet64 -Descending)
  if($choices.Count -eq 0){Start-Sleep -Seconds $IntervalSeconds;continue}
  $chosen=$choices[0].Id
  Write-Host "Process $($choices[0].ProcessName), PID=$chosen"
 }
 $p=Get-Process -Id $chosen -ErrorAction SilentlyContinue
 if($null -eq $p){Write-Host 'Game exited';break}
 $cpu=[double]$p.CPU;$pct=$null
 if($null -ne $lastCpu -and $null -ne $lastAt){
  $dt=($now-$lastAt).TotalSeconds
  if($dt -gt 0){$pct=[math]::Round(100*($cpu-$lastCpu)/$dt/[Environment]::ProcessorCount,2)}
 }
 $row=[pscustomobject]@{
  time=$now.ToString('o')
  process=$p.ProcessName
  process_id=$p.Id
  rss_mib=[math]::Round($p.WorkingSet64/1MB,1)
  private_mib=[math]::Round($p.PrivateMemorySize64/1MB,1)
  cpu_pct_total_machine=$pct
  handles=$p.HandleCount
  threads=$p.Threads.Count
 }
 $row | Export-Csv -Path $output -NoTypeInformation -Append -Encoding UTF8
 $samples++
 if($samples -eq 1 -or ($samples % 12 -eq 0)){
  Write-Host ("{0}: RSS {1} MiB, Private {2} MiB, CPU {3}%" -f $row.time,$row.rss_mib,$row.private_mib,$row.cpu_pct_total_machine)
 }
 $lastCpu=$cpu;$lastAt=$now
 Start-Sleep -Seconds $IntervalSeconds
}
Write-Host "Captured $samples samples: $output"
