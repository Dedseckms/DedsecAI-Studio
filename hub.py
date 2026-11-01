"""Hugging Face GGUF discovery, split-file grouping and resumable downloads."""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import urllib.error
import urllib.parse
import urllib.request
from common import CONFIG,MODELS,ROOT,digest_file,read_json,write_json

GIB=1024**3
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        validate_url(newurl)
        next_req=super().redirect_request(req,fp,code,msg,headers,newurl)
        if next_req and urllib.parse.urlsplit(req.full_url).hostname!=urllib.parse.urlsplit(newurl).hostname:
            next_req.remove_header('Authorization')
        return next_req

HTTP=urllib.request.build_opener(Redirect())

def validate_url(url):
    if not isinstance(url,str) or len(url)>8192:raise ValueError('Некорректная ссылка.')
    p=urllib.parse.urlsplit(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password:raise ValueError('Нужна HTTPS-ссылка без логина и пароля в адресе.')
    if p.port not in (None,443):raise ValueError('Поддерживается стандартный HTTPS-порт 443.')
    if p.hostname.lower() in {'localhost','localhost.localdomain'}:raise ValueError('Нужна публичная ссылка на модель.')
    # Explicit local URLs/IP literals are disallowed. DNS may be routed through a
    # trusted corporate proxy, so do not mistake proxy addresses for local targets.
    try:
        literal=ipaddress.ip_address(p.hostname)
    except ValueError:
        literal=None
    if literal is not None and not literal.is_global:raise ValueError('Локальные и служебные IP-адреса загрузки запрещены.')
    if p.hostname.lower().endswith(('.local','.internal','.localhost')):raise ValueError('Нужна публичная HTTPS-ссылка.')
    return url

def get_json(url):
    validate_url(url)
    headers={'User-Agent':'DedsecAI-Studio/0.2'}
    if os.environ.get('HF_TOKEN') and urllib.parse.urlsplit(url).hostname=='huggingface.co':headers['Authorization']='Bearer '+os.environ['HF_TOKEN']
    try:
        with HTTP.open(urllib.request.Request(url,headers=headers),timeout=30) as r:
            if int(r.headers.get('Content-Length','0'))>20*1024*1024:raise ValueError('Метаданные слишком велики.')
            body=r.read(20*1024*1024+1)
            if len(body)>20*1024*1024:raise ValueError('Метаданные слишком велики.')
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        if exc.code in (401,403):raise ValueError('Репозиторий закрыт или gated. Примите лицензию и задайте HF_TOKEN в окружении приложения.') from exc
        if exc.code==404:raise ValueError('Репозиторий или ревизия не найдены.') from exc
        raise ValueError(f'Источник вернул HTTP {exc.code}.') from exc

def repo_id(value):
    if not isinstance(value,str):raise ValueError('Укажите owner/repository или ссылку Hugging Face.')
    value=value.strip()
    if value.startswith('https://'):
        p=urllib.parse.urlsplit(value)
        if p.hostname!='huggingface.co':raise ValueError('Для репозитория нужна ссылка huggingface.co.')
        value='/'.join(p.path.strip('/').split('/')[:2])
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*',value):raise ValueError('Формат репозитория: owner/name.')
    return value

def groups(siblings,projectors=False):
    single=[];split={}
    for row in siblings:
        name=row['rfilename']
        if not name.lower().endswith('.gguf') or Path(name).name.lower().startswith('mmproj')!=projectors:continue
        leaf=Path(name).name
        if any(x in leaf for x in ['\\',':','\0']) or leaf in {'.','..'}:continue
        f={'name':leaf,'remote_path':name,'size':row.get('size') or row.get('lfs',{}).get('size',0),'sha256':row.get('lfs',{}).get('sha256')}
        match=re.fullmatch(r'(.*)-(\d{5})-of-(\d{5})\.gguf',name,re.I)
        if match:
            key=match[1];n,total=int(match[2]),int(match[3]);split.setdefault((key,total),{})[n]=f
        else:single.append({'variant':name,'files':[f],'size':f['size']})
    for (key,total),items in split.items():
        if total>1000 or set(items)!=set(range(1,total+1)):continue
        files=[items[n] for n in range(1,total+1)]
        single.append({'variant':key+'.gguf','files':files,'size':sum(x['size'] for x in files)})
    return sorted(single,key=lambda x:(x['size'] or 2**63,x['variant']))

def inspect_repo(value,revision=None):
    repo=repo_id(value)
    suffix=('/revision/'+urllib.parse.quote(revision,safe='')) if revision else ''
    d=get_json('https://huggingface.co/api/models/'+repo+suffix+'?blobs=true')
    variants=groups(d.get('siblings',[]))
    return {'repo':repo,'revision':d['sha'],'source':'https://huggingface.co/'+repo,'variants':variants,'projectors':groups(d.get('siblings',[]),True),'license':d.get('cardData',{}).get('license','уточните в карточке модели')}

def search_repos(query):
    if not isinstance(query,str) or not 2<=len(query.strip())<=100:raise ValueError('Введите от 2 до 100 символов.')
    url='https://huggingface.co/api/models?'+urllib.parse.urlencode({'search':query.strip(),'filter':'gguf','sort':'downloads','direction':-1,'limit':20})
    rows=get_json(url)
    return [{'repo':r['id'],'downloads':r.get('downloads',0),'likes':r.get('likes',0)} for r in rows]

def from_variant(repo,revision,variant,name=None,family='Custom'):
    ident='hf-'+hashlib.sha256((repo+'@'+revision+':'+variant['variant']).encode()).hexdigest()[:16]
    return dict(id=ident,name=name or Path(variant['variant']).name.removesuffix('.gguf'),family=family,repo=repo,revision=revision,files=variant['files'],
                file=variant['files'][0]['name'],size=variant['size'],alias=ident,native_ctx=32768,source='https://huggingface.co/'+repo,tasks='GGUF из Hugging Face. Совместимость chat template и инструментов нужно проверить.')

def register_repo(repo,variant,revision=None,projector=None):
    info=inspect_repo(repo,revision)
    row=next((v for v in info['variants'] if v['variant']==variant),None)
    if not row:raise ValueError('Вариант GGUF не найден. Обновите список файлов.')
    item=from_variant(info['repo'],info['revision'],row)
    if projector:
        proj=next((p for p in info['projectors'] if p['variant']==projector),None)
        if not proj:raise ValueError('Проектор не найден в репозитории.')
        item['projector_download']=proj
    save_custom(item);return item

def save_custom(item):
    rows=read_json(CONFIG/'custom.json',[])
    existing=next((i for i,r in enumerate(rows) if r['id']==item['id']),None)
    if existing is None:rows.append(item)
    else:rows[existing]=item
    write_json(CONFIG/'custom.json',rows)

def inspect_url(url,sha256=None):
    validate_url(url)
    filename=urllib.parse.unquote(Path(urllib.parse.urlsplit(url).path).name)
    if not re.fullmatch(r'[^<>:"/\\|?*\x00-\x1f]{1,180}\.gguf',filename,re.I):raise ValueError('Прямая ссылка должна заканчиваться именем .gguf. Для split-модели используйте Hugging Face.')
    if re.search(r'-\d{5}-of-\d{5}\.gguf$',filename,re.I):raise ValueError('Для split GGUF укажите репозиторий Hugging Face — нужны все части.')
    if sha256 and not re.fullmatch('[a-fA-F0-9]{64}',sha256):raise ValueError('SHA-256 должен содержать 64 шестнадцатеричных символа.')
    try:
        r=HTTP.open(urllib.request.Request(url,method='HEAD'),timeout=20)
    except urllib.error.HTTPError as exc:
        if exc.code not in (405,501):raise
        r=HTTP.open(urllib.request.Request(url,headers={'Range':'bytes=0-0'}),timeout=20)
    with r:
        total=r.headers.get('Content-Range','').split('/')[-1]
        size=int(total) if total.isdigit() else int(r.headers.get('Content-Length','0'))
    ident='url-'+hashlib.sha256(url.encode()).hexdigest()[:16]
    return dict(id=ident,name=filename.removesuffix('.gguf'),family='Custom',file=filename,size=size,alias=ident,native_ctx=8192,
                files=[{'name':filename,'size':size,'sha256':sha256.lower() if sha256 else None,'url':url}],source=url,tasks='Модель по вашей HTTPS-ссылке. Совместимость требует проверки.')

def paths(item):
    if item.get('path'):
        first=Path(item['path']);files=item.get('files') or [{'name':first.name,'size':item.get('size')}]
        return [(first.parent/f['name'],f) for f in files]
    files=item.get('files') or [{'name':item['file'],'size':item.get('size'),'sha256':item.get('sha256')}]
    return [(MODELS/item['id']/f['name'],f) for f in files]

def installed(item):
    try:
        for p,f in paths(item):
            if not p.is_file() or (f.get('size') and p.stat().st_size!=f['size']):return False
            with p.open('rb') as src:
                if src.read(4)!=b'GGUF':return False
        return bool(paths(item))
    except OSError:return False

def download(item):
    if installed(item):print('Модель уже установлена.',flush=True);return
    if item.get('path'):raise ValueError('Локальный файл отсутствует или изменился. Импортируйте его заново.')
    files=paths(item)
    remaining=sum(max(0,(f.get('size') or 0)-(p.with_suffix('.gguf.part').stat().st_size if p.with_suffix('.gguf.part').exists() else 0)) for p,f in files)
    if shutil.disk_usage(MODELS).free<remaining+2*GIB:raise ValueError(f'Не хватает места: нужно {remaining/GIB:.1f} ГиБ и резерв 2 ГиБ.')
    for index,(dest,f) in enumerate(files,1):
        if dest.exists():
            with dest.open('rb') as src:valid=src.read(4)==b'GGUF'
            if valid and (not f.get('size') or dest.stat().st_size==f['size']):continue
            raise ValueError('Файл назначения уже существует, но не совпадает с моделью: '+str(dest))
        dest.parent.mkdir(parents=True,exist_ok=True);part=dest.with_suffix('.gguf.part')
        have=part.stat().st_size if part.exists() else 0;size=f.get('size') or 0
        if size and have>size:raise ValueError('Временный файл больше ожидаемого: '+str(part))
        if not size or have<size:
            url=f.get('url') or 'https://huggingface.co/'+item['repo']+'/resolve/'+item['revision']+'/'+urllib.parse.quote(f['remote_path'],safe='/')
            validate_url(url)
            headers={'User-Agent':'DedsecAI-Studio/0.2'}
            if have:headers['Range']=f'bytes={have}-'
            if os.environ.get('HF_TOKEN') and urllib.parse.urlsplit(url).hostname=='huggingface.co':headers['Authorization']='Bearer '+os.environ['HF_TOKEN']
            print(f'Часть {index}/{len(files)}: {f["name"]}',flush=True)
            with HTTP.open(urllib.request.Request(url,headers=headers),timeout=60) as response:
                if have and response.status!=206:raise ValueError('Сервер не поддержал докачку. Временный файл сохранён: '+str(part))
                if have and not response.headers.get('Content-Range','').startswith(f'bytes {have}-'):raise ValueError('Сервер вернул неверный диапазон докачки.')
                with part.open('ab') as out:
                    last=0
                    for chunk in iter(lambda:response.read(2*1024*1024),b''):
                        if shutil.disk_usage(MODELS).free<len(chunk)+512*1024**2:raise ValueError('Загрузка остановлена: мало места на диске. Частичный файл сохранён.')
                        out.write(chunk);have+=len(chunk)
                        if size and have>size:raise ValueError('Источник прислал больше данных, чем заявлено.')
                        if have-last>32*1024**2:
                            print(f'{have/GIB:.2f} / {size/GIB:.2f} ГиБ' if size else f'{have/GIB:.2f} ГиБ',flush=True);last=have
        if size and part.stat().st_size!=size:raise ValueError('Загрузка неполная; повторите для докачки.')
        with part.open('rb') as src:
            if src.read(4)!=b'GGUF':raise ValueError('Источник вернул не GGUF; модель не установлена.')
        digest=digest_file(part)
        if f.get('sha256') and digest!=f['sha256']:raise ValueError('SHA-256 не совпал; модель не установлена. Временный файл сохранён.')
        f['sha256_computed']=digest;f['verified']=bool(f.get('sha256'));f['size']=part.stat().st_size
        os.replace(part,dest)
    item['size']=sum(f['size'] for _,f in files);item['files']=[f for _,f in files]
    if not item.get('artifact'):save_custom(item)
    print('Все части GGUF установлены. '+('SHA-256 подтверждён источником.' if all(f.get('verified') for _,f in files) else 'Для части файлов источник не предоставил контрольную сумму; хеш рассчитан локально.'),flush=True)
