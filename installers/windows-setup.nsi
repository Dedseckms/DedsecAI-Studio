Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "Sections.nsh"
!include "FileFunc.nsh"
!ifndef PAYLOAD
  !error "PAYLOAD must point to the clean application payload"
!endif
!ifndef OUTPUT
  !error "OUTPUT must be an absolute .exe path"
!endif
!ifndef VERSION
  !define VERSION "0.4.2"
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
VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=1033 "ProductName" "DedsecAI Studio"
VIAddVersionKey /LANG=1033 "FileDescription" "DedsecAI Studio online installer"
VIAddVersionKey /LANG=1033 "ProductVersion" "${VERSION}"
VIAddVersionKey /LANG=1033 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "DedsecAI Studio contributors"
Var SetupArgs
Var PowerShellExe
Var SetupResult
BrandingText "DedsecAI Studio  /  ${VERSION}"
!define MUI_ICON "artwork/studio.ico"
!define MUI_UNICON "artwork/studio.ico"
!define MUI_BGCOLOR "101114"
!define MUI_TEXTCOLOR "F2F2F5"
!define MUI_LICENSEPAGE_BGCOLOR "191A1F"
!define MUI_WELCOMEFINISHPAGE_BITMAP "artwork/sidebar.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "artwork/sidebar.bmp"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP "artwork/header.bmp"
!define MUI_HEADER_TRANSPARENT_TEXT
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "DedsecAI Studio"
!define MUI_WELCOMEPAGE_TEXT "$(WelcomeText)"
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchStudio
!define MUI_FINISHPAGE_RUN_TEXT "$(LaunchText)"
!define MUI_PAGE_CUSTOMFUNCTION_SHOW ThemePage
!insertmacro MUI_PAGE_WELCOME
!define MUI_PAGE_CUSTOMFUNCTION_SHOW ThemePage
!insertmacro MUI_PAGE_LICENSE "${PAYLOAD}/LICENSE"
!define MUI_PAGE_CUSTOMFUNCTION_SHOW ThemePage
!insertmacro MUI_PAGE_COMPONENTS
!define MUI_PAGE_CUSTOMFUNCTION_SHOW ThemePage
!insertmacro MUI_PAGE_INSTFILES
!define MUI_PAGE_CUSTOMFUNCTION_SHOW ThemePage
!insertmacro MUI_PAGE_FINISH
!define MUI_PAGE_CUSTOMFUNCTION_SHOW un.ThemePage
!insertmacro MUI_UNPAGE_CONFIRM
!define MUI_PAGE_CUSTOMFUNCTION_SHOW un.ThemePage
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "English"
LangString WelcomeText ${LANG_RUSSIAN} "Твои модели. Твои проекты. Твои правила.$\r$\n$\r$\nСобеседник с памятью, код в Pi и генерация изображений — на твоём компьютере.$\r$\n$\r$\nВыбери компоненты на следующем шаге. Python, движок и Pi при необходимости загрузятся из официальных источников.$\r$\n$\r$\nМодели скачиваются отдельно. Драйверы видеокарты не изменяются."
LangString WelcomeText ${LANG_ENGLISH} "Your models. Your projects. Your rules.$\r$\n$\r$\nChat with memory, code with Pi and generate images on your computer.$\r$\n$\r$\nChoose components on the next page. Python, the engine and Pi are downloaded from their official sources when needed.$\r$\n$\r$\nModels are downloaded separately. GPU drivers are not changed."
LangString LaunchText ${LANG_RUSSIAN} "Открыть DedsecAI Studio"
LangString LaunchText ${LANG_ENGLISH} "Open DedsecAI Studio"
LangString CoreText ${LANG_RUSSIAN} "DedsecAI Studio (обязательно)"
LangString CoreText ${LANG_ENGLISH} "DedsecAI Studio (required)"
LangString RuntimeText ${LANG_RUSSIAN} "Движок llama.cpp — Vulkan / GPU"
LangString RuntimeText ${LANG_ENGLISH} "llama.cpp engine — Vulkan / GPU"
LangString PiText ${LANG_RUSSIAN} "Терминальный Pi + Node.js"
LangString PiText ${LANG_ENGLISH} "Pi terminal client + Node.js"
LangString StartupText ${LANG_RUSSIAN} "Запускать панель при входе в Windows"
LangString StartupText ${LANG_ENGLISH} "Start panel when signing in"

; Apply the Studio palette to each wizard page, including native child controls.
!macro StudioTheme Prefix
Function ${Prefix}ThemeTree
  Exch $0
  Push $1
  System::Call 'uxtheme::SetWindowTheme(p r0, w "", w "")'
  SetCtlColors $0 0xF2F2F5 0x101114
  System::Call 'user32::GetWindow(p r0, i 5) p.r1'
  ${DoWhile} $1 P<> 0
    Push $1
    Call ${Prefix}ThemeTree
    System::Call 'user32::GetWindow(p r1, i 2) p.r1'
  ${Loop}
  Pop $1
  Pop $0
FunctionEnd
Function ${Prefix}ThemePage
  Push $0
  Push $HWNDPARENT
  Call ${Prefix}ThemeTree
  GetDlgItem $0 $HWNDPARENT 1
  SetCtlColors $0 0x183326 0x9DE8BA
  GetDlgItem $0 $HWNDPARENT 2
  SetCtlColors $0 0xC5C5D0 0x24242B
  GetDlgItem $0 $HWNDPARENT 3
  SetCtlColors $0 0xC5C5D0 0x24242B
  Pop $0
FunctionEnd
!macroend
!insertmacro StudioTheme ""
!insertmacro StudioTheme "un."



Section "$(CoreText)" SecCore
  SectionIn RO
  InitPluginsDir
  SetOutPath "$PLUGINSDIR\payload"
  File /r "${PAYLOAD}/*"
SectionEnd
Section "$(RuntimeText)" SecRuntime
  DetailPrint "llama.cpp will be installed."
SectionEnd
Section "$(PiText)" SecPi
  DetailPrint "Pi and Node.js will be installed if missing."
SectionEnd
Section "$(StartupText)" SecStartup
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
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DedsecAIStudio" "DisplayIcon" "$INSTDIR\app\installers\artwork\studio.ico"
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
  Delete "$DESKTOP\DedsecAI Studio.lnk"
  Delete "$SMSTARTUP\DedsecAI Studio.lnk"
  Delete "$LOCALAPPDATA\DedsecAI Studio\DedsecAI Studio.cmd"
  RMDir /r "$LOCALAPPDATA\DedsecAI Studio\app"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\DedsecAIStudio"
  Delete "$LOCALAPPDATA\DedsecAI Studio\Uninstall.exe"
SectionEnd

Function .onInit
  SetShellVarContext current
  ReadEnvStr $0 "DEDSECAI_HOME"
  ${If} $0 != ""
    StrCpy $INSTDIR $0
  ${EndIf}
  ClearErrors
  ${GetOptions} $CMDLINE "/APPONLY" $0
  ${IfNot} ${Errors}
    !insertmacro UnselectSection ${SecRuntime}
    !insertmacro UnselectSection ${SecPi}
    !insertmacro UnselectSection ${SecStartup}
  ${EndIf}
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
