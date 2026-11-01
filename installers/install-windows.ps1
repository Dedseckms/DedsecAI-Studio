[CmdletBinding()]
param([switch]$SkipRuntime,[switch]$SkipPi,[switch]$NoAutostart,[switch]$NoOpen,[ValidateSet('auto','cpu','vulkan','cuda')][string]$Backend='auto')
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$StudioSource=Split-Path -Parent $PSScriptRoot
$StudioHome=Join-Path $env:LOCALAPPDATA 'DedsecAI Studio'
$StateDir=Join-Path $StudioHome 'state'
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
$TranscriptStarted=$false
try { Start-Transcript -Path (Join-Path $StateDir 'windows-setup.log') -Append -Force | Out-Null; $TranscriptStarted=$true } catch {}
$SetupExit=0
try {
 [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
 $env:PYTHONUTF8='1'
 [Console]::OutputEncoding=New-Object System.Text.UTF8Encoding
 $OutputEncoding=[Console]::OutputEncoding
 $PythonExe=$null
 $Candidates=@((Join-Path $StudioHome 'python\python.exe'),(Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314\python.exe'),(Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),(Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'))
 $Existing=Get-Command python.exe -ErrorAction SilentlyContinue
 if($Existing -and $Existing.Source -notlike '*\WindowsApps\python.exe'){$Candidates+= $Existing.Source}
 foreach($Candidate in $Candidates){
  if(Test-Path $Candidate){
   try {
    & $Candidate (Join-Path $PSScriptRoot 'probe-python.py') 2>$null
    if($LASTEXITCODE -eq 0){$PythonExe=$Candidate;break}
   } catch {}
  }
 }
 if(-not $PythonExe){
  $Manifest=Get-Content -Raw -Encoding UTF8 (Join-Path $StudioSource 'assets\python-runtime.json') | ConvertFrom-Json
  $NativeArch=if($env:PROCESSOR_ARCHITEW6432 -eq 'ARM64' -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64'){'arm64'}else{'x64'}
  $PythonPackage=$Manifest.architectures.$NativeArch
  if(-not $PythonPackage){throw 'No supported Python installer for this Windows architecture.'}
  $DownloadDir=Join-Path $StateDir 'downloads'
  New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null
  $PythonInstaller=Join-Path $DownloadDir ('python-'+$Manifest.version+'-'+$NativeArch+'.exe')
  Write-Host 'Downloading official Python runtime...'
  Invoke-WebRequest -UseBasicParsing -Uri $PythonPackage.url -OutFile $PythonInstaller
  if((Get-FileHash -Algorithm SHA256 -LiteralPath $PythonInstaller).Hash -ne $PythonPackage.sha256){throw 'Python installer SHA-256 mismatch.'}
  $Signature=Get-AuthenticodeSignature -LiteralPath $PythonInstaller
  if($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notmatch 'Python Software Foundation'){throw 'Python installer publisher signature could not be verified.'}
  $PythonTarget=Join-Path $StudioHome 'python'
  Write-Host 'Installing Python for the current user...'
  $PythonArgs=@('/quiet','InstallAllUsers=0',('TargetDir="'+$PythonTarget+'"'),'PrependPath=0','Include_launcher=0','Include_pip=0','Include_test=0','Include_doc=0','Include_tcltk=1','Shortcuts=0')
  $Process=Start-Process -FilePath $PythonInstaller -ArgumentList $PythonArgs -Wait -PassThru
  if($Process.ExitCode -notin @(0,3010)){throw ('Python installation failed: '+$Process.ExitCode)}
  $PythonExe=Join-Path $PythonTarget 'python.exe'
  if(-not (Test-Path $PythonExe)){throw 'Python executable was not created.'}
 }
 $InstallerArgs=@((Join-Path $StudioSource 'installers\install.py'),'--backend',$Backend)
 if($SkipRuntime){$InstallerArgs+='--skip-runtime'}
 if($SkipPi){$InstallerArgs+='--skip-pi'}
 if($NoAutostart){$InstallerArgs+='--no-autostart'}
 if($NoOpen){$InstallerArgs+='--no-open'}
 & $PythonExe @InstallerArgs
 if($LASTEXITCODE -ne 0){throw 'DedsecAI Studio setup did not finish. See the error above.'}
 Write-Host 'DedsecAI Studio is installed. No model weights were downloaded.'
} catch {
 Write-Host ('SETUP ERROR: '+$_.Exception.Message)
 $SetupExit=1
} finally {
 if($TranscriptStarted){Stop-Transcript | Out-Null}
}
exit $SetupExit
