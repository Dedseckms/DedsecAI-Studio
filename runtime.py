"""Portable llama.cpp lifecycle. A migrated Linux installation can retain its user service."""
import contextlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time
import urllib.request
from common import HOME,CONFIG,STATE,ROOT,SERVER_PORT,read_json,write_json

HTTP=urllib.request.build_opener(urllib.request.ProxyHandler({}))

def api(path,payload=None,timeout=3):
    req=urllib.request.Request(f'http://127.0.0.1:{SERVER_PORT}'+path,data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None,headers={'Content-Type':'application/json'})
    with HTTP.open(req,timeout=timeout) as r:return json.load(r)

def healthy():
    try:api('/health',timeout=1);return True
    except OSError:return False

def binary():
    configured=read_json(CONFIG/'runtime.json',{}).get('executable')
    candidate=os.environ.get('DEDSECAI_LLAMA_SERVER') or configured or shutil.which('llama-server')
    if candidate and Path(candidate).is_file():return str(Path(candidate).resolve())
    raise ValueError('llama-server не найден. Откройте настройки и установите runtime или выполните dedsecai setup-runtime.')

def legacy():return os.name!='nt' and read_json(CONFIG/'legacy.json',{}).get('service')=='qwen-server.service'

def unit(*args,check=True):
    r=subprocess.run(['systemctl','--user',*args,'qwen-server.service'],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if check and r.returncode:raise ValueError(r.stderr.strip() or 'Не удалось управлять службой llama.cpp.')
    return r

def arguments(item):
    from manager import file_path
    args=[binary(),'-m',str(file_path(item)),'--alias',item['alias'],'-c',str(item['ctx']),'-ngl',str(item['gpu_layers']),
            '--fit-target','768','-fa','on','--cache-type-k',item['cache'],'--cache-type-v',item['cache'],
            '-t',str(item.get('threads',max(1,(os.cpu_count() or 2)//2))),'-ub',str(item['ubatch']),'--parallel','1',
            '--host','127.0.0.1','--port',str(SERVER_PORT),'--jinja','--reasoning','off','--no-reasoning-preserve',
            '--chat-template-kwargs','{"enable_thinking":false}','--temp','0.6','--top-p','0.95','--repeat-penalty','1.0','--dry-multiplier','0']
    if item.get('mmproj'):args.extend(['--mmproj',item['mmproj']])
    return args

def wait_ready(item,seconds=150,cancel=None):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if cancel is not None and cancel.is_set():raise InterruptedError('Загрузка отменена.')
        try:
            api('/health');props=api('/props');names=[r['id'] for r in api('/v1/models')['data']]
            ctx=props['default_generation_settings']['n_ctx']
            if item['alias'] not in names or ctx!=item['ctx']:raise ValueError('Сервер сообщил другую модель или контекст.')
            return
        except (OSError,KeyError):time.sleep(.5)
    raise ValueError('Модель не загрузилась вовремя. Проверьте журнал сервера и уменьшите контекст.')

def start(item,foreground=False,cancel=None):
    import imaging
    imaging.stop()
    if healthy():
        wait_ready(item,3);return
    if foreground:
        write_json(STATE/'server-process.json',{'pid':os.getpid(),'executable':binary(),'model':str(item['id'])})
        os.execv(binary(),arguments(item))
    if legacy() and not item.get('mmproj'):
        unit('reset-failed',check=False);unit('start');write_json(STATE/'server-mode.json',{'mode':'legacy'})
    else:
        args=arguments(item)
        with (STATE/'server.log').open('ab') as out:
            opts={'stdout':out,'stderr':subprocess.STDOUT,'stdin':subprocess.DEVNULL}
            if os.name=='nt':opts['creationflags']=subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW
            else:opts['start_new_session']=True
            p=subprocess.Popen(args,**opts)
        write_json(STATE/'server-mode.json',{'mode':'portable'})
        write_json(STATE/'server-process.json',{'pid':p.pid,'executable':args[0],'model':item['id']})
    wait_ready(item,cancel=cancel)

def stop():
    if legacy():unit('stop')
    record=read_json(STATE/'server-process.json',{});pid=record.get('pid')
    if not pid:
        if healthy():raise ValueError('На порту работает внешний сервер. Остановите его отдельно; приложение не завершает чужие процессы.')
        return
    if os.name=='nt':
        # Verify executable and command line before asking Windows to stop the process.
        script='$p=Get-CimInstance Win32_Process -Filter "ProcessId = '+str(int(pid))+'"; if($p -and $p.ExecutablePath -eq $env:DEDSECAI_EXPECT_EXE -and $p.CommandLine -like "*--alias*"){Stop-Process -Id $p.ProcessId -ErrorAction Stop}'
        env=dict(os.environ,DEDSECAI_EXPECT_EXE=record['executable'])
        subprocess.run(['powershell','-NoProfile','-Command',script],env=env,check=True,capture_output=True)
    else:
        proc=Path('/proc')/str(pid)
        try:
            cmd=(proc/'cmdline').read_bytes()
            exe=(proc/'exe').resolve()
            if str(exe)!=str(Path(record['executable']).resolve()) or b'--alias' not in cmd:raise ValueError('PID уже принадлежит другому процессу; остановка отменена.')
            os.kill(pid,signal.SIGTERM)
            for _ in range(100):
                try:
                    if not proc.exists() or (proc/'stat').read_text().split(') ',1)[1].startswith('Z'):return
                except OSError:return
                time.sleep(.1)
            os.kill(pid,signal.SIGKILL)
        except ProcessLookupError:return
        except FileNotFoundError:return
