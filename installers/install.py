#!/usr/bin/env python3
"""Per-user installation; no model/user data deletion, no system-wide Python packages."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

SOURCE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SOURCE))
from common import APP_HOME,HOME,STATE,VERSION,write_json

FILES=['common.py','hardware.py','hub.py','gguf.py','runtime.py','manager.py','moderation.py','desktop.py','bootstrap.py','cli.py','server.py','worker.py','companion.py','imaging.py','resources.py','image_hub.py','build.py','README.md','LICENSE']
DIRS=['assets','static','pi-extensions','installers','packaging']

def quote(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'

def shortcut(path,python,entry,argument):
    script='$s=New-Object -ComObject WScript.Shell; $l=$s.CreateShortcut($env:DS_SHORTCUT); $l.TargetPath=$env:DS_PYTHON; $l.Arguments=$env:DS_ARGS; $l.WorkingDirectory=$env:DS_WORKDIR; $l.Description="DedsecAI Studio"; $l.Save()'
    env=dict(os.environ,DS_SHORTCUT=str(path),DS_PYTHON=str(python),DS_ARGS='"'+str(entry)+'" '+argument,DS_WORKDIR=str(entry.parent))
    path.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['powershell','-NoProfile','-Command',script],env=env,check=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--skip-runtime',action='store_true');p.add_argument('--skip-pi',action='store_true');p.add_argument('--no-autostart',action='store_true');p.add_argument('--no-open',action='store_true');p.add_argument('--migrate',action='store_true');p.add_argument('--dry-run',action='store_true');p.add_argument('--backend',choices=['auto','cpu','vulkan','cuda'],default='auto')
    args=p.parse_args();dest=APP_HOME/'app'
    if args.dry_run:
        print(json.dumps({'destination':str(dest),'files':FILES,'directories':DIRS,'runtime':not args.skip_runtime,'pi':not args.skip_pi,'autostart':not args.no_autostart,'models_downloaded':False},indent=2));return
    if os.name!='nt' and hasattr(os,'geteuid') and os.geteuid()==0:raise ValueError('Запустите установщик от обычного пользователя. sudo нужен только менеджеру системных пакетов.')
    if SOURCE.resolve()!=dest.resolve():
        if dest.exists():shutil.copytree(dest,APP_HOME/'backups'/('app-'+str(int(time.time()))),dirs_exist_ok=True)
        dest.mkdir(parents=True,exist_ok=True)
        for name in FILES:
            if (SOURCE/name).exists():shutil.copy2(SOURCE/name,dest/name)
        for name in DIRS:shutil.copytree(SOURCE/name,dest/name,dirs_exist_ok=True)
        if (SOURCE/'dist').exists():shutil.copytree(SOURCE/'dist',dest/'dist',dirs_exist_ok=True)
    entry=dest/'cli.py';python=Path(sys.executable)
    subprocess.run([str(python),str(dest/'build.py')],check=True)
    if args.migrate:subprocess.run([str(python),str(entry),'init','--migrate'],check=True)
    else:subprocess.run([str(python),str(entry),'init'],check=True)
    if not args.skip_runtime:subprocess.run([str(python),str(entry),'setup-runtime','--backend',args.backend],check=True)
    if not args.skip_pi:subprocess.run([str(python),str(entry),'setup-pi'],check=True)
    if os.name=='nt':
        gui=python.with_name('pythonw.exe')
        if not gui.exists():gui=python
        programs=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs'
        shortcut(programs/'DedsecAI Studio.lnk',gui,entry,'web')
        if not args.no_autostart:shortcut(programs/'Startup/DedsecAI Studio.lnk',gui,entry,'serve')
        launcher=APP_HOME/'DedsecAI Studio.cmd'
        launcher.write_text('@echo off\r\n"'+str(python)+'" "'+str(entry)+'" web\r\n',encoding='utf-8')
    else:
        bin_dir=HOME/'.local/bin';bin_dir.mkdir(parents=True,exist_ok=True)
        launcher=bin_dir/'dedsecai';launcher.write_text('#!/bin/sh\nexec '+__import__('shlex').quote(str(python))+' '+__import__('shlex').quote(str(entry))+' "$@"\n');launcher.chmod(0o755)
        apps=HOME/'.local/share/applications';apps.mkdir(parents=True,exist_ok=True)
        (apps/'dedsecai-studio.desktop').write_text('[Desktop Entry]\nType=Application\nName=DedsecAI Studio\nComment=Локальные модели, память и проекты\nExec='+quote(python)+' '+quote(entry)+' web\nIcon=applications-development\nTerminal=false\nCategories=Development;\n',encoding='utf-8')
        if not args.no_autostart and shutil.which('systemctl') and os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
            units=HOME/'.config/systemd/user';units.mkdir(parents=True,exist_ok=True)
            (units/'dedsecai-studio.service').write_text('[Unit]\nDescription=DedsecAI Studio local application\n[Service]\nType=simple\nExecStart='+quote(python)+' '+quote(entry)+' serve\nRestart=on-failure\nRestartSec=2\nEnvironment=PYTHONUTF8=1\n[Install]\nWantedBy=default.target\n',encoding='utf-8')
            subprocess.run(['systemctl','--user','daemon-reload'],check=True)
            subprocess.run(['systemctl','--user','enable','--now','dedsecai-studio.service'],check=True)
    write_json(STATE/'installation.json',{'version':VERSION,'source':str(dest),'platform':sys.platform,'runtime_configured':not args.skip_runtime,'pi_configured':not args.skip_pi})
    print('DedsecAI Studio установлена. Модели не скачивались. Данные: '+str(APP_HOME))
    if not args.no_open:subprocess.run([str(python),str(entry),'web'],check=True)

if __name__=='__main__':
    try:main()
    except Exception as exc:print('Установка не завершена: '+str(exc),file=sys.stderr);sys.exit(1)
