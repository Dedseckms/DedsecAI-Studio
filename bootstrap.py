"""Explicit runtime/Pi installation. No model is downloaded during setup."""
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from common import APP_HOME,CONFIG,ROOT,STATE,digest_file,read_json,write_json


def fetch(url,dest,expected=None):
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(url,timeout=60) as src,dest.open('wb') as out:
        for chunk in iter(lambda:src.read(2*1024*1024),b''):out.write(chunk)
    if expected and digest_file(dest)!=expected.removeprefix('sha256:'):raise ValueError('SHA-256 установочного архива не совпал.')
    return dest


def extract(archive,dest):
    dest=Path(dest).resolve();dest.mkdir(parents=True,exist_ok=True)
    def safe(name):
        target=(dest/name).resolve()
        if target!=dest and dest not in target.parents:raise ValueError('Небезопасный путь в архиве runtime.')
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as src:
            for item in src.infolist():safe(item.filename)
            src.extractall(dest)
    else:
        with tarfile.open(archive) as src:
            for item in src.getmembers():
                safe(item.name)
                if item.isdir() or item.isfile():
                    if sys.version_info>=(3,12):src.extract(item,dest,filter='data')
                    else:src.extract(item,dest)


def setup_runtime(backend='auto'):
    import runtime
    if backend=='auto':
        try:
            exe=runtime.binary();subprocess.run([exe,'--version'],check=True,capture_output=True,timeout=10)
            write_json(CONFIG/'runtime.json',{'executable':exe,'backend':'existing'})
            print('Используется установленный llama.cpp: '+exe,flush=True);return exe
        except (ValueError,OSError,subprocess.SubprocessError):pass
    manifest=read_json(ROOT/'assets/runtime.json');tag=manifest['tag'];arch=platform.machine().lower()
    arch='arm64' if arch in {'aarch64','arm64'} else 'x64' if arch in {'x86_64','amd64'} else arch
    if os.name=='nt':
        selected='vulkan' if backend=='auto' else backend
        if selected not in {'cpu','vulkan'}:raise ValueError('Windows-установщик поддерживает CPU или Vulkan. Собственный CUDA llama-server можно указать через DEDSECAI_LLAMA_SERVER.')
        name=f'llama-{tag}-bin-win-{selected}-{arch}.zip'
        asset=next((a for a in manifest['assets'] if a['name']==name),None)
        if not asset:raise ValueError('Для этой архитектуры нет закреплённого runtime. Укажите собственный llama-server.')
        if not asset.get('digest'):raise ValueError('Для runtime отсутствует контрольная сумма.')
        archive=fetch(asset['url'],STATE/'downloads'/name,asset['digest'])
        dest=APP_HOME/'runtime'/tag/selected;extract(archive,dest)
        exe=next(dest.rglob('llama-server.exe'),None)
        if not exe:raise ValueError('В архиве нет llama-server.exe.')
        subprocess.run([str(exe),'--version'],check=True,capture_output=True,timeout=20)
    else:
        for tool in ['cmake','c++']:
            if not shutil.which(tool):raise ValueError('Для сборки нужны cmake и компилятор C++. Запустите установщик Arch/Debian для зависимостей.')
        selected=backend
        if selected=='auto':selected='vulkan' if shutil.which('glslc') else 'cpu'
        if selected not in {'cpu','vulkan','cuda'}:raise ValueError('Backend: auto, cpu, vulkan или cuda.')
        if selected=='cuda' and not shutil.which('nvcc'):raise ValueError('Для CUDA-сборки нужен nvcc. Используйте Vulkan/CPU или готовый llama-server.')
        source_url=manifest.get('source_url',f'https://github.com/ggml-org/llama.cpp/archive/refs/tags/{tag}.tar.gz')
        archive=fetch(source_url,STATE/'downloads'/f'{tag}.tar.gz',manifest.get('source_sha256'))
        source=APP_HOME/'runtime'/tag/'source';extract(archive,source)
        cmake_file=next(source.glob('*/CMakeLists.txt'),None)
        if not cmake_file:raise ValueError('Исходники llama.cpp не найдены в архиве.')
        src=cmake_file.parent;build=APP_HOME/'runtime'/tag/selected/'build'
        flags=['-DGGML_NATIVE=OFF','-DLLAMA_CURL=OFF','-DLLAMA_BUILD_TESTS=OFF',
               '-DGGML_VULKAN='+('ON' if selected=='vulkan' else 'OFF'),'-DGGML_CUDA='+('ON' if selected=='cuda' else 'OFF')]
        subprocess.run(['cmake','-S',str(src),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release',*flags],check=True)
        subprocess.run(['cmake','--build',str(build),'--config','Release','--target','llama-server','-j',str(min(os.cpu_count() or 2,6))],check=True)
        exe=next(build.rglob('llama-server'),None)
        if not exe:raise ValueError('Сборка не создала llama-server.')
    write_json(CONFIG/'runtime.json',{'executable':str(exe.resolve()),'backend':selected,'release':tag})
    print('llama.cpp установлен: '+str(exe),flush=True);return str(exe)


def setup_node():
    candidates=[shutil.which('node'),str(Path.home()/'.local/share/pi-node/current/bin/node'),read_json(CONFIG/'node.json',{}).get('executable')]
    for candidate in candidates:
        if not candidate or not Path(candidate).is_file():continue
        try:
            version=subprocess.check_output([candidate,'--version'],text=True).strip().lstrip('v')
            v=tuple(int(x) for x in version.split('.')[:3])
            if v>=(22,19,0):
                root=Path(candidate).resolve().parent
                npm=next((p for p in [root/'node_modules/npm/bin/npm-cli.js',root.parent/'lib/node_modules/npm/bin/npm-cli.js'] if p.exists()),None)
                if npm:write_json(CONFIG/'node.json',{'executable':str(Path(candidate).resolve()),'npm':str(npm)});return candidate,npm
        except (OSError,subprocess.SubprocessError,ValueError):pass
    version='v22.23.3';arch=platform.machine().lower();arch='arm64' if arch in {'arm64','aarch64'} else 'x64' if arch in {'x86_64','amd64'} else arch
    system='win' if os.name=='nt' else 'linux'
    extension='zip' if os.name=='nt' else 'tar.xz'
    filename=f'node-{version}-{system}-{arch}.{extension}';base=f'https://nodejs.org/dist/{version}/'
    with urllib.request.urlopen(base+'SHASUMS256.txt',timeout=30) as r:checksums=r.read().decode()
    match=next((line.split()[0] for line in checksums.splitlines() if line.split()[-1]==filename),None)
    if not match:raise ValueError('Для этой архитектуры не найден проверяемый Node.js.')
    archive=fetch(base+filename,STATE/'downloads'/filename,match);dest=APP_HOME/'node';extract(archive,dest)
    exe=next(dest.rglob('node.exe' if os.name=='nt' else 'node'),None)
    npm=next(dest.rglob('npm-cli.js'),None)
    if not exe or not npm:raise ValueError('Архив Node.js неполный.')
    write_json(CONFIG/'node.json',{'executable':str(exe),'npm':str(npm)});return str(exe),npm


def setup_pi():
    import desktop
    if desktop.pi_available():print('Pi уже установлен.',flush=True);return
    node,npm=setup_node();env=dict(os.environ)
    env['PATH']=str(Path(node).parent)+os.pathsep+env.get('PATH','')
    subprocess.run([str(node),str(npm),'install','--prefix',str(APP_HOME/'pi'),'--ignore-scripts','--no-audit','--no-fund','@earendil-works/pi-coding-agent@1.1.0'],check=True,env=env)
    if not desktop.pi_available():raise ValueError('Pi установлен, но CLI не найден. Проверьте журнал установки.')
    target=Path.home()/'.pi/agent/extensions'
    for source in (ROOT/'pi-extensions').iterdir():
        if source.is_dir():
            dest=target/source.name
            if dest.exists():shutil.copytree(dest,APP_HOME/'backups'/('pi-'+source.name+'-'+str(int(__import__('time').time()))),dirs_exist_ok=True)
            shutil.copytree(source,dest,dirs_exist_ok=True)
    print('Pi установлен.',flush=True)
