"""Hardware detection and deliberately conservative memory planning."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time

GIB=1024**3
_cache=None
_stamp=0

def command(args,timeout=4):
    try:
        r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0)
        return r.stdout.strip() if r.returncode==0 else ''
    except (OSError,subprocess.TimeoutExpired):return ''

def detect(refresh=False):
    global _cache,_stamp
    if not refresh and _cache and time.monotonic()-_stamp<10:return dict(_cache)
    total=available=0;cpu=platform.processor() or platform.machine();logical=os.cpu_count() or 1;cores=max(1,logical//2);gpus=[]
    if os.name=='nt':
        class Memory(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(x,ctypes.c_ulonglong) for x in ['total','available','page_total','page_available','virtual_total','virtual_available','extended']]
        m=Memory();m.length=ctypes.sizeof(m)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):total,available=m.total,m.available
        data=command(['powershell','-NoProfile','-Command','[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Get-CimInstance Win32_Processor | Select-Object -First 1 Name,NumberOfCores | ConvertTo-Json -Compress'])
        try:d=json.loads(data);cpu=d['Name'];cores=int(d['NumberOfCores'])
        except (ValueError,KeyError,TypeError):pass
    else:
        try:
            mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if len(line.split())>=2}
            total,available=mem.get('MemTotal',0),mem.get('MemAvailable',0)
            text=Path('/proc/cpuinfo').read_text()
            cpu=next((line.split(':',1)[1].strip() for line in text.splitlines() if line.startswith('model name')),cpu)
            pairs=set()
            for block in text.split('\n\n'):
                fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
                normalized={k.strip():v.strip() for k,v in fields.items()}
                if 'core id' in normalized:pairs.add((normalized.get('physical id','0'),normalized['core id']))
            if pairs:cores=len(pairs)
        except (OSError,ValueError):pass
    nv=command(['nvidia-smi','--query-gpu=name,memory.total,memory.free,utilization.gpu,temperature.gpu','--format=csv,noheader,nounits'])
    for line in nv.splitlines():
        try:
            name,vram,free,load,temp=[x.strip() for x in line.split(',')]
            def optional(value):
                try:return float(value)
                except ValueError:return None
            gpus.append(dict(name=name,vendor='NVIDIA',vram_bytes=int(float(vram)*1024**2),free_bytes=int(float(free)*1024**2),load=optional(load),temp=optional(temp),dedicated=True))
        except ValueError:pass
    if os.name=='nt':
        from windows_gpu import adapters
        for gpu in adapters():
            if not any(g['name'].casefold()==gpu['name'].casefold() for g in gpus):gpus.append(gpu)
    if not gpus and os.name!='nt':
        for p in Path('/sys/class/drm').glob('card[0-9]*/device'):
            try:
                vram=int((p/'mem_info_vram_total').read_text());used=int((p/'mem_info_vram_used').read_text())
                vendor=(p/'vendor').read_text().strip();name='AMD Radeon' if vendor=='0x1002' else 'GPU'
                gpus.append(dict(name=name,vendor='AMD' if vendor=='0x1002' else vendor,vram_bytes=vram,free_bytes=max(0,vram-used),dedicated=True,load=None,temp=None))
            except (OSError,ValueError):pass
    if not gpus and os.name=='nt':
        data=command(['powershell','-NoProfile','-Command','[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; @(Get-CimInstance Win32_VideoController | Select-Object Name) | ConvertTo-Json -Compress'])
        try:
            rows=json.loads(data);rows=rows if isinstance(rows,list) else [rows]
            for row in rows:gpus.append(dict(name=row['Name'],vendor='unknown',vram_bytes=0,free_bytes=0,dedicated=False,load=None,temp=None))
        except (ValueError,KeyError,TypeError):pass
    fingerprint=hashlib.sha256(json.dumps([platform.system(),platform.machine(),cpu,cores,total,[(g['name'],g['vram_bytes']) for g in gpus]],sort_keys=True).encode()).hexdigest()[:20]
    from common import MODELS
    result=dict(os=platform.system(),arch=platform.machine(),cpu=cpu,cores=cores,threads=logical,ram_bytes=total,ram_available_bytes=available,
                gpus=gpus,disk_free_bytes=shutil.disk_usage(MODELS).free,fingerprint=fingerprint)
    _cache=result;_stamp=time.monotonic();return dict(result)

def kv_bytes(item,ctx,cache):
    geometry=item.get('geometry')
    if geometry:
        layers,heads,dim=geometry
        return int(layers*heads*dim*2*ctx*(34/32 if cache=='q8_0' else 18/32))
    # Unknown/MLA/hybrid architectures need verification; this is only a planning allowance.
    return ctx*128*1024

def plan(item,hw=None):
    hw=hw or detect();size=item.get('size') or 0
    gpu=max(hw['gpus'],key=lambda g:g.get('vram_bytes',0),default={})
    vram=gpu.get('vram_bytes',0);ram=hw.get('ram_bytes',0)
    native=max(512,int(item.get('native_ctx',item.get('ctx',32768))))
    max_ctx=min(native,32768)
    verified=item.get('verified_hardware')==hw['fingerprint']
    if verified:
        ctx=item['ctx'];cache=item.get('cache','q4_0');layers=item.get('gpu_layers','all');tier='gpu'
    else:
        ctx=min(4096,max_ctx);cache='q4_0';tier='too_large';layers='auto'
        reserve=max(int(1.5*GIB),int(vram*.12))
        candidates=[c for c in [32768,16384,8192,4096,2048,1024] if c<=max_ctx] or [max_ctx]
        if vram:
            for c in candidates:
                for quant in ['q8_0','q4_0']:
                    if size+kv_bytes(item,c,quant)+reserve<=vram:
                        ctx,cache,tier,layers=c,quant,'gpu','all';break
                if tier=='gpu':break
        if tier!='gpu':
            host_budget=max(0,ram-max(3*GIB,int(ram*.2)))
            usable_gpu=max(0,vram-int(1.5*GIB))
            if size+kv_bytes(item,ctx,cache)<host_budget+usable_gpu:
                tier='hybrid' if vram else 'cpu'
            else:tier='too_large'
    estimated=size+kv_bytes(item,ctx,cache)+int(1.5*GIB)
    if tier=='gpu':
        label='Быстро · оценка' if size<6*GIB else 'Средняя скорость · оценка'
        why='По расчёту веса и кэш помещаются в видеопамять. Точная скорость зависит от архитектуры, драйвера и длины истории.'
    elif tier=='hybrid':
        label='Возможное замедление · GPU + CPU'
        why='Целиком в VRAM не помещается: часть слоёв и вычислений уйдёт в RAM/CPU. Обмен памятью может ограничить скорость.'
    elif tier=='cpu':
        label='CPU · скорость нужно замерить'
        why='Доступная дискретная видеопамять не обнаружена. Работа из RAM зависит от пропускной способности памяти и CPU.'
    else:
        label='Не рекомендуется этому ПК'
        why='По предварительной оценке не хватает RAM и VRAM. Активные параметры MoE не равны общему размеру всех весов.'
    if not item.get('geometry') and not verified:why+=' Расход KV оценён приблизительно; архитектуру уточнит GGUF после загрузки.'
    return dict(ctx=ctx,cache=cache,ubatch=64 if size>8*GIB else 128,gpu_layers=layers,threads=max(1,min(hw['cores'],12)),
                tier=tier,cpu_risk=tier!='gpu',speed=label,why=why,estimated_bytes=estimated,geometry_known=bool(item.get('geometry')),verified=verified)
