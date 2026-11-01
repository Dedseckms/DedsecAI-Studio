Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "Sections.nsh"
!ifndef PAYLOAD
  !error "PAYLOAD must point to the clean application payload"
!endif
!ifndef OUTPUT
  !error "OUTPUT must be an absolute .exe path"
!endif
!ifndef VERSION
  !define VERSION "0.2.0"
!endif
Name "DedsecAI Studio"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\DedsecAI Studio"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 16
ShowInstDetails show
ShowUninstDetails show
ManifestSupportedOS Win10
VIProductVersion "0.2.0.0"
VIAddVersionKey /LANG=1033 "ProductName" "DedsecAI Studio"
VIAddVersionKey /LANG=1033 "FileDescription" "DedsecAI Studio online installer"
VIAddVersionKey /LANG=1033 "ProductVersion" "${VERSION}"
VIAddVersionKey /LANG=1033 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "DedsecAI Studio contributors"
Var SetupArgs
Var PowerShellExe
Var SetupResult
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TEXT "Install DedsecAI Studio for the current user.$\r$\n$\r$\nPython (if needed), llama.cpp and Pi are downloaded from their sources. Internet access is required.$\r$\n$\r$\nModel weights are selected and downloaded separately after installation. GPU drivers are not changed."
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchStudio
!define MUI_FINISHPAGE_RUN_TEXT "Open DedsecAI Studio"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${PAYLOAD}/LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  SetShellVarContext current
  ReadEnvStr $0 "PROCESSOR_ARCHITEW6432"
  StrCmp $0 "" 0 +2
    ReadEnvStr $0 "PROCESSOR_ARCHITECTURE"
  ${If} $0 != "AMD64"
  ${AndIf} $0 != "ARM64"
    MessageBox MB_OK|MB_ICONSTOP "DedsecAI Studio requires 64-bit Windows 10/11 (x64 or ARM64)."
    SetErrorLevel 1
    Quit
  ${EndIf}
  StrCpy $PowerShellExe "$WINDIR\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
  IfFileExists "$PowerShellExe" +2 0
    StrCpy $PowerShellExe "$SYSDIR\WindowsPowerShell\v1.0\powershell.exe"
FunctionEnd

Section "DedsecAI Studio (required)" SecCore
  SectionIn RO
  InitPluginsDir
  SetOutPath "$PLUGINSDIR\payload"
  File /r "${PAYLOAD}/*"
SectionEnd
Section "llama.cpp runtime (Vulkan / GPU)" SecRuntime
  DetailPrint "llama.cpp will be installed."
SectionEnd
Section "Pi terminal client + Node.js" SecPi
  DetailPrint "Pi and Node.js will be installed if missing."
SectionEnd
Section "Start Studio when signing in" SecStartup
  DetailPrint "The local Studio panel will start at sign-in."
SectionEnd
Section "-Install selected components"
  StrCpy $SetupArgs "-NoOpen"
  ${IfNot} ${SectionIsSelected} ${SecRuntime}
    StrCpy $SetupArgs "$SetupArgs -SkipRuntime"
  ${EndIf}
  ${IfNot} ${SectionIsSelected} ${SecPi}
    StrCpy $SetupArgs "$SetupArgs -SkipPi"
  ${EndIf}
  ${IfNot} ${SectionIsSelected} ${SecStartup}
    StrCpy $SetupArgs "$SetupArgs -NoAutostart"
  ${EndIf}
  DetailPrint "Configuring Python, Studio and selected dependencies..."
  nsExec::ExecToLog '"$PowerShellExe" -NoProfile -ExecutionPolicy Bypass -File "$PLUGINSDIR\payload\installers\install-windows.ps1" $SetupArgs'
  Pop $SetupResult
  ${If} $SetupResult != "0"
    MessageBox MB_OK|MB_ICONSTOP "Setup did not finish (code: $SetupResult). See Details and $LOCALAPPDATA\DedsecAI Studio\state\windows-setup.log. Existing user data has not been removed."
    SetErrorLevel 1
    Abort "Installation did not finish."
  ${EndIf}
  SetOutPath "$INSTDIR"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DedsecAIStudio" "DisplayName" "DedsecAI Studio"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DedsecAIStudio" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DedsecAIStudio" "Publisher" "DedsecAI"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DedsecAIStudio" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DedsecAIStudio" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DedsecAIStudio" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DedsecAIStudio" "NoRepair" 1
SectionEnd

Function LaunchStudio
  ExecShell "open" "$SMPROGRAMS\DedsecAI Studio.lnk"
FunctionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
!insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Local web application, model catalog, chat and persistent memory. Model weights are not bundled."
!insertmacro MUI_DESCRIPTION_TEXT ${SecRuntime} "Uses an existing llama-server or downloads the pinned Vulkan build. GPU drivers must already be installed."
!insertmacro MUI_DESCRIPTION_TEXT ${SecPi} "Installs the Pi coding client and a private Node.js runtime when required."
!insertmacro MUI_DESCRIPTION_TEXT ${SecStartup} "Starts only the local web panel at sign-in. A model is loaded when requested."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  SetShellVarContext current
  MessageBox MB_OKCANCEL|MB_ICONINFORMATION "Remove the application and shortcuts? Model files, chat history, memory and downloaded runtimes will be kept in $LOCALAPPDATA\DedsecAI Studio." IDOK +2
    Abort
  StrCpy $PowerShellExe "$WINDIR\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
  IfFileExists "$PowerShellExe" +2 0
    StrCpy $PowerShellExe "$SYSDIR\WindowsPowerShell\v1.0\powershell.exe"
  nsExec::ExecToLog '"$PowerShellExe" -NoProfile -ExecutionPolicy Bypass -File "$LOCALAPPDATA\DedsecAI Studio\app\installers\uninstall-windows.ps1"'
  Pop $0
  ${If} $0 != "0"
    MessageBox MB_OK|MB_ICONSTOP "Could not stop Studio. Close the application and run uninstall again. No application files were removed."
    Abort
  ${EndIf}
  Delete "$SMPROGRAMS\DedsecAI Studio.lnk"
  Delete "$SMSTARTUP\DedsecAI Studio.lnk"
  Delete "$LOCALAPPDATA\DedsecAI Studio\DedsecAI Studio.cmd"
  RMDir /r "$LOCALAPPDATA\DedsecAI Studio\app"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DedsecAIStudio"
  Delete "$LOCALAPPDATA\DedsecAI Studio\Uninstall.exe"
SectionEnd
