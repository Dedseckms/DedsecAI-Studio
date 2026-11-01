"""One long operation, JSON on stdin, progress on stdout."""
import json
import sys
from pathlib import Path
import manager
import runtime
import hub
import bootstrap
from common import lock

def run(data):
 action=data['action']
 with lock():
  if action=='start':manager.start()
  elif action=='stop':
   runtime.stop()
   import imaging
   imaging.stop()
  elif action=='restart':runtime.stop();manager.start()
  elif action=='download':return manager.downloaded(manager.model(data['id']))
  elif action=='profile':return manager.set_profile(data['id'],data.get('ctx'),data.get('mmproj'))
  elif action.startswith('image_'):
   import imaging
   return imaging.run(action,data)
  elif action=='use':manager.activate(manager.model(data['id']),data.get('allow_cpu') is True)
  elif action=='bench':return manager.benchmark(manager.model(manager.selected()))
  elif action=='hf_download':
   item=hub.register_repo(data.get('repo'),data.get('variant'),data.get('revision'),data.get('projector'));return manager.downloaded(item)
  elif action=='url_download':
   item=hub.inspect_url(data.get('url'),data.get('sha256') or None);hub.save_custom(item);return manager.downloaded(item)
  elif action=='local_import':return {'id':manager.add(data['path'])['id']}
  elif action=='setup_runtime':return {'executable':bootstrap.setup_runtime(data.get('backend','auto'))}
  elif action=='setup_pi':bootstrap.setup_pi()
  else:raise ValueError('Неизвестная операция.')
 return {'message':'Готово.'}
if __name__=='__main__':
 try:print('RESULT '+json.dumps(run(json.load(sys.stdin)),ensure_ascii=False),flush=True)
 except Exception as exc:print('Ошибка: '+str(exc),file=sys.stderr,flush=True);sys.exit(1)
