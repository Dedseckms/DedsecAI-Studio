"""Image-only Hugging Face discovery; downloads stay separate from the text model registry."""
import hashlib
from pathlib import Path
import re
import urllib.parse
import hub
from common import CONFIG,read_json,write_json,named_lock


def component_repo(data):
    tags={str(t).lower() for t in data.get('tags',[])}
    return bool(tags & {'text-encoder','text_encoders','text-encoders','lora','lora-adapter','vae','clip-vision'}) or (data.get('cardData') or {}).get('base_model_relation')=='adapter'


def search(query,uncensored=False):
    if not isinstance(query,str) or len(query.strip())>100:raise ValueError('Поиск: до 100 символов.')
    query=query.strip()
    if uncensored and not re.search('uncensored|abliterat|unfiltered',query,re.I):query=(query+' uncensored').strip()
    params={'search':query,'pipeline_tag':'text-to-image','full':'true','limit':30,'sort':'downloads','direction':-1}
    rows=hub.get_json('https://huggingface.co/api/models?'+urllib.parse.urlencode(params))
    return [{'repo':r['id'],'downloads':r.get('downloads',0),'uncensored':bool(re.search('uncensored|abliterat|unfiltered',r['id'],re.I))} for r in rows if r.get('pipeline_tag')=='text-to-image' and not component_repo(r)]


def infer_recipe(text):
    text=text.lower().replace('_','-')
    if 'qwen-image' in text and re.search(r'2[.-]1',text):return 'qwen-image-21-turbo' if 'turbo' in text else 'qwen-image-21'
    if 'qwen-image' in text:return 'qwen-image'
    if 'sdxl' in text or 'sd-xl' in text:return 'sdxl-turbo' if 'turbo' in text else 'sdxl-checkpoint'
    if 'sd-turbo' in text:return 'sd-turbo'
    if 'stable-diffusion-v1' in text or 'sd15' in text or 'v1-5' in text:return 'sd1-checkpoint'
    if 'flux' in text:return 'flux1-schnell' if 'schnell' in text else None
    if 'z-image' in text:return 'z-image-turbo' if 'turbo' in text else 'z-image'
    return None


def inspect(value,revision=None):
    repo=hub.repo_id(value)
    suffix='/revision/'+urllib.parse.quote(revision,safe='') if revision else ''
    data=hub.get_json('https://huggingface.co/api/models/'+repo+suffix+'?blobs=true')
    if component_repo(data):raise ValueError('Это энкодер, VAE или LoRA, а не самостоятельный генератор. Компоненты подключаются в дополнительных настройках.')
    if data.get('pipeline_tag') not in {None,'text-to-image','image-to-image'}:raise ValueError('Это не репозиторий генератора изображений.')
    card=data.get('cardData') or {};base=card.get('base_model',[]);base=base if isinstance(base,list) else [str(base)]
    recipe=infer_recipe(repo+' '+' '.join(map(str,base)))
    files=[]
    for item in data.get('siblings',[]):
        remote=item['rfilename'];name=Path(remote).name;low=remote.lower()
        if not low.endswith(('.gguf','.safetensors')) or re.search(r'-\d{5}-of-\d{5}',name):continue
        if any(part in low for part in ['mlx','nvfp4','mxfp4','mmproj','lora','text_encoder','text-encoder','vae/','clip_l','clip_g','t5xxl','optimizer']):continue
        if low.startswith(('tokenizer/','scheduler/')):continue
        if not re.fullmatch(r'[\w. -]{1,180}\.(?:gguf|safetensors)',name,re.I):continue
        size=item.get('size') or item.get('lfs',{}).get('size',0)
        if not size:continue
        files.append({'file':remote,'name':name,'size':size,'gib':round(size/1024**3,2),'sha256':item.get('lfs',{}).get('sha256'),'recipe':infer_recipe(remote) or recipe})
    import imaging,hardware
    dependencies=read_json(imaging.ROOT/'assets/image-components.json',{'recipes':{}})['recipes'];free=hardware.detect()['disk_free_bytes']
    for file in files:
        extra=sum(c['size'] for c in dependencies.get(file['recipe'],[]) if not (imaging.MODEL_DIR/c['category']/c['file']).is_file())
        file['dependency_gib']=round(extra/1024**3,2);file['fits_disk']=file['size']+extra+2*1024**3<free
    return {'repo':repo,'revision':data['sha'],'source':'https://huggingface.co/'+repo,'license':card.get('license','Уточните в карточке автора'),'uncensored':bool(re.search('uncensored|abliterat|unfiltered',repo,re.I)),'recipe':recipe,'files':sorted(files,key=lambda f:f['size'])}


def install(data):
    import imaging
    info=inspect(data.get('repo'),data.get('revision'));file=next((f for f in info['files'] if f['file']==data.get('file')),None)
    if file is None:raise ValueError('Файл не найден. Обновите список репозитория.')
    recipe=data.get('recipe') or file['recipe']
    # Only runtime recipe IDs, no arbitrary objects/commands supplied by the browser.
    if recipe and (not isinstance(recipe,str) or not re.fullmatch('[a-z0-9-]{1,80}',recipe)):raise ValueError('Некорректный рецепт.')
    category='checkpoints' if recipe in {'sd-turbo','sd1-checkpoint','sdxl-checkpoint','sdxl-turbo'} else 'diffusion_models'
    folder=hashlib.sha256((info['repo']+'@'+info['revision']).encode()).hexdigest()[:12]
    artifact={'url':'https://huggingface.co/'+info['repo']+'/resolve/'+info['revision']+'/'+urllib.parse.quote(file['file'],safe='/'),'category':category,'folder':folder,'size':file['size'],'sha256':file['sha256']}
    path=imaging.MODEL_DIR/category/folder/file['name']
    # Reuse a verified same-name existing import instead of downloading a second copy.
    reused=False
    if file['sha256']:
        from common import digest_file
        for existing in (imaging.MODEL_DIR/category).rglob(file['name']):
            if existing.is_file() and existing.stat().st_size==file['size'] and digest_file(existing)==file['sha256']:path=existing;reused=True;break
    if not reused:imaging.download(artifact)
    ident='hf-image-'+hashlib.sha256((info['repo']+'@'+info['revision']+':'+file['file']).encode()).hexdigest()[:16]
    entry={'id':ident,'name':file['name'].removesuffix('.gguf').removesuffix('.safetensors'),'path':str(path),'local':True,'source':info['source'],'recipe':recipe,'uncensored':info['uncensored']}
    with named_lock('image-library'):
        rows=read_json(CONFIG/'image-library.json',[]);rows=[r for r in rows if r.get('path')!=str(path) and r['id']!=ident];rows.append(entry);write_json(CONFIG/'image-library.json',rows)
    if data.get('activate') is True:return imaging.use_library(ident)
    return {'id':ident,'message':'Image-модель скачана. Она доступна в «Мои модели»; выберите её, когда захотите генерировать.'}
