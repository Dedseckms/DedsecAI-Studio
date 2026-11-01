"""Portable model registry and hardware-specific profiles."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sqlite3
import time
from common import HOME,APP_HOME,CONFIG,STATE,MODELS,ROOT,SERVER_PORT,atomic,read_json,write_json,lock
from gguf import gguf_info
import hardware
import hub
import runtime

GIB=1024**3
api=runtime.api
wait_ready=runtime.wait_ready


def raw_catalog():
    rows=read_json(ROOT/'assets/catalog.json',{'models':[]})['models']
    custom=read_json(CONFIG/'custom.json',[])
    merged={row['id']:row for row in rows}
    for row in custom:
        if row.get('path') and row.get('repo'):
            for ident,seed in list(merged.items()):
                if ident!=row['id'] and seed.get('repo')==row['repo'] and seed.get('file')==row.get('file'):merged.pop(ident)
        merged[row['id']]=row
    return list(merged.values())

def catalog():
    hw=hardware.detect();rows=[]
    for raw in raw_catalog():
        row=copy.deepcopy(raw);profile=hardware.plan(row,hw);row.update(profile)
        row['assessment']=profile
        override=read_json(CONFIG/'profiles.json',{}).get(row['id'],{})
        if override.get('ctx'):
            row['ctx']=override['ctx'];row['custom_ctx']=True
        if 'mmproj' in override:row['mmproj']=override['mmproj']
        if row.get('custom_ctx'):row['why']+=' Размер контекста задан вручную; расход памяти может превышать автоматический профиль.'
        rows.append(row)
    return rows

def model(ident):
    for row in catalog():
        if row['id']==ident:return row
    raise ValueError('Модель не выбрана или не найдена. Выберите GGUF в каталоге.')

def selected():return read_json(CONFIG/'active.json',{}).get('id')
def file_path(item):return hub.paths(item)[0][0]
def installed(item):return hub.installed(item)
def kv_gib(item):return hardware.kv_bytes(item,item['ctx'],item['cache'])/GIB

def profile_key(item):
    p=file_path(item)
    return f"{hardware.detect()['fingerprint']}:{item['id']}:{item['ctx']}:{item['cache']}:{item['ubatch']}:{p.stat().st_mtime_ns}:{p.stat().st_size}"

def speed(item):
    if installed(item):
        result=read_json(STATE/'model-benchmarks.json',{}).get(profile_key(item))
        if result:return f"ЗАМЕР: {result['tokens_per_second']:.1f} ток/с ({result['generated_tokens']} токенов)"
    return item['speed']

def update_metadata(item):
    info=gguf_info(file_path(item));arch=info.get('general.architecture','')
    item['architecture']=arch
    if 'image' in arch or arch in {'flux','flux2','sd1','sd2','sdxl','sd3','stable-diffusion','hidream'}:item['kind']='image'
    item['native_ctx']=int(info.get(arch+'.context_length',32768))
    # MLA/SSM/hybrid caches are not the ordinary GQA cache; leave their estimate marked unknown.
    if arch in {'qwen2','qwen3','llama','phi3','gemma','gemma2'}:
        n=info.get(arch+'.block_count');h=info.get(arch+'.attention.head_count_kv');d=info.get(arch+'.attention.key_length')
        if not d and info.get(arch+'.attention.head_count'):d=info.get(arch+'.embedding_length',0)//info[arch+'.attention.head_count']
        if n and h and d:item['geometry']=[int(n),int(h),int(d)]
    hub.save_custom(item)

def download(item):
    hub.download(item)
    if item.get('projector_download'):
        proj=item['projector_download'];artifact=dict(id=item['id'],files=proj['files'],file=proj['files'][0]['name'],size=proj['size'],repo=item['repo'],revision=item['revision'],artifact=True)
        hub.download(artifact);item['mmproj']=str(hub.paths(artifact)[0][0]);hub.save_custom(item)
    if installed(item):
        update_metadata(item)
    return item

def environment(item):
    write_json(CONFIG/'active.json',{'id':item['id'],'alias':item['alias'],'ctx':item['ctx'],'profile':{k:item[k] for k in ['ctx','cache','ubatch','gpu_layers','threads']}})
    if runtime.legacy():
        values=dict(QWEN_MODEL=str(file_path(item)),QWEN_ALIAS=item['alias'],QWEN_CTX=str(item['ctx']),QWEN_CACHE=item['cache'],QWEN_UBATCH=str(item['ubatch']),QWEN_GPU_LAYERS=str(item['gpu_layers']))
        atomic(HOME/'.config/qwen/active.env','\n'.join(f'export {k}={shlex.quote(v)}' for k,v in values.items())+'\n')
        write_json(HOME/'.config/qwen/active.json',{'id':item['id'],'alias':item['alias'],'ctx':item['ctx']})
        # Old qcode still asks its registry for the selected alias. Preserve that entry for compatibility.
        path=HOME/'.local/share/qwen/catalog.json';old=read_json(path,{'models':[]})
        old['models']=[r for r in old['models'] if r['id']!=item['id']]+[dict(item,path=str(file_path(item)))]
        write_json(path,old)

def sync_pi(item):
    path=HOME/'.pi/agent/models.json';data=read_json(path,{})
    provider=data.setdefault('providers',{}).setdefault('lmstudio',{})
    provider.update(baseUrl=f'http://127.0.0.1:{SERVER_PORT}/v1',api='openai-completions',apiKey='local')
    entries=provider.setdefault('models',[]);entry=next((r for r in entries if r['id']==item['alias']),None)
    if entry is None:entry={'id':item['alias']};entries.append(entry)
    entry.update(contextWindow=item['ctx'],maxTokens=min(4096,item['ctx']//4))
    entry.setdefault('samplingParams',{}).update(temperature=.6,top_p=.95,repeat_penalty=1.0,dry_multiplier=0.0)
    write_json(path,data)
    path=HOME/'.pi/agent/settings.json';data=read_json(path,{})
    data.update(defaultProvider='lmstudio',defaultModel=item['alias'],defaultThinkingLevel='off',tuiMode='fullscreen')
    data.setdefault('compaction',{}).setdefault('modelOverrides',{})['lmstudio/'+item['alias']]={'reserveTokens':min(8192,item['ctx']//3),'keepRecentTokens':min(6144,item['ctx']//4)}
    write_json(path,data)

def activate(item,allow_cpu=False):
    if item.get('kind')=='image':raise ValueError('Это генератор изображений. Откройте вкладку «Изображения».')
    if not installed(item):raise ValueError('Сначала скачайте или импортируйте модель.')
    if item['tier']=='too_large':raise ValueError('Модель слишком велика по оценке RAM/VRAM этого ПК. Выберите меньшую квантовку или модель.')
    if item['cpu_risk'] and not allow_cpu:raise ValueError('Этот профиль использует CPU. Подтвердите выбор варианта с CPU.')
    paths=[CONFIG/'active.json',HOME/'.pi/agent/models.json',HOME/'.pi/agent/settings.json']
    if runtime.legacy():paths.extend([HOME/'.config/qwen/active.env',HOME/'.config/qwen/active.json',HOME/'.local/share/qwen/catalog.json'])
    before={p:p.read_text(encoding='utf-8') if p.exists() else None for p in paths}
    previous=selected();was_running=runtime.healthy()
    try:
        runtime.stop();environment(item);runtime.start(item);sync_pi(item)
    except BaseException:
        runtime.stop()
        for p,content in before.items():
            if content is not None:atomic(p,content)
            elif p==CONFIG/'active.json':write_json(p,{})
        if previous and was_running:
            try:runtime.start(model(previous))
            except Exception as exc:print('Настройки восстановлены, но предыдущий сервер не готов: '+str(exc),flush=True)
        raise
    print('Модель готова: '+item['name'],flush=True)
    return item

def start(foreground=False,cancel=None):
    item=model(selected())
    if not installed(item):raise ValueError('Выбранная модель не установлена.')
    runtime.start(item,foreground,cancel)

def benchmark(item,tokens=192):
    wait_ready(item,5)
    result=api('/v1/chat/completions',{'model':item['alias'],'messages':[{'role':'user','content':'Write Python merge sort with type hints. Output only code.'}],'max_tokens':tokens,'temperature':.2},timeout=180)
    timing=result['timings'];value=dict(tokens_per_second=timing['predicted_per_second'],generated_tokens=timing['predicted_n'],hardware=hardware.detect()['fingerprint'],context=item['ctx'],measured_at=time.strftime('%Y-%m-%d %H:%M:%S'))
    p=STATE/'model-benchmarks.json';rows=read_json(p,{})
    rows[profile_key(item)]=value;write_json(p,rows)
    print(f"ЗАМЕР: {value['tokens_per_second']:.1f} ток/с",flush=True);return value

def add(path,ident=None):
    path=Path(path).expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix.lower()!='.gguf':raise ValueError('Выберите файл GGUF.')
    ident=ident or 'local-'+hashlib.sha256(str(path).encode()).hexdigest()[:16]
    if not re.fullmatch('[a-z0-9_-]{1,80}',ident):raise ValueError('ID: латинские строчные буквы, цифры, - и _.')
    files=[];match=re.fullmatch(r'(.*)-(\d{5})-of-(\d{5})\.gguf',path.name,re.I)
    if match:
        total=int(match[3]);stem=match[1]
        if total>1000:raise ValueError('Слишком много частей GGUF.')
        for n in range(1,total+1):
            p=path.parent/f'{stem}-{n:05d}-of-{total:05d}.gguf'
            if not p.is_file():raise ValueError('Не хватает части: '+p.name)
            files.append({'name':p.name,'size':p.stat().st_size})
        path=path.parent/files[0]['name']
    else:files=[{'name':path.name,'size':path.stat().st_size}]
    item=dict(id=ident,alias=ident,name=path.stem,path=str(path),file=path.name,files=files,size=sum(f['size'] for f in files),family='Custom',tasks='Ваш локальный GGUF; исходный файл не копируется и не перемещается.')
    update_metadata(item);return model(ident)

def migrate():
    """Explicit one-time local migration; originals are retained."""
    if read_json(CONFIG/'migration.json',{}).get('done'):return
    old=read_json(HOME/'.local/share/qwen/catalog.json',{'models':[]})['models']
    hw=hardware.detect();rows=read_json(CONFIG/'custom.json',[])
    for oldrow in old:
        p=Path(oldrow.get('path',HOME/'models'/oldrow['file']))
        if not p.is_file():continue
        row=dict(oldrow,path=str(p),files=[{'name':p.name,'size':p.stat().st_size}],family=oldrow.get('family','Qwen'),verified_hardware=hw['fingerprint'],native_ctx=oldrow.get('ctx',32768),threads=hw['cores'])
        rows=[r for r in rows if r['id']!=row['id']]+[row]
    if rows:write_json(CONFIG/'custom.json',rows)
    previous=read_json(HOME/'.config/qwen/active.json',{})
    if previous.get('id') in {r['id'] for r in rows}:write_json(CONFIG/'active.json',previous)
    if os.name!='nt' and (HOME/'.config/systemd/user/qwen-server.service').exists():
        write_json(CONFIG/'legacy.json',{'service':'qwen-server.service','log':str(HOME/'.local/state/qwen-server/server.log')})
    old_db=HOME/'.local/share/qwen-companion/companion.sqlite3';new_db=APP_HOME/'companion/companion.sqlite3'
    if old_db.is_file() and not new_db.exists():
        new_db.parent.mkdir(parents=True,exist_ok=True)
        src=sqlite3.connect(str(old_db));dest=sqlite3.connect(str(new_db))
        try:src.backup(dest)
        finally:src.close();dest.close()
    projects=HOME/'.local/state/qwen-server/panel/projects.json'
    if projects.exists() and not (STATE/'panel/projects.json').exists():write_json(STATE/'panel/projects.json',read_json(projects,[]))
    oldbench=read_json(HOME/'.local/state/qwen-server/model-benchmarks.json',{})
    newbench=read_json(STATE/'model-benchmarks.json',{})
    for row in catalog():
        if not installed(row):continue
        p=file_path(row);oldkey=f"{row['id']}:{row['ctx']}:{row['cache']}:{row['ubatch']}:{p.stat().st_mtime_ns}:{p.stat().st_size}"
        if oldkey in oldbench:newbench[profile_key(row)]=oldbench[oldkey]
    write_json(STATE/'model-benchmarks.json',newbench)
    write_json(CONFIG/'migration.json',{'done':True,'originals_preserved':True})

def server_log():
    if read_json(STATE/'server-mode.json',{}).get('mode')=='portable':return STATE/'server.log'
    return Path(read_json(CONFIG/'legacy.json',{}).get('log',STATE/'server.log'))


def set_profile(ident,ctx,mmproj=None):
    item=model(ident)
    if isinstance(ctx,bool) or not isinstance(ctx,int) or not 512<=ctx<=int(item.get('native_ctx',32768)):
        raise ValueError('Контекст: от 512 до '+str(item.get('native_ctx',32768))+' токенов (предел модели).')
    rows=read_json(CONFIG/'profiles.json',{});entry=rows.setdefault(ident,{})
    entry['ctx']=ctx
    if mmproj is not None:
        if not isinstance(mmproj,str):raise ValueError('Укажите путь к mmproj строкой.')
        if mmproj:
            path=Path(mmproj).expanduser().resolve(strict=True)
            if path.suffix.lower()!='.gguf' or not path.is_file():raise ValueError('Проектор должен быть файлом GGUF.')
            gguf_info(path);entry['mmproj']=str(path)
        else:entry['mmproj']=''
    write_json(CONFIG/'profiles.json',rows)
    item=model(ident)
    if selected()==ident:
        runtime.stop();environment(item);runtime.start(item);sync_pi(item)
    return {'message':'Профиль сохранён. Контекст: '+str(ctx)}


def downloaded(item):
    download(item)
    result={'id':item['id'],'message':'Модель скачана и проверена.'}
    item=model(item['id'])
    if item.get('kind')=='image':
        import imaging
        return imaging.import_model(str(file_path(item)))
    if item['tier']=='too_large':
        result['message']+=' Автозамер пропущен: профиль превышает память ПК.'
        return result
    previous=selected();running=runtime.healthy()
    try:
        activate(item,allow_cpu=True);result['benchmark']=benchmark(item)
        result['message']+=' Скорость измерена автоматически.'
    except Exception as exc:result['message']+=' Автозамер не выполнен: '+str(exc)
    finally:
        if previous and previous!=item['id']:
            runtime.stop();environment(model(previous))
            if running:runtime.start(model(previous))
            sync_pi(model(previous))
    return result


def refresh_installed_metadata():
    from common import VERSION
    marker=read_json(STATE/'metadata-version.json',{})
    if marker.get('version')==VERSION:return
    for item in raw_catalog():
        if installed(item):
            try:update_metadata(item)
            except (ValueError,OSError) as exc:print('Не удалось уточнить метаданные '+item['id']+': '+str(exc),flush=True)
    write_json(STATE/'metadata-version.json',{'version':VERSION})
