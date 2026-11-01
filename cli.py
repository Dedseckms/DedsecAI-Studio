#!/usr/bin/env python3
"""DedsecAI Studio command-line entry point, Windows/Linux."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser
from common import ROOT,APP_HOME,CONFIG,STATE,VERSION,read_json,lock
import manager
import runtime


def web(open_browser=True):
    port=int(os.environ.get('DEDSECAI_PANEL_PORT','1236'));url=f'http://127.0.0.1:{port}'
    try:urllib.request.urlopen(url+'/api/state',timeout=2)
    except OSError:
        log=(STATE/'panel.log').open('ab')
        kwargs={'stdin':subprocess.DEVNULL,'stdout':log,'stderr':log}
        if os.name=='nt':kwargs['creationflags']=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP
        else:kwargs['start_new_session']=True
        subprocess.Popen([sys.executable,str(ROOT/'server.py')],**kwargs);log.close()
        for _ in range(80):
            try:urllib.request.urlopen(url+'/api/state',timeout=.5);break
            except OSError:time.sleep(.2)
        else:raise ValueError('Панель не запустилась. Журнал: '+str(STATE/'panel.log'))
    if open_browser:webbrowser.open(url)
    print('DedsecAI Studio: '+url)


def pi(project):
    import desktop
    project=Path(project).expanduser().resolve(strict=True)
    if not project.is_dir():raise ValueError('Выберите папку проекта.')
    with lock():
        manager.start();item=manager.model(manager.selected());manager.sync_pi(item)
    os.chdir(project)
    command=desktop.pi_command()+['--offline','--provider','lmstudio','--model',item['alias'],'--thinking','off']
    if os.name=='nt':command.extend(['--tools','read,edit,write,powershell'])
    env=dict(os.environ,NO_PROXY='localhost,127.0.0.1,::1',no_proxy='localhost,127.0.0.1,::1')
    node=read_json(CONFIG/'node.json',{}).get('executable')
    if not node:
        candidate=Path.home()/'.local/share/pi-node/current/bin/node'
        if candidate.exists():node=str(candidate)
    if node:env['PATH']=str(Path(node).parent)+os.pathsep+env.get('PATH','')
    subprocess.run(command,env=env,check=True)


def main():
    p=argparse.ArgumentParser(description='DedsecAI Studio — локальные модели на вашем ПК')
    p.add_argument('--version',action='version',version=VERSION)
    s=p.add_subparsers(dest='cmd')
    w=s.add_parser('web');w.add_argument('--no-open',action='store_true')
    s.add_parser('init').add_argument('--migrate',action='store_true')
    s.add_parser('hardware')
    s.add_parser('serve')
    r=s.add_parser('setup-runtime');r.add_argument('--backend',choices=['auto','cpu','vulkan','cuda'],default='auto')
    s.add_parser('setup-pi')
    pp=s.add_parser('pi');pp.add_argument('--project',default=str(Path.cwd()))
    sv=s.add_parser('server');sv.add_argument('action',choices=['start','stop','restart','foreground','status'])
    models=s.add_parser('models');models.add_argument('action',nargs='?',default='list',choices=['list','active','info','download','use','bench','add']);models.add_argument('id',nargs='?');models.add_argument('--allow-cpu',action='store_true')
    a=p.parse_args()
    if a.cmd in (None,'web'):web(not getattr(a,'no_open',False))
    elif a.cmd=='init':
        if a.migrate:manager.migrate()
        print('Данные приложения: '+str(APP_HOME))
    elif a.cmd=='serve':
        import server
        manager.refresh_installed_metadata()
        server.companion.init(recover=True)
        server.ThreadingHTTPServer(('127.0.0.1',server.PORT),server.Handler).serve_forever()
    elif a.cmd=='hardware':print(__import__('json').dumps(__import__('hardware').detect(),ensure_ascii=False,indent=2))
    elif a.cmd=='setup-runtime':__import__('bootstrap').setup_runtime(a.backend)
    elif a.cmd=='setup-pi':__import__('bootstrap').setup_pi()
    elif a.cmd=='pi':pi(a.project)
    elif a.cmd=='server':
        if a.action=='status':print('работает' if runtime.healthy() else 'остановлен')
        elif a.action=='stop':runtime.stop()
        elif a.action=='foreground':manager.start(foreground=True)
        else:
            with lock():
                if a.action=='restart':runtime.stop()
                manager.start()
    elif a.cmd=='models':
        if a.action=='list':
            for item in manager.catalog():print(item['id'],item['name'],item['tier'],manager.speed(item))
        elif a.action=='active':print(manager.model(manager.selected())['alias'])
        elif a.action=='info':print(__import__('json').dumps(manager.model(a.id),ensure_ascii=False,indent=2))
        else:
            with lock():
                if a.action=='download':manager.download(manager.model(a.id))
                elif a.action=='use':manager.activate(manager.model(a.id),a.allow_cpu)
                elif a.action=='bench':manager.benchmark(manager.model(a.id or manager.selected()))
                elif a.action=='add':print(manager.add(a.id)['id'])

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
        print('Ошибка: '+str(exc),file=sys.stderr);sys.exit(1)
