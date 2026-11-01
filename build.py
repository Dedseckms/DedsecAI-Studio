"""Build portable installers and an architecture-independent Debian package using stdlib."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time
import sys
for stream in (sys.stdout,sys.stderr):
    if hasattr(stream,"reconfigure"):stream.reconfigure(encoding="utf-8",errors="replace")
import zipfile

ROOT=Path(__file__).resolve().parent
VERSION='0.4.0'
FILES=['common.py','hardware.py','hub.py','gguf.py','runtime.py','manager.py','moderation.py','desktop.py','bootstrap.py','cli.py','server.py','worker.py','companion.py','imaging.py','resources.py','image_hub.py','build.py','README.md','LICENSE']
DIRS=['assets','static','pi-extensions','installers','packaging']

def files():
    result=[ROOT/n for n in FILES if (ROOT/n).is_file()]
    for name in DIRS:
        result.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc'} and not p.name.endswith(('.pkg.tar.zst','.tar.gz')))
    return sorted(set(result))

def tar_bytes(items):
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w:gz') as tar:
        parents=set()
        for name,_,_ in items:
            parents.update(p.as_posix() for p in Path(name).parents if p.as_posix()!='.')
        for directory in sorted(parents,key=lambda p:(p.count('/'),p)):
            info=tarfile.TarInfo(directory);info.type=tarfile.DIRTYPE;info.mode=0o755;tar.addfile(info)
        for name,data,mode in items:
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=mode;info.mtime=int(time.time());tar.addfile(info,io.BytesIO(data))
    return out.getvalue()

def ar(items):
    out=bytearray(b'!<arch>\n')
    for name,data in items:
        header=f'{name+"/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(data):<10}`\n'.encode('ascii')
        out+=header+data
        if len(data)%2:out+=b'\n'
    return bytes(out)

def build():
    dest=ROOT/'dist';dest.mkdir(exist_ok=True);sources=files();folder=f'DedsecAI-Studio-{VERSION}';result=[]
    win=dest/f'{folder}-windows.zip'
    with zipfile.ZipFile(win,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sources:z.write(p,folder+'/'+p.relative_to(ROOT).as_posix())
    result.append({'file':win.name,'label':'Windows · ZIP + CMD/PowerShell'})
    for system in ['arch','debian']:
        archive=dest/f'{folder}-{system}.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            for p in sources:tar.add(p,arcname=folder+'/'+p.relative_to(ROOT).as_posix(),recursive=False)
        result.append({'file':archive.name,'label':system.capitalize()+' · установщик tar.gz'})
    control=f'''Package: dedsecai-studio
Version: {VERSION}
Architecture: all
Maintainer: DedsecAI Studio contributors
Section: science
Priority: optional
Depends: python3 (>= 3.10), python3-tk, xdg-utils
Recommends: cmake, g++, git, libvulkan-dev, glslc, xterm
Description: Local AI studio with GGUF catalog, chat, memory and hardware profiles
 Model weights and runtime are downloaded separately by the user.
'''.encode()
    controltar=tar_bytes([('control',control,0o644)])
    app=[('opt/dedsecai-studio/'+p.relative_to(ROOT).as_posix(),p.read_bytes(),0o755 if p.suffix=='.sh' else 0o644) for p in sources]
    app.append(('usr/bin/dedsecai',b'#!/bin/sh\nexec /usr/bin/python3 /opt/dedsecai-studio/cli.py "$@"\n',0o755))
    desktop=b'[Desktop Entry]\nType=Application\nName=DedsecAI Studio\nExec=/usr/bin/dedsecai web\nIcon=applications-development\nTerminal=false\nCategories=Development;\n'
    app.append(('usr/share/applications/dedsecai-studio.desktop',desktop,0o644))
    app.append(('usr/share/licenses/dedsecai-studio/LICENSE',(ROOT/'LICENSE').read_bytes(),0o644))
    deb=dest/f'dedsecai-studio_{VERSION}_all.deb';deb.write_bytes(ar([('debian-binary',b'2.0\n'),('control.tar.gz',controltar),('data.tar.gz',tar_bytes(app))]))
    result.append({'file':deb.name,'label':'Debian / Ubuntu · DEB'})
    previous=json.loads((dest/'manifest.json').read_text(encoding='utf-8')) if (dest/'manifest.json').exists() else {'files':[]}
    names={r['file'] for r in result}
    for extra in previous['files']:
        if VERSION in extra['file'] and extra['file'] not in names and (dest/extra['file']).exists():result.append(extra)
    for entry in result:entry['sha256']=hashlib.sha256((dest/entry['file']).read_bytes()).hexdigest()
    (dest/'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['file']}\n" for r in result),encoding='utf-8')
    (dest/'manifest.json').write_text(json.dumps({'version':VERSION,'files':result},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':build()
