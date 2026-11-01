#!/usr/bin/env python3
"""Build a real Windows NSIS setup from a clean application payload."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build import files,VERSION

def build(makensis=None):
    compiler=makensis or shutil.which('makensis') or shutil.which('makensis.exe')
    if not compiler:raise ValueError('Install NSIS 3 and put makensis on PATH, or pass --makensis PATH.')
    dest=ROOT/'dist';dest.mkdir(exist_ok=True)
    output=dest/f'DedsecAI-Studio-{VERSION}-Setup.exe'
    with tempfile.TemporaryDirectory(prefix='dedsecai-windows-payload-') as temporary:
        payload=Path(temporary)/'payload';payload.mkdir()
        for source in files():
            target=payload/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        script=ROOT/'installers/windows-setup.nsi'
        flags=['/V3',f'/DPAYLOAD={payload}',f'/DOUTPUT={output}',f'/DVERSION={VERSION}'] if os.name=='nt' else ['-V3',f'-DPAYLOAD={payload}',f'-DOUTPUT={output}',f'-DVERSION={VERSION}']
        subprocess.run([str(compiler),*flags,str(script)],check=True)
    data=output.read_bytes()
    if data[:2]!=b'MZ':raise ValueError('Compiler did not create a Windows PE executable.')
    pe=int.from_bytes(data[0x3c:0x40],'little')
    if data[pe:pe+4]!=b'PE\0\0':raise ValueError('Invalid PE header.')
    manifest=dest/'manifest.json'
    info=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {'version':VERSION,'files':[]}
    row={'file':output.name,'label':'Windows · мастер установки EXE','sha256':hashlib.sha256(data).hexdigest()}
    info['files']=[row]+[r for r in info['files'] if r['file']!=output.name]
    manifest.write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (dest/'SHA256SUMS').write_text(''.join(r['sha256']+'  '+r['file']+'\n' for r in info['files']),encoding='utf-8')
    print(json.dumps({'file':str(output),'bytes':len(data),'sha256':row['sha256']},indent=2));return output

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--makensis');args=parser.parse_args()
    try:build(args.makensis)
    except (ValueError,OSError,subprocess.SubprocessError) as exc:print(str(exc),file=sys.stderr);sys.exit(1)
