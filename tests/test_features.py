"""Regression checks for cancellation, context overrides, vision and automatic memory."""
import base64
import copy
import contextlib
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import companion
import manager
import hardware
import hub
import runtime
from common import write_json

class FeatureDataTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.patches=[patch.object(companion,'DATA',self.root),patch.object(companion,'DB_PATH',self.root/'chat.sqlite3'),patch.object(companion,'CONFIG',self.root)]
  for p in self.patches:p.start()
  companion.init()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def test_automatic_memory_survives_and_corrects_name(self):
  companion.auto_remember('Меня зовут Алексей.',1)
  companion.auto_remember('Меня зовут Иван.',2)
  companion.init();rows=companion.memories()
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['content'],'Меня зовут Иван');self.assertEqual(rows[0]['source_message'],2)
  with companion.db() as con:self.assertEqual(con.execute('SELECT count(*) FROM memory_history').fetchone()[0],1)
 def test_automatic_memory_does_not_overwrite_manual_correction(self):
  companion.auto_remember('Меня зовут Иван.',1);row=companion.memories()[0]
  companion.save_memory('Имя: Алексей',row['id']);companion.auto_remember('Меня зовут Пётр.',2)
  self.assertEqual(companion.memories()[0]['content'],'Имя: Алексей')
 def test_examples_secrets_and_questions_are_not_facts(self):
  for text in ['Представь, меня зовут Иван.','Например, я люблю Rust.','Меня зовут Иван?','Мой пароль secret, я люблю Python.','Он сказал "меня зовут Иван".']:
   companion.auto_remember(text,1)
  self.assertEqual(companion.memories(),[])
 def test_image_round_trip_and_multimodal_context(self):
  raw=b'\x89PNG\r\n\x1a\n'+b'test'
  value='data:image/png;base64,'+base64.b64encode(raw).decode()
  class FakeManager:
   selected=staticmethod(lambda:'vision')
   model=staticmethod(lambda _:dict(mmproj='projector.gguf'))
  conv=companion.create();engine=companion.ChatEngine(FakeManager())
  task=engine.prepare(conv['id'],'Что на картинке?',[value])
  message=companion.overview(conv['id'])['messages'][0]
  self.assertEqual(companion.attachment(message['images'][0]['id'])[1],raw)
  parts=companion.message_content(message,{'mmproj':'x'})
  self.assertEqual(parts[1]['image_url']['url'],value)
  self.assertEqual(companion.message_content(message,{}),'Что на картинке?')
 def test_non_vision_model_rejects_image_before_storing_message(self):
  class FakeManager:
   selected=staticmethod(lambda:'text')
   model=staticmethod(lambda _:dict())
  conv=companion.create();engine=companion.ChatEngine(FakeManager())
  image='data:image/png;base64,'+base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()
  with self.assertRaises(ValueError):engine.prepare(conv['id'],'Image',[image])
  self.assertEqual(companion.overview(conv['id'])['messages'],[])
 def test_mime_spoof_rejected(self):
  with self.assertRaises(ValueError):companion.validate_images(['data:image/png;base64,'+base64.b64encode(b'<script>x</script>').decode()])

class ProfileTests(unittest.TestCase):
 def test_custom_context_survives_hardware_recalculation(self):
  raw={'id':'a','size':10,'native_ctx':131072}
  with tempfile.TemporaryDirectory() as d,patch.object(manager,'CONFIG',Path(d)),patch.object(manager,'raw_catalog',return_value=[raw]):
   write_json(Path(d)/'profiles.json',{'a':{'ctx':65536}})
   self.assertEqual(manager.model('a')['ctx'],65536)
   self.assertTrue(manager.model('a')['custom_ctx'])
 def test_large_context_keeps_more_than_32_messages(self):
  class FakeManager:
   api=staticmethod(lambda path,*a,**k: {'prompt':'history'} if path=='/apply-template' else {'tokens':list(range(100))})
  rows=[{'id':i,'role':'user' if i%2==0 else 'assistant','content':'Long conversation message '+str(i),'status':'done'} for i in range(70)]
  engine=companion.ChatEngine(FakeManager())
  with patch.object(companion,'overview',return_value={'messages':rows}),patch.object(companion,'search',return_value=[]),patch.object(companion,'memories',return_value=[]):
   messages,sources,output=engine.context({'conversation':'test','text':'continue'},{'id':'test','ctx':65536})
  self.assertEqual(len(messages),71);self.assertEqual(output,4096)
 def test_native_context_limit_rejected(self):
  with patch.object(manager,'model',return_value={'native_ctx':8192}):
   for value in [True,8193,0,'4096']:
    with self.assertRaises(ValueError):manager.set_profile('a',value)
 def test_projectors_are_separate_from_text_variants(self):
  rows=[{'rfilename':'model.gguf','size':100},{'rfilename':'mmproj-F16.gguf','size':20}]
  self.assertEqual(hub.groups(rows)[0]['variant'],'model.gguf')
  self.assertEqual(hub.groups(rows,True)[0]['variant'],'mmproj-F16.gguf')
 def test_cancel_interrupts_readiness_wait(self):
  event=threading.Event();event.set()
  with self.assertRaises(InterruptedError):runtime.wait_ready({'alias':'a','ctx':4096},150,event)
 def test_download_is_followed_by_benchmark_and_previous_model_restore(self):
  item={'id':'new','tier':'gpu'};old={'id':'old'}
  with patch.object(manager,'download'),patch.object(manager,'model',side_effect=lambda ident:item if ident=='new' else old),patch.object(manager,'selected',return_value='old'),patch.object(runtime,'healthy',return_value=True),patch.object(manager,'activate') as activate,patch.object(manager,'benchmark',return_value={'tokens_per_second':50}) as bench,patch.object(runtime,'stop'),patch.object(runtime,'start') as start,patch.object(manager,'environment'),patch.object(manager,'sync_pi'):
   result=manager.downloaded(item)
   activate.assert_called_once_with(item,allow_cpu=True);bench.assert_called_once_with(item);start.assert_called_once_with(old)
   self.assertEqual(result['benchmark']['tokens_per_second'],50)

class CancellationTests(unittest.TestCase):
 def test_stop_preempts_stuck_worker_without_stale_completion(self):
  import server
  real_popen=subprocess.Popen;calls=[]
  def child(*args,**kwargs):
   if args and args[0][0]=='taskkill':return real_popen(*args,**kwargs)
   calls.append(1)
   code='import time;time.sleep(30)' if len(calls)==1 else 'print(\'RESULT {"message":"stopped"}\')'
   return real_popen([os.sys.executable,'-c',code],**kwargs)
  with patch.object(server.subprocess,'Popen',side_effect=child),patch.object(server,'job',None),patch.object(server,'active_thread',None),patch.object(server,'active_process',None):
   first=server.submit('start',{})
   for _ in range(100):
    if server.active_process is not None:break
    time.sleep(.01)
   old=server.job;started=time.monotonic();second=server.submit('stop',{})
   server.active_thread.join(5)
   self.assertLess(time.monotonic()-started,5)
   self.assertEqual(old['status'],'cancelled');self.assertEqual(server.job['id'],second['id']);self.assertEqual(server.job['status'],'done')

if __name__=='__main__':unittest.main()
