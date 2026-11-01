$ErrorActionPreference='Stop'
$StudioHome=Join-Path $env:LOCALAPPDATA 'DedsecAI Studio'
$Entry=Join-Path $StudioHome 'app\cli.py'
$ServerScript=Join-Path $StudioHome 'app\server.py'
$Record=Join-Path $StudioHome 'state\server-process.json'
if(Test-Path $Record){
 try {
  $Owned=Get-Content -Raw -Encoding UTF8 $Record | ConvertFrom-Json
  $Process=Get-CimInstance Win32_Process -Filter ('ProcessId = '+[int]$Owned.pid)
  if($Process -and $Process.ExecutablePath -eq $Owned.executable -and $Process.CommandLine -like '*--alias*'){Stop-Process -Id $Process.ProcessId -ErrorAction Stop}
 } catch { Write-Host 'The model process was already stopped or could not be verified.' }
}
$Candidates=Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'"
foreach($Process in $Candidates){
 $Line=$Process.CommandLine
 if($Line -and (($Line.IndexOf($Entry,[StringComparison]::OrdinalIgnoreCase) -ge 0 -and $Line -match '\sserve(\s|$)') -or $Line.IndexOf($ServerScript,[StringComparison]::OrdinalIgnoreCase) -ge 0)){
  Stop-Process -Id $Process.ProcessId -ErrorAction Stop
 }
}
