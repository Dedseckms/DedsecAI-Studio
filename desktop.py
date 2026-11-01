"""Native dialogs and terminal launchers on Windows and Linux."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from common import HOME,ROOT,APP_HOME,CONFIG,read_json

def choose(kind='directory',initial=None):
    initial=str(initial or HOME/'Projects')
    if os.name!='nt' and shutil.which('kdialog'):
        args=['kdialog','--title','DedsecAI Studio — выбор проекта' if kind=='directory' else 'DedsecAI Studio — импорт GGUF',
              '--getexistingdirectory' if kind=='directory' else '--getopenfilename',initial]
        if kind!='directory':args.append('*.gguf *.safetensors *.ckpt | Image models' if kind=='image' else '*.gguf | GGUF models')
        r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',timeout=600)
        if r.returncode==1:return None
        if r.returncode:raise ValueError('Не удалось открыть диалог. Укажите путь вручную.')
        return r.stdout.strip() or None
    try:
        import tkinter
        from tkinter import filedialog
        root=tkinter.Tk();root.withdraw();root.attributes('-topmost',True)
        try:
            return (filedialog.askdirectory(title='Выбери папку проекта',initialdir=initial) if kind=='directory' else filedialog.askopenfilename(title='Выбери GGUF',initialdir=initial,filetypes=[('Image models','*.gguf *.safetensors *.ckpt')] if kind=='image' else [('GGUF','*.gguf')])) or None
        finally:root.destroy()
    except (ImportError,RuntimeError) as exc:raise ValueError('Диалог недоступен. Укажите полный путь вручную; на Linux можно установить python3-tk / tk.') from exc

def pi_available():
    return bool(shutil.which('pi') or (HOME/'.local/bin/pi').exists() or (APP_HOME/'pi/node_modules/@earendil-works/pi-coding-agent/dist/cli.js').exists())

def pi_command():
    package=APP_HOME/'pi/node_modules/@earendil-works/pi-coding-agent/dist/cli.js'
    if package.exists():
        node=read_json(CONFIG/'node.json',{}).get('executable')
        if not node:raise ValueError('Node.js для Pi не настроен.')
        return [node,str(package)]
    executable=shutil.which('pi')
    if not executable and (HOME/'.local/bin/pi').exists():executable=str(HOME/'.local/bin/pi')
    if not executable:raise ValueError('Pi не установлен. Установите его в разделе «Система».')
    return [executable]

def launch_pi(path):
    args=[sys.executable,str(ROOT/'cli.py'),'pi','--project',str(path)]
    if os.name=='nt':
        # CreateProcess receives an argument list; never interpolate the project into PowerShell.
        subprocess.Popen(args,cwd=path,creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        terms=[('konsole',['--separate','--workdir',str(path),'-e']),('gnome-terminal',['--working-directory='+str(path),'--']),
               ('xfce4-terminal',['--working-directory='+str(path),'--disable-server','-x']),('xterm',['-e'])]
        choice=next(((name,opts) for name,opts in terms if shutil.which(name)),None)
        if not choice:raise ValueError('Терминал не найден. Установите Konsole, GNOME Terminal, XFCE Terminal или xterm.')
        command=[choice[0],*choice[1],*args]
        env=dict(os.environ)
        if shutil.which('systemd-run') and os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
            command=['systemd-run','--user','--collect','--unit=dedsecai-pi-'+os.urandom(4).hex(),*command]
        subprocess.Popen(command,cwd=path,env=env,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return {'path':str(path),'message':'Pi открыт в отдельном терминале.'}
