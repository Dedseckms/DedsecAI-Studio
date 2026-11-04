#!/usr/bin/env python3
"""DedsecAI Studio local HTTP application, standard library only."""
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import threading
import time
import sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs
from common import HOME,ROOT,APP_HOME,STATE as APP_STATE,VERSION
import manager
import hardware
import hub
import runtime
import desktop
import moderation
import companion

STATE=Path(os.environ.get('DEDSECAI_PANEL_STATE_DIR',APP_STATE/'panel'));STATE.mkdir(parents=True,exist_ok=True)
PORT=int(os.environ.get('DEDSECAI_PANEL_PORT','1236'));TOKEN=secrets.token_urlsafe(32)
ALLOWED_HOSTS={f'127.0.0.1:{PORT}',f'localhost:{PORT}'}
job_lock=threading.RLock();job=None
active_process=None
active_thread=None
submit_lock=threading.Lock()
companion.init();chat_engine=companion.ChatEngine(manager)


def project_path(value):
    if not isinstance(value,str) or not value or '\0' in value or '\n' in value:raise ValueError('Укажите папку проекта.')
    p=Path(value).expanduser()
    if not p.is_absolute():raise ValueError('Нужен полный путь к папке проекта.')
    p=p.resolve(strict=True)
    if not p.is_dir():raise ValueError('Это не папка.')
    return p

def recent():return manager.read_json(STATE/'projects.json',[])
def remember(path):manager.write_json(STATE/'projects.json',([str(path)]+[x for x in recent() if x!=str(path)])[:10])
def launch_pi(path):
    if not desktop.pi_available():raise ValueError('Pi не установлен. Откройте раздел «Система».')
    result=desktop.launch_pi(path);remember(path);return result

def tail(path,limit=8000):
    try:
        with Path(path).open('rb') as src:src.seek(max(0,Path(path).stat().st_size-limit));return src.read().decode('utf-8','replace').replace('\r','\n')
    except OSError:return ''

def submit(action,data):
    with submit_lock:return _submit(action,data)

def _submit(action,data):
    global job,active_process,active_thread
    allowed={'start','stop','restart','use','download','bench','choose','pi','chat','hf_download','url_download','local_import','choose_file','setup_runtime','setup_pi','profile','cancel','image_generate','image_setup','image_start','image_stop','image_load','image_download','image_import','image_use','image_pick','image_hf_download','text_stop','image_download_preset'}
    if not isinstance(action,str) or action not in allowed:raise ValueError('Неизвестное действие.')
    item=None;path=None
    if action in {'use','download','profile'}:
        if not isinstance(data.get('id'),str):raise ValueError('Выберите модель.')
        item=manager.model(data['id'])
    if action=='pi':path=project_path(data.get('path'))
    if action=='local_import':
        if not isinstance(data.get('path'),str):raise ValueError('Укажите файл GGUF.')
        path=Path(data['path']).expanduser().resolve(strict=True)
    preempt=action in {'stop','restart','use','profile','cancel','image_stop','image_start','image_load','image_use','text_stop'}
    with job_lock:
        previous=job if job and job['status'] in {'running','cancelling'} else None
        if previous and not preempt:raise BlockingIOError('Операция выполняется. Можно остановить её или выбрать другую модель.')
        if previous:
            previous.update(status='cancelling')
            chat_engine.cancel()
            process=active_process
            if process and process.poll() is None:
                if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10)
                else:os.killpg(process.pid,signal.SIGKILL)
    if previous and previous['action']=='chat':runtime.stop()
    if previous and active_thread:
        active_thread.join(4)
        if active_thread.is_alive():raise BlockingIOError('Остановка ещё выполняется. Повторите через несколько секунд.')
    if previous:previous.update(status='cancelled',finished=time.time())
    if action=='cancel':action='stop'
    with job_lock:
        chat_task=chat_engine.prepare(data.get('conversation'),data.get('text'),data.get('images')) if action=='chat' else None
        logfile=STATE/('operation-'+secrets.token_hex(8)+'.log');logfile.write_text('',encoding='utf-8')
        task={'id':secrets.token_hex(8),'action':action,'status':'running','started':time.time(),'result':None,'error':None,'logfile':str(logfile)}
        if chat_task:task['conversation']=chat_task['conversation']
        job=task
    def work():
        global active_process
        try:
            result=None
            if action=='chat':
                result=chat_engine.run(chat_task)
                if result['status']=='error':raise ValueError(result['error'])
            elif action in {'choose','choose_file'}:
                value=desktop.choose('directory' if action=='choose' else 'file',recent()[0] if recent() else HOME)
                result={'path':value} if value else {'cancelled':True}
            elif action=='pi':result=launch_pi(path)
            else:
                # Use a child CLI for long operations so output/progress is isolated per job.
                payload=dict(data,action=action)
                args=[sys.executable,str(ROOT/'worker.py')]
                with logfile.open('wb') as out:
                    process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=out,stderr=subprocess.STDOUT,start_new_session=os.name!='nt')
                    with job_lock:
                        active_process=process
                        if task['status'] in {'cancelled','cancelling'}:process.kill()
                    process.communicate(json.dumps(payload,ensure_ascii=False).encode())
                if process.returncode:raise ValueError(tail(logfile,1800).strip() or 'Операция не завершилась. Проверьте журнал.')
                result_line=next((line[7:] for line in reversed(tail(logfile).splitlines()) if line.startswith('RESULT ')),None)
                if result_line:result=json.loads(result_line)
            with job_lock:
                if task['status'] not in {'cancelled','cancelling'}:task.update(status='done',result=result,finished=time.time())
        except Exception as error:
            with job_lock:
                if task['status'] not in {'cancelled','cancelling'}:task.update(status='error',error=str(error),finished=time.time())
    active_process=None;active_thread=threading.Thread(target=work,daemon=True);active_thread.start();return dict(task)


