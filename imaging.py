"""Local stable-diffusion.cpp service, recipe selection and durable gallery."""
import base64
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
import urllib.parse
from common import APP_HOME,CONFIG,STATE,ROOT,read_json,write_json
import bootstrap

PORT=int(os.environ.get('DEDSECAI_IMAGE_PORT','1237'))
MODEL_DIR=APP_HOME/'image-models'
GALLERY=APP_HOME/'gallery'
HTTP=urllib.request.build_opener(urllib.request.ProxyHandler({}))

def api(path,payload=None,timeout=5):
    req=urllib.request.Request(f'http://127.0.0.1:{PORT}'+path,data=json.dumps(payload).encode() if payload is not None else None,headers={'Content-Type':'application/json'})
    try:
        with HTTP.open(req,timeout=timeout) as response:return json.load(response)
    except urllib.error.HTTPError as exc:
        detail=exc.read(8192).decode('utf-8','replace')
        raise ValueError('Image-сервер: '+detail) from exc

def binary():
    value=read_json(CONFIG/'image-runtime.json',{}).get('executable') or shutil.which('sd-server')
    return value if value and Path(value).is_file() else None

def setup(backend='vulkan'):
    if backend not in {'vulkan','cpu'}:raise ValueError('Выберите Vulkan или CPU.')
    if platform.machine().lower() not in {'x86_64','amd64'}:raise ValueError('Автоустановка image-runtime пока доступна для x64. Установите sd-server самостоятельно.')
    manifest=read_json(ROOT/'assets/image-runtime.json')
    suffix=f'bin-win-{backend}-x64.zip' if os.name=='nt' else 'bin-Linux-Ubuntu-24.04-x86_64'+('-vulkan' if backend=='vulkan' else '')+'.zip'
    asset=next(a for a in manifest['assets'] if a['name'].endswith(suffix))
    if not asset.get('digest'):raise ValueError('Отсутствует SHA-256 image-runtime.')
    archive=bootstrap.fetch(asset['url'],STATE/'downloads'/asset['name'],asset['digest'])
    dest=APP_HOME/'image-runtime'/manifest['tag']/backend;bootstrap.extract(archive,dest)
    exe=next(dest.rglob('sd-server.exe' if os.name=='nt' else 'sd-server'),None)
    if exe is None:raise ValueError('Архив не содержит sd-server.')
    if os.name!='nt':exe.chmod(0o755)
    try:subprocess.run([str(exe),'--version'],check=True,capture_output=True,timeout=15)
    except (OSError,subprocess.SubprocessError):
        if os.name=='nt':raise ValueError('Image-runtime не запускается. Проверьте драйвер Vulkan или выберите CPU.')
        for tool in ['git','cmake','c++']:
            if not shutil.which(tool):raise ValueError('Готовый image-runtime несовместим с этой ОС. Для сборки нужны git, cmake и C++.')
        source=APP_HOME/'image-runtime'/manifest['tag']/'source'
        if not (source/'.git').exists():subprocess.run(['git','clone','--depth','1','--branch',manifest['tag'],'https://github.com/leejet/stable-diffusion.cpp',str(source)],check=True)
        subprocess.run(['git','-C',str(source),'submodule','update','--init','--recursive','--depth','1'],check=True)
        build=dest/'build'
        subprocess.run(['cmake','-S',str(source),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DSD_WEBP=OFF','-DSD_WEBM=OFF','-DSD_VULKAN='+('ON' if backend=='vulkan' else 'OFF')],check=True)
        subprocess.run(['cmake','--build',str(build),'--target','sd-server','-j',str(min(4,os.cpu_count() or 2))],check=True)
        exe=next(build.rglob('sd-server'))
    write_json(CONFIG/'image-runtime.json',{'executable':str(exe),'backend':backend})
    return {'message':'Движок изображений установлен.'}

def stop():
    record=read_json(STATE/'image-process.json',{});pid=record.get('pid')
    if not pid:return
    if os.name=='nt':
        env=dict(os.environ,DEDSECAI_IMAGE_EXE=record['executable'])
        subprocess.run(['powershell','-NoProfile','-Command','$p=Get-CimInstance Win32_Process -Filter "ProcessId = '+str(int(pid))+'";if($p -and $p.ExecutablePath -eq $env:DEDSECAI_IMAGE_EXE){Stop-Process -Id $p.ProcessId -Force}'],env=env,check=True,capture_output=True)
    else:
        proc=Path('/proc')/str(pid)
        try:
            if (proc/'exe').resolve()!=Path(record['executable']).resolve():
                if not proc.exists():return
                raise ValueError('PID image-сервера принадлежит другому процессу.')
            os.kill(pid,signal.SIGKILL)
        except (ProcessLookupError,FileNotFoundError):pass

def start():
    try:api('/sdcpp/v1/recipes');return {'message':'Image-сервер готов.'}
    except (OSError,ValueError):pass
    exe=binary()
    if not exe:raise ValueError('Сначала установите движок изображений.')
    # Release text weights before allocating diffusion VRAM on the same computer.
    import runtime
    runtime.stop();MODEL_DIR.mkdir(parents=True,exist_ok=True)
    args=[exe,'--listen-ip','127.0.0.1','--listen-port',str(PORT),'--model-dir',str(MODEL_DIR)]
    with (STATE/'image-server.log').open('ab') as out:
        opts={'stdout':out,'stderr':subprocess.STDOUT,'stdin':subprocess.DEVNULL}
        if os.name=='nt':opts['creationflags']=subprocess.CREATE_NO_WINDOW
        else:opts['start_new_session']=True
        process=subprocess.Popen(args,**opts)
    write_json(STATE/'image-process.json',{'pid':process.pid,'executable':exe})
    for _ in range(60):
        if process.poll() is not None:raise ValueError('Image-сервер завершился. '+(STATE/'image-server.log').read_text(errors='replace')[-1600:])
        try:api('/sdcpp/v1/recipes');return {'message':'Image-сервер готов. Выберите рецепт и файлы модели.'}
        except (OSError,ValueError):time.sleep(.5)
    raise ValueError('Image-сервер не ответил за 30 секунд.')

def state():
    result={'installed':bool(binary()),'running':False,'model_dir':str(MODEL_DIR),'gallery':read_json(STATE/'gallery.json',[])}
    try:
        result.update(running=True,recipes=api('/sdcpp/v1/recipes'),files=api('/sdcpp/v1/model-files'),model=api('/sdcpp/v1/models/status'))
    except (OSError,ValueError):result['running']=False
    return result

def download(data):
    import hub
    url=hub.validate_url(data.get('url'));name=Path(urllib.request.url2pathname(urllib.parse.urlsplit(url).path)).name
    if not re.fullmatch(r'[\w. -]{1,180}\.(?:gguf|safetensors|ckpt)',name,re.I):raise ValueError('Нужна прямая ссылка на GGUF, safetensors или ckpt.')
    category=data.get('category','checkpoints')
    if category not in {'checkpoints','diffusion_models','text_encoders','vae','loras'}:raise ValueError('Неизвестная категория весов.')
    dest=MODEL_DIR/category/name;dest.parent.mkdir(parents=True,exist_ok=True)
    expected=data.get('sha256') or None
    if expected and not re.fullmatch('[a-fA-F0-9]{64}',expected):raise ValueError('Неверный SHA-256.')
    if dest.exists():raise ValueError('Такой файл уже есть: '+str(dest))
    part=dest.with_suffix(dest.suffix+'.part')
    have=part.stat().st_size if part.exists() else 0
    headers={'Range':f'bytes={have}-'} if have else {}
    if os.environ.get('HF_TOKEN') and urllib.parse.urlsplit(url).hostname=='huggingface.co':headers['Authorization']='Bearer '+os.environ['HF_TOKEN']
    with hub.HTTP.open(urllib.request.Request(url,headers=headers),timeout=60) as src,part.open('ab') as out:
        if have and (src.status!=206 or not src.headers.get('Content-Range','').startswith(f'bytes {have}-')):raise ValueError('Источник не поддержал докачку. Частичный файл сохранён.')
        expected_bytes=int(src.headers.get('Content-Length','0'));received=0
        for chunk in iter(lambda:src.read(2*1024*1024),b''):
            if shutil.disk_usage(MODEL_DIR).free<len(chunk)+2*1024**3:raise ValueError('Недостаточно свободного места.')
            out.write(chunk);received+=len(chunk)
        if expected_bytes and received!=expected_bytes:raise ValueError('Загрузка неполная; повторите для докачки.')
    from common import digest_file
    if expected and digest_file(part).lower()!=expected.lower():raise ValueError('SHA-256 не совпал. Файл не установлен.')
    os.replace(part,dest)
    try:api('/sdcpp/v1/models/refresh',{})
    except (OSError,ValueError):pass
    return {'message':'Веса изображения скачаны: '+name}

def run(action,data):
    if action=='image_setup':return setup(data.get('backend','vulkan'))
    if action=='image_start':return start()
    if action=='image_stop':stop();return {'message':'Image-сервер остановлен.'}
    if action=='image_download':return download(data)
    if action=='image_import':return import_model(data.get('path'),data.get('category','diffusion_models'))
    if action=='image_load':
        payload={'recipe':data.get('recipe'),'models':data.get('models',{})}
        result=api('/sdcpp/v1/models/load',payload,timeout=240)
        if result.get('state')!='ready':raise ValueError('Image-модель не загрузилась: '+str(result.get('error') or result.get('state')))
        # A real short generation measures the newly loaded image model automatically.
        try:
            measured=generate({'prompt':'a small green cube on a black background','size':'512x512'},benchmark=True)
            message='Image-модель загружена и проверена. '+str(measured['seconds'])+' с на тест.'
        except Exception as exc:message='Модель загружена. Автозамер не выполнен: '+str(exc)
        return {'message':message,'model':result}
    if action=='image_generate':return generate(data)
    raise ValueError('Неизвестная image-операция.')

def generate(data,benchmark=False):
    prompt=data.get('prompt','');size=data.get('size','512x512')
    if not isinstance(prompt,str) or not 1<=len(prompt)<=4000:raise ValueError('Описание: от 1 до 4000 символов.')
    if size not in {'256x256','512x512','768x768','1024x1024'}:raise ValueError('Выберите доступное разрешение.')
    start_time=time.monotonic()
    result=api('/v1/images/generations',{'prompt':prompt,'n':1,'size':size,'output_format':'png'},timeout=600)
    elapsed=round(time.monotonic()-start_time,2)
    GALLERY.mkdir(parents=True,exist_ok=True)
    import secrets
    name=secrets.token_hex(16)+'.png';raw=base64.b64decode(result['data'][0]['b64_json'],validate=True)
    if not raw.startswith(b'\x89PNG'):raise ValueError('Сервер вернул неверный PNG.')
    (GALLERY/name).write_bytes(raw)
    entry={'file':name,'prompt':prompt,'seconds':elapsed,'size':size,'benchmark':benchmark,'created':time.time()}
    rows=read_json(STATE/'gallery.json',[]);rows.insert(0,entry);write_json(STATE/'gallery.json',rows)
    return dict(entry,message='Изображение готово за '+str(elapsed)+' с.')


def import_model(value,category='diffusion_models'):
    path=Path(value).expanduser().resolve(strict=True)
    if path.suffix.lower() not in {'.gguf','.safetensors','.ckpt'} or not path.is_file():raise ValueError('Выберите GGUF, safetensors или ckpt.')
    if category not in {'checkpoints','diffusion_models','text_encoders','vae','loras'}:raise ValueError('Неизвестная категория.')
    dest=MODEL_DIR/category/path.name;dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():
        if not os.path.samefile(path,dest):raise ValueError('Файл с таким именем уже есть в image-models.')
    else:
        try:os.link(path,dest)
        except OSError as exc:raise ValueError('Нельзя создать ссылку между этими дисками. Скопируйте файл в '+str(dest.parent)) from exc
    try:api('/sdcpp/v1/models/refresh',{})
    except (OSError,ValueError):pass
    return {'message':'Веса доступны в «Изображения». Оригинал сохранён; дополнительное место для весов не занято. Выберите рецепт и необходимые энкодеры/VAE. Скорость измерится после загрузки модели.'}
