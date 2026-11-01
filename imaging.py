"""Local stable-diffusion.cpp service, recipe selection and durable gallery."""
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import struct
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
    result={'installed':bool(binary()),'running':False,'model_dir':str(MODEL_DIR),'gallery':read_json(STATE/'gallery.json',[]),'library':library()}
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
    if dest.exists():
        from common import digest_file
        if (not data.get('size') or dest.stat().st_size==data['size']) and expected and digest_file(dest).lower()==expected.lower():return {'message':'Файл уже скачан и проверен: '+name}
        raise ValueError('Такой файл уже есть, но его соответствие загрузке не подтверждено: '+str(dest))
    part=dest.with_suffix(dest.suffix+'.part')
    have=part.stat().st_size if part.exists() else 0
    headers={'Range':f'bytes={have}-'} if have else {}
    if os.environ.get('HF_TOKEN') and urllib.parse.urlsplit(url).hostname=='huggingface.co':headers['Authorization']='Bearer '+os.environ['HF_TOKEN']
    if data.get('size') and have>data['size']:raise ValueError('Частичный файл больше ожидаемого; он сохранён: '+str(part))
    print('Компонент: '+name,flush=True)
    if not (data.get('size') and have==data['size']):
        with hub.HTTP.open(urllib.request.Request(url,headers=headers),timeout=60) as src,part.open('ab') as out:
            if have and (src.status!=206 or not src.headers.get('Content-Range','').startswith(f'bytes {have}-')):raise ValueError('Источник не поддержал докачку. Частичный файл сохранён.')
            expected_bytes=int(src.headers.get('Content-Length','0'));received=0;reported=0
            if expected_bytes and shutil.disk_usage(MODEL_DIR).free<expected_bytes+2*1024**3:raise ValueError('Недостаточно места для компонента и резерва 2 ГиБ.')
            for chunk in iter(lambda:src.read(2*1024*1024),b''):
                if shutil.disk_usage(MODEL_DIR).free<len(chunk)+2*1024**3:raise ValueError('Недостаточно свободного места.')
                out.write(chunk);received+=len(chunk)
                if received-reported>=128*1024**2:
                    print(name+': '+str(round((have+received)/1024**3,2))+' ГиБ',flush=True);reported=received
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
    if action=='image_use':return use_library(data.get('id'))
    if action=='image_pick':
        import desktop
        value=desktop.choose('image',MODEL_DIR)
        if not value:return {'cancelled':True}
        return import_model(value,guess_category(value))
    if action=='image_load':
        payload={'recipe':data.get('recipe'),'models':dict(data.get('models',{}))}
        if payload['recipe'] in read_json(ROOT/'assets/image-components.json',{'recipes':{}})['recipes']:
            recipe=next((r for r in api('/sdcpp/v1/recipes')['recipes'] if r['id']==payload['recipe']),None)
            if recipe:
                payload['models']=resolve_components(recipe,payload['models'],api('/sdcpp/v1/model-files')['files'])
                missing=missing_components(recipe,payload['models'])
                if missing:raise ValueError('Не хватает компонентов модели: '+', '.join(missing))
        print('Загружаем модель и совместимые компоненты: '+str(payload['recipe']),flush=True)
        result=api('/sdcpp/v1/models/load',payload,timeout=240)
        if result.get('state')!='ready':raise ValueError('Image-модель не загрузилась: '+str(result.get('error') or result.get('state')))
        # A real short generation measures the newly loaded image model automatically.
        try:
            print('Автозамер: создаём тестовое изображение 512×512.',flush=True)
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
        except OSError:
            if shutil.disk_usage(dest.parent).free<path.stat().st_size+2*1024**3:raise ValueError('Не хватает места для импорта с другого диска.')
            print('Копируем модель с другого диска; исходный файл остаётся на месте.',flush=True)
            partial=dest.with_suffix(dest.suffix+'.import.part');shutil.copyfile(path,partial);os.replace(partial,dest)
    try:api('/sdcpp/v1/models/refresh',{})
    except (OSError,ValueError):pass
    register_local(dest)
    return {'message':'Веса доступны в «Изображения». Оригинал сохранён; дополнительное место для весов не занято. Выберите рецепт и необходимые энкодеры/VAE. Скорость измерится после загрузки модели.'}


def guess_category(value):
    name=Path(value).name.lower()
    if any(x in name for x in ['sd_turbo','sd-turbo','sd_xl','sdxl','v1-5','sd15']):return 'checkpoints'
    return 'diffusion_models'