def status():
    hw=hardware.detect();gpu=next((g for g in hw['gpus'] if g['vram_bytes']),None)
    gpu_view=dict(name=gpu['name'],used=(gpu['vram_bytes']-gpu['free_bytes'])//1024**2,total=gpu['vram_bytes']//1024**2,load=gpu['load'],temp=gpu['temp']) if gpu else None
    rows=[]
    for item in manager.catalog():
        rows.append(dict(id=item['id'],name=item['name'],family=item.get('family','Custom'),installed=manager.installed(item),ctx=item['ctx'],
                         gib=round((item.get('size') or 0)/1024**3,2),speed=manager.speed(item),why=item['why'],tasks=item.get('tasks',''),
                         cpu_risk=item['cpu_risk'],tier=item['tier'],cache=item['cache'],source=item.get('source',''),
                         parts=len(item.get('files',[]) or [1]),disk_fits=(item.get('size') or 0)+2*1024**3<hw['disk_free_bytes'],
                         verified=item['assessment']['verified'],kind=item.get('kind','text'),path=str(manager.file_path(item)) if manager.installed(item) else None,native_ctx=item.get('native_ctx',32768),mmproj=item.get('mmproj',''),vision=bool(item.get('mmproj')),custom_ctx=item.get('custom_ctx',False),kv_gib=round(manager.kv_gib(item),2)))
    with job_lock:current=dict(job) if job else None
    try:exe=runtime.binary()
    except ValueError:exe=None
    import resources
    resource_state=resources.snapshot()
    alias_names={m.get('alias',m['id']):m['name'] for m in manager.raw_catalog()}
    resource_state['text']['display_name']=alias_names.get(resource_state['text']['name'],resource_state['text']['name'])
    return dict(resources=resource_state,csrf=TOKEN,version=VERSION,brand='DedsecAI Studio',running=runtime.healthy(),selected=manager.selected(),gpu=gpu_view,hardware=hw,
                models=rows,projects=recent(),home=str(HOME),default_project=str(HOME/'Projects' if (HOME/'Projects').is_dir() else HOME),job=current,
                operation_log=tail(current['logfile']) if current else '',server_log=tail(manager.server_log()),runtime={'executable':exe,'pi':desktop.pi_available()},
                moderation=moderation.public(manager.selected()),data_directory=str(APP_HOME))


class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):
        if args and any(str(args[0]).startswith('GET '+p) for p in ['/api/state','/api/chat?','/api/memory']):return
        super().log_message(fmt,*args)
    def respond(self,code,payload,kind='application/json; charset=utf-8'):
        body=json.dumps(payload,ensure_ascii=False).encode() if isinstance(payload,(dict,list)) else payload
        self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
    def valid_host(self):
        if self.headers.get('Host') not in ALLOWED_HOSTS:self.respond(403,{'error':'Недопустимый адрес панели.'});return False
        return True
    def do_GET(self):
        if not self.valid_host():return
        path=urlsplit(self.path).path;query=parse_qs(urlsplit(self.path).query)
        try:
            if path=='/api/state':self.respond(200,status())
            elif path=='/api/chat':self.respond(200,companion.overview(query.get('id',[None])[0]))
            elif path=='/api/chat/trash':self.respond(200,{'conversations':companion.trashed_conversations()})
            elif path=='/api/chat/search':self.respond(200,{'results':companion.search(query.get('q',[''])[0])})
            elif path.startswith('/api/attachment/'):
                mime,raw=companion.attachment(path.rsplit('/',1)[1]);self.respond(200,raw,mime)
            elif path=='/api/memory':self.respond(200,{'memories':companion.memories(),'automatic':manager.read_json(manager.CONFIG/'memory.json',{}).get('automatic',True)})
            elif path=='/api/images/hub/search':
                import image_hub
                self.respond(200,{'results':image_hub.search(query.get('q',[''])[0],query.get('uncensored',['0'])[0]=='1')})
            elif path=='/api/images/hub/inspect':
                import image_hub
                self.respond(200,image_hub.inspect(query.get('repo',[''])[0]))
            elif path=='/api/images':
                import imaging
                self.respond(200,imaging.state())
            elif path.startswith(('/gallery/','/gallery-trash/')):
                import imaging,re
                name=path.rsplit('/',1)[1]
                if not re.fullmatch(r'[a-f0-9]{32}\.png',name):raise ValueError('Изображение не найдено.')
                directory=imaging.GALLERY.parent/'gallery-trash' if path.startswith('/gallery-trash/') else imaging.GALLERY
                self.respond(200,(directory/name).read_bytes(),'image/png')
            elif path=='/api/installers':
                manifest=manager.read_json(ROOT/'dist/manifest.json',{'files':[]})
                self.respond(200,{'files':[dict(r,url='/downloads/'+r['file']) for r in manifest['files']]})
            elif path.startswith('/downloads/'):
                manifest=manager.read_json(ROOT/'dist/manifest.json',{'files':[]})
                filename=path.removeprefix('/downloads/')
                if filename not in {r['file'] for r in manifest['files']}:
                    self.respond(404,{'error':'Установщик не найден.'})
                else:self.respond(200,(ROOT/'dist'/filename).read_bytes(),'application/octet-stream')
            elif path=='/api/policy':self.respond(200,moderation.public(query.get('model',[manager.selected()])[0]))
            elif path=='/api/hub/search':self.respond(200,{'results':hub.search_repos(query.get('q',[''])[0])})
            elif path=='/api/hub/inspect':
                info=hub.inspect_repo(query.get('repo',[''])[0]);hw=hardware.detect()
                for variant in info['variants']:variant['assessment']=hardware.plan({'size':variant['size']},hw)
                self.respond(200,info)
            elif path in {'/','/app.js','/style.css','/chat.js','/chat.css','/studio.js','/studio.css','/brand.svg','/terminal.css','/features.js'}:
                name='index.html' if path=='/' else path[1:]
                kind='image/svg+xml' if name.endswith('.svg') else 'text/html' if name.endswith('.html') else 'text/javascript' if name.endswith('.js') else 'text/css'
                self.respond(200,(ROOT/'static'/name).read_bytes(),kind+'; charset=utf-8')
            elif path=='/favicon.ico':self.respond(204,b'','image/x-icon')
            else:self.respond(404,{'error':'Не найдено.'})
        except (ValueError,OSError,KeyError) as exc:self.respond(400,{'error':str(exc)})
    def do_POST(self):
        if not self.valid_host():return
        origin=self.headers.get('Origin')
        if (origin and origin!='http://'+self.headers.get('Host','')) or not secrets.compare_digest(self.headers.get('X-Qwen-Token',''),TOKEN):self.respond(403,{'error':'Обновите страницу панели.'});return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=34*1024*1024:raise ValueError('Неверный размер запроса.')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict):raise ValueError('Ожидается объект JSON.')
            if self.path=='/api/chat/new':self.respond(200,companion.create())
            elif self.path=='/api/chat/send':self.respond(202,{'job':submit('chat',data)})
            elif self.path=='/api/chat/delete':
                with submit_lock:self.respond(200,companion.remove_conversation(data.get('id')))
            elif self.path=='/api/chat/restore':self.respond(200,companion.restore_conversation(data.get('id')))
            elif self.path=='/api/chat/stop':chat_engine.cancel();self.respond(200,{'stopping':True})
            elif self.path=='/api/images/delete':
                import imaging
                self.respond(200,imaging.gallery_remove(data.get('file')))
            elif self.path=='/api/images/restore':
                import imaging
                self.respond(200,imaging.gallery_restore(data.get('file')))
            elif self.path=='/api/memory/settings':
                manager.write_json(manager.CONFIG/'memory.json',{'automatic':data.get('automatic') is True});self.respond(200,{'saved':True})
            elif self.path=='/api/memory/save':self.respond(200,{'id':companion.save_memory(data.get('content'),data.get('id')),'memories':companion.memories()})
            elif self.path=='/api/policy':self.respond(200,moderation.save(data))
            elif self.path=='/api/action':self.respond(202,{'job':submit(data.get('action'),data)})
            else:self.respond(404,{'error':'Не найдено.'})
        except BlockingIOError as exc:self.respond(409,{'error':str(exc)})
        except (ValueError,OSError,KeyError) as exc:self.respond(400,{'error':str(exc)})

if __name__=='__main__':
    manager.refresh_installed_metadata()
    companion.init(recover=True)
    print(f'DedsecAI Studio: http://127.0.0.1:{PORT}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
