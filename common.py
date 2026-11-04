"""Portable paths and persistence; user data never lives in the installation directory."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import tempfile
import sys
for _stream in (sys.stdin,sys.stdout,sys.stderr):
    if hasattr(_stream,"reconfigure"):_stream.reconfigure(encoding="utf-8",errors="replace")

VERSION='0.4.1'
HOME=Path.home()
ROOT=Path(__file__).resolve().parent
if os.name=='nt':
    default=Path(os.environ.get('LOCALAPPDATA',HOME/'AppData/Local'))/'DedsecAI Studio'
else:
    default=Path(os.environ.get('XDG_DATA_HOME',HOME/'.local/share'))/'dedsecai-studio'
APP_HOME=Path(os.environ.get('DEDSECAI_HOME',default)).expanduser().resolve()
CONFIG=APP_HOME/'config'
STATE=APP_HOME/'state'
MODELS=APP_HOME/'models'
SERVER_PORT=int(os.environ.get('DEDSECAI_SERVER_PORT','1235'))
for d in (APP_HOME,CONFIG,STATE,MODELS):d.mkdir(parents=True,exist_ok=True)

def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as out:
            out.write(data);out.flush();os.fsync(out.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def read_json(path,default=None):
    p=Path(path)
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default

def write_json(path,data):atomic(path,json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def digest_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as src:
        for chunk in iter(lambda:src.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

@contextlib.contextmanager
def lock():
    with (CONFIG/'manager.lock').open('a+b') as out:
        if os.name=='nt':
            import msvcrt
            if out.tell()==0:out.write(b'0');out.flush()
            out.seek(0);msvcrt.locking(out.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(out,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:
            if os.name=='nt':out.seek(0);msvcrt.locking(out.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(out,fcntl.LOCK_UN)

@contextlib.contextmanager
def named_lock(name):
    """Short cross-process transactions, independent of long model jobs."""
    if not name.replace('-','').isalnum():raise ValueError('Invalid lock name')
    with (CONFIG/(name+'.lock')).open('a+b') as out:
        if os.name=='nt':
            import msvcrt
            if out.tell()==0:out.write(b'0');out.flush()
            out.seek(0);msvcrt.locking(out.fileno(),msvcrt.LK_LOCK,1)
        else:
            import fcntl
            fcntl.flock(out,fcntl.LOCK_EX)
        try:yield
        finally:
            if os.name=='nt':out.seek(0);msvcrt.locking(out.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(out,fcntl.LOCK_UN)
