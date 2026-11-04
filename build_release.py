"""Build the same six public packages and checksums for every release."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time
import build

ROOT=Path(__file__).resolve().parent

def main():
    import zstandard
    entries=build.build();dest=ROOT/'dist';version=build.VERSION
    sources=build.files()
    items=[('opt/dedsecai-studio/'+p.relative_to(ROOT).as_posix(),p.read_bytes(),0o755 if p.suffix=='.sh' else 0o644) for p in sources]
    items.extend([
        ('usr/bin/dedsecai',b'#!/bin/sh\nexec /usr/bin/python3 /opt/dedsecai-studio/cli.py "$@"\n',0o755),
        ('usr/share/applications/dedsecai-studio.desktop',b'[Desktop Entry]\nType=Application\nName=DedsecAI Studio\nExec=/usr/bin/dedsecai web\nIcon=applications-development\nTerminal=false\nCategories=Development;\n',0o644),
        ('usr/share/licenses/dedsecai-studio/LICENSE',(ROOT/'LICENSE').read_bytes(),0o644),
    ])
    info=f'pkgname = dedsecai-studio\npkgbase = dedsecai-studio\npkgver = {version}-1\npkgdesc = Local AI studio: chat, code and images\nurl = https://github.com/Dedseckms/DedsecAI-Studio\nbuilddate = {int(time.time())}\npackager = DedsecAI Studio contributors\nsize = {sum(len(data) for _,data,_ in items)}\narch = any\nlicense = MIT\ndepend = python\ndepend = tk\ndepend = xdg-utils\noptdepend = xterm: Pi terminal\n'
    items.insert(0,('.PKGINFO',info.encode(),0o644))
    archive=io.BytesIO()
    with tarfile.open(fileobj=archive,mode='w') as tar:
        for name,data,mode in items:
            member=tarfile.TarInfo(name);member.mode=mode;member.size=len(data);member.mtime=int(time.time());member.uname=member.gname='root'
            tar.addfile(member,io.BytesIO(data))
    arch=dest/f'dedsecai-studio-{version}-1-any.pkg.tar.zst'
    arch.write_bytes(zstandard.ZstdCompressor(level=19).compress(archive.getvalue()))
    entries.append({'file':arch.name,'label':'Arch Linux · pacman'})
    compiler=shutil.which('makensis')
    if not compiler:raise SystemExit('NSIS compiler required: apt install nsis / install NSIS on Windows')
    exe=dest/f'DedsecAI-Studio-{version}-Setup.exe'
    with tempfile.TemporaryDirectory() as folder:
        payload=Path(folder)/'payload';payload.mkdir()
        for p in sources:
            target=payload/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        prefix='/D' if __import__('os').name=='nt' else '-D'
        subprocess.run([compiler,prefix+'VERSION='+version,prefix+'PAYLOAD='+str(payload),prefix+'OUTPUT='+str(exe),str(ROOT/'installers/windows-setup.nsi')],check=True)
    entries.append({'file':exe.name,'label':'Windows · EXE'})
    # Rebuild the manifest from these exact outputs; never carry old release assets.
    entries=list({e['file']:e for e in entries}.values())
    for entry in entries:entry['sha256']=hashlib.sha256((dest/entry['file']).read_bytes()).hexdigest()
    (dest/'manifest.json').write_text(json.dumps({'version':version,'files':entries},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (dest/'SHA256SUMS').write_text(''.join(f"{e['sha256']}  {e['file']}\n" for e in entries),encoding='utf-8')
    notes=(ROOT/'packaging/release-notes.md').read_text(encoding='utf-8').replace('@VERSION@',version)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    notes=notes.replace('@COMMIT@',commit)
    (dest/'release-notes.md').write_text(notes,encoding='utf-8')
    print(json.dumps(entries,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