def guess_recipe(value):
    name=Path(value).name.lower()
    for entry in read_json(ROOT/'assets/image-catalog.json')['models']:
        if any(c['file'].lower()==name for c in entry['components']):return entry['recipe']
    if 'sdxl' in name or 'sd_xl' in name:return 'sdxl-turbo' if 'turbo' in name else 'sdxl-checkpoint'
    if 'sd-turbo' in name or 'sd_turbo' in name:return 'sd-turbo'
    if 'v1-5' in name or 'sd15' in name:return 'sd1-checkpoint'
    arch=''
    if Path(value).suffix.lower()=='.gguf':
        from gguf import gguf_info
        arch=gguf_info(Path(value)).get('general.architecture','')
    if arch in {'sd1','sd15'}:return 'sd1-checkpoint'
    if arch=='sdxl':return 'sdxl-checkpoint'
    if Path(value).suffix.lower()=='.safetensors':
        try:
            with Path(value).open('rb') as src:
                length=struct.unpack('<Q',src.read(8))[0]
                header=json.loads(src.read(length)) if 0<length<=32*1024*1024 else {}
            if any(k.startswith('conditioner.embedders.1.') for k in header):return 'sdxl-checkpoint'
            embedding=header.get('cond_stage_model.transformer.text_model.embeddings.token_embedding.weight',{})
            if embedding.get('shape',[0,0])[-1]==768:return 'sd1-checkpoint'
        except (OSError,ValueError,struct.error,AttributeError):pass
    if 'qwen_image21' in arch or 'qwen-image-2.1' in name:return 'qwen-image-21'
    if 'qwen_image' in arch or 'qwen-image' in name:return 'qwen-image'
    if 'flux' in arch or 'flux' in name:return 'flux1-schnell' if 'schnell' in name else 'flux1-dev'
    return None


def register_local(path):
    rows=read_json(CONFIG/'image-library.json',[])
    ident='local-'+hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]
    if any(c['file']==path.name for r in read_json(ROOT/'assets/image-catalog.json')['models'] for c in r['components']):return
    if any(r['id']==ident for r in rows):return
    rows.append({'id':ident,'name':path.stem,'recipe':guess_recipe(path),'path':str(path),'local':True})
    write_json(CONFIG/'image-library.json',rows)


def library():
    import hardware,manager
    rows=read_json(ROOT/'assets/image-catalog.json')['models']+read_json(CONFIG/'image-library.json',[])
    registered={str(Path(r['path']).resolve()) for r in rows if r.get('path')}
    known={c['file'] for r in rows for c in r.get('components',[])}|{Path(r['path']).name for r in rows if r.get('path')}
    for category in ['checkpoints','diffusion_models']:
        for path in sorted((MODEL_DIR/category).glob('*')):
            if path.is_file() and path.suffix.lower() in {'.gguf','.safetensors','.ckpt'} and path.name not in known:
                rows.append({'id':'file-'+hashlib.sha256(str(path).encode()).hexdigest()[:16],'name':path.stem,'path':str(path),'local':True,'recipe':guess_recipe(path)})
                known.add(path.name);registered.add(str(path.resolve()))
    # Show image weights already imported through the main model catalog as well.
    for item in manager.raw_catalog():
        if item.get('kind')=='image' and manager.installed(item):
            path=manager.file_path(item)
            if str(path.resolve()) not in registered and path.name not in known:
                rows.append({'id':'model-'+item['id'],'name':item['name'],'path':str(path),'local':True,'recipe':guess_recipe(path)})
                registered.add(str(path.resolve()))
    hw=hardware.detect();vram=max((g.get('vram_bytes',0) for g in hw['gpus']),default=0)/1024**3
    result=[]
    for row in rows:
        entry=dict(row);components=entry.get('components',[])
        if components:
            entry['installed']=all((MODEL_DIR/c['category']/c['file']).is_file() and (MODEL_DIR/c['category']/c['file']).stat().st_size==c['size'] for c in components)
            size=sum(c['size'] for c in components)
        else:
            path=Path(entry['path']);entry['installed']=path.is_file();size=path.stat().st_size if path.is_file() else 0
        dependencies=read_json(ROOT/'assets/image-components.json',{'recipes':{}})['recipes'].get(entry.get('recipe'),[])
        extra=sum(c['size'] for c in dependencies if not (MODEL_DIR/c['category']/c['file']).is_file())
        entry['dependency_gib']=round(extra/1024**3,2)
        entry['gib']=round(size/1024**3,2)
        entry['fits_disk']=(0 if entry['installed'] else size)+extra+2*1024**3<hw['disk_free_bytes']
        target=entry.get('min_vram_gib')
        entry['assessment']=('Ориентир: комфортно на GPU этого ПК.' if target and vram>=target else 'Может потребоваться CPU или выгрузка части весов; будет медленнее.' if target else 'Свой файл: требования зависят от модели и её компонентов.')
        if dependencies:entry['assessment']='Энкодер и VAE подключаются автоматически. Часть весов может использовать RAM/диск; генерация будет медленнее лёгких SD-моделей.'
        result.append(entry)
    return result


