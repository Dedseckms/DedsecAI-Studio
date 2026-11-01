"""Live engine identities and measured NVIDIA process memory, never selected-model guesses."""
import csv
import io
import os
from pathlib import Path
import threading
import time
import hardware
import runtime
import imaging
from common import SERVER_PORT,STATE,read_json

_guard=threading.Lock();_cached=None;_stamp=0

def process_port(pid,exe,port,flag):
    if os.name=='nt':
        record=read_json(STATE/('image-process.json' if exe=='sd-server' else 'server-process.json'),{})
        if record.get('pid')!=pid:return False
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return False
        try:
            buffer=ctypes.create_unicode_buffer(32768);size=ctypes.c_ulong(len(buffer))
            return bool(kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(size))) and Path(buffer.value).name.lower() in {exe,exe+'.exe'}
        finally:kernel.CloseHandle(handle)
    try:
        proc=Path('/proc')/str(pid)
        if Path((proc/'exe').resolve()).name!=exe:return False
        args=(proc/'cmdline').read_bytes().decode('utf-8','replace').split('\0')
        return any(arg==flag and i+1<len(args) and args[i+1]==str(port) or arg==flag+'='+str(port) for i,arg in enumerate(args))
    except OSError:return False

def snapshot(refresh=False):
    global _cached,_stamp
    with _guard:
        if not refresh and _cached and time.monotonic()-_stamp<2:return _cached
        measured={}
        output=hardware.command(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],timeout=2)
        for row in csv.reader(io.StringIO(output)):
            try:measured[int(row[0].strip())]=int(row[1].strip())
            except (ValueError,IndexError):pass
        candidates=set(measured)
        for name in ['server-process.json','image-process.json']:
            pid=read_json(STATE/name,{}).get('pid')
            if isinstance(pid,int):candidates.add(pid)
        text={'state':'offline','name':None,'pid':None,'vram_mib':None}
        image=dict(text)
        for pid in candidates:
            if process_port(pid,'llama-server',SERVER_PORT,'--port'):text.update(pid=pid,vram_mib=measured.get(pid),state='loading')
            if process_port(pid,'sd-server',imaging.PORT,'--listen-port'):image.update(pid=pid,vram_mib=measured.get(pid),state='loading')
        try:
            data=runtime.api('/v1/models',timeout=.7)['data']
            if data:text.update(state='ready',name=data[0]['id'])
        except (OSError,ValueError,KeyError):pass
        try:
            data=imaging.api('/sdcpp/v1/models/status',timeout=.7)
            phase=data.get('state','empty');image['state']={'ready':'ready','loading':'loading','unloading':'loading','error':'error','empty':'idle'}.get(phase,'idle')
            models=data.get('models',{});main=models.get('diffusion_model') or models.get('model')
            image['name']=Path(main).name if main else None;image['recipe']=data.get('recipe');image['error']=data.get('error')
        except (OSError,ValueError,KeyError):pass
        active=[kind for kind,item in [('text',text),('image',image)] if item['state'] in {'ready','loading'}]
        _cached={'text':text,'image':image,'active':active,'measured_at':time.time(),'process_memory_available':bool(measured)};_stamp=time.monotonic()
        return _cached
