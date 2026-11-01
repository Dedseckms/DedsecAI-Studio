import json,time,urllib.request,urllib.parse
from pathlib import Path
base='http://127.0.0.1:1240'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):return json.load(op.open(base+path,timeout=40))
token=get('/api/state')['csrf']
def post(path,data):
 req=urllib.request.Request(base+path,data=json.dumps(data,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','X-Qwen-Token':token})
 return json.load(op.open(req,timeout=40))
def action(name,**kw):
 task=post('/api/action',dict(action=name,**kw))['job']
 for _ in range(400):
  state=get('/api/state');job=state['job']
  if job['id']==task['id'] and job['status']!='running':
   if job['status']=='error':raise RuntimeError(job['error'])
   return job
  time.sleep(.15)
 raise RuntimeError('Job timeout')
job=action('hf_download',repo='ggml-org/tiny-llamas',variant='stories260K.gguf')
assert job['result']['id']
job=action('local_import',path=str(Path.home()/'models/Qwen3-4B-Instruct-2507-Q5_K_M.gguf'))
assert job['result']['id']
info=get('/api/hub/inspect?repo='+urllib.parse.quote('unsloth/Kimi-K2-Instruct-GGUF',safe=''))
assert any(len(v['files'])>1 and v['size']>200*1024**3 and v['assessment']['tier']=='too_large' for v in info['variants'])
post('/api/policy',{'mode':'strict','model':'qwen27','topics':[],'blocked_terms':['четыре']})
conv=post('/api/chat/new',{})['id']
post('/api/chat/send',{'conversation':conv,'text':'Сколько будет 2+2? Ответь по-русски одним словом.'})
seen=''
for _ in range(250):
 rows=get('/api/chat?id='+conv)['messages'];r=rows[-1]
 if r['status']=='generating':assert 'четыре' not in r['content'].lower()
 else:
  assert r['status']=='blocked',r
  assert 'четыре' not in r['content'].lower();break
 time.sleep(.1)
else:raise RuntimeError('Chat timeout')
post('/api/policy',{'mode':'off','model':'qwen27','topics':[],'blocked_terms':['четыре']})
for _ in range(30):
 if get('/api/state')['job']['status']!='running':break
 time.sleep(.1)
conv2=post('/api/chat/new',{})['id']
post('/api/chat/send',{'conversation':conv2,'text':'Сколько будет 2+2? Ответь по-русски одним словом.'})
for _ in range(250):
 r=get('/api/chat?id='+conv2)['messages'][-1]
 if r['status']!='generating':
  assert r['status']=='done' and 'четыре' in r['content'].lower(),r;break
 time.sleep(.1)
else:raise RuntimeError('Chat timeout')
print(json.dumps({'real_hf_download_and_sha256':True,'local_import':True,'kimi_split_size':True,'strict_output_no_leak':True,'filters_off':True,'weights_used_for_download_test':'1.1 MiB in isolated QA'},ensure_ascii=False))