def use_library(ident):
    entry=next((r for r in library() if r['id']==ident),None)
    if entry is None:raise ValueError('Модель не найдена. Обновите список.')
    recipe_id=entry.get('recipe')
    if not recipe_id:raise ValueError('Не удалось определить тип своего файла. Выберите рецепт один раз в дополнительных настройках.')
    if not entry['fits_disk']:raise ValueError('Не хватает свободного места для этой модели.')
    models={}
    if entry.get('components'):
        for component in entry['components']:
            download(dict(component,url=component['url']))
            models[component['slot']]=component['category']+'/'+component['file']
    else:
        path=Path(entry['path']);category=guess_category(path)
        dest=MODEL_DIR/category/path.name
        if not dest.exists():import_model(str(path),category)
        elif not os.path.samefile(path,dest):raise ValueError('В библиотеке уже есть другой файл с таким именем. Выберите его или переименуйте свой файл.')
        # Runtime returns opaque IDs; find them rather than constructing a file ID.
    if not binary():
        import hardware
        setup('vulkan' if hardware.detect()['gpus'] else 'cpu')
    start();api('/sdcpp/v1/models/refresh',{})
    recipes=api('/sdcpp/v1/recipes')['recipes'];recipe=next((r for r in recipes if r['id']==recipe_id),None)
    if recipe is None:raise ValueError('В установленном движке нет рецепта '+recipe_id)
    files=api('/sdcpp/v1/model-files')['files']
    if entry.get('components'):
        for slot,relative in list(models.items()):
            match=next((f for f in files if f.get('relative_path')==relative),None)
            if not match:raise ValueError('Движок не обнаружил '+relative)
            models[slot]=match['id']
    else:
        name=Path(entry['path']).name
        main=next((f for f in files if Path(f.get('relative_path','')).name==name),None)
        slot=next((s['id'] for s in recipe['slots'] if s['id'] in {'model','diffusion_model'}),None)
        if not main or not slot:raise ValueError('Не удалось подключить основной файл модели.')
        models[slot]=main['id']
        for spec in recipe['slots']:
            if not spec.get('required') or spec['id'] in models:continue
            candidates=[f for f in files if f.get('category') in spec.get('categories',[spec.get('category')]) and spec['id'].replace('_','') in Path(f.get('name','')).stem.lower().replace('_','').replace('-','')]
            if len(candidates)==1:models[spec['id']]=candidates[0]['id']
        models=resolve_components(recipe,models,files)
        missing=missing_components(recipe,models)
        if missing:raise ValueError('Основная модель найдена. Ей нужны ещё: '+', '.join(missing)+'. Добавьте совместимые компоненты в дополнительных настройках; их нельзя заменить произвольными файлами.')
    result=run('image_load',{'recipe':recipe_id,'models':models})
    write_json(CONFIG/'image-selected.json',{'id':ident,'recipe':recipe_id,'models':models})
    return result


def missing_components(recipe,models):
    labels={s['id']:s.get('label',s['id']) for s in recipe['slots']}
    missing=[labels[s['id']] for s in recipe['slots'] if s.get('required') and not models.get(s['id'])]
    for group in recipe.get('required_any',[]):
        if not any(models.get(slot) for slot in group):missing.append(' / '.join(labels.get(slot,slot) for slot in group))
    return missing


def resolve_components(recipe,models,files):
    """Use pinned architecture-specific dependencies; never substitute another Qwen generation."""
    result=dict(models)
    manifest=read_json(ROOT/'assets/image-components.json',{'recipes':{}})
    components=manifest['recipes'].get(recipe['id'],[])
    changed=False
    for component in components:
        slot=component['slot']
        if result.get(slot):continue
        alternatives=next((g for g in recipe.get('required_any',[]) if slot in g),[])
        if any(result.get(other) for other in alternatives):continue
        relative=component['category']+'/'+component['file']
        existing=next((f for f in files if f.get('relative_path')==relative),None)
        path=MODEL_DIR/relative
        if existing and path.is_file() and path.stat().st_size==component['size']:
            result[slot]=existing['id'];continue
        print('Автоматически подключаем '+slot+': '+component['file'],flush=True)
        download(component);changed=True
    if changed:
        api('/sdcpp/v1/models/refresh',{})
        files=api('/sdcpp/v1/model-files')['files']
    for component in components:
        slot=component['slot']
        if result.get(slot):continue
        alternatives=next((g for g in recipe.get('required_any',[]) if slot in g),[])
        if any(result.get(other) for other in alternatives):continue
        relative=component['category']+'/'+component['file']
        existing=next((f for f in files if f.get('relative_path')==relative),None)
        if existing:result[slot]=existing['id']
    return result
