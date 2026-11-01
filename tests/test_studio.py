import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import common
import hardware
import hub
import manager
import moderation
import bootstrap
import companion


def machine(ram=16,vram=12,gpu=True):
 return {'os':'Windows' if not gpu else 'Linux','arch':'x86_64','cpu':'Test CPU','cores':6,'threads':12,'ram_bytes':int(ram*1024**3),'ram_available_bytes':int((ram-3)*1024**3),'gpus':[{'name':'GPU','vram_bytes':int(vram*1024**3),'free_bytes':int(vram*1024**3)}] if gpu else [],'fingerprint':'test-hardware','disk_free_bytes':100*1024**3}

class HardwareTests(unittest.TestCase):
 def test_small_model_fits_12gb_gpu(self):
  p=hardware.plan({'size':3*1024**3,'geometry':[36,8,128]},machine())
  self.assertEqual(p['tier'],'gpu');self.assertEqual(p['ctx'],32768)
 def test_same_model_changes_profile_on_4gb_gpu(self):
  p=hardware.plan({'size':3*1024**3,'geometry':[36,8,128]},machine(vram=4))
  self.assertNotEqual(p['ctx'],32768);self.assertIn(p['tier'],['gpu','hybrid'])
 def test_cpu_only_has_no_fake_vram(self):
  self.assertEqual(hardware.plan({'size':2*1024**3},machine(gpu=False))['tier'],'cpu')
 def test_kimi_cannot_fit_small_pc(self):
  self.assertEqual(hardware.plan({'size':261*1024**3},machine())['tier'],'too_large')
 def test_large_machine_can_offer_hybrid_kimi(self):
  self.assertEqual(hardware.plan({'size':261*1024**3},machine(ram=512,vram=80))['tier'],'hybrid')
 def test_verified_profile_is_only_reused_on_matching_hardware(self):
  item={'size':10*1024**3,'verified_hardware':'test-hardware','ctx':32768,'cache':'q4_0','gpu_layers':'all'}
  self.assertTrue(hardware.plan(item,machine())['verified'])
  hw=machine(vram=4);hw['fingerprint']='different'
  self.assertFalse(hardware.plan(item,hw)['verified'])

class HubTests(unittest.TestCase):
 def test_split_groups_include_all_bytes(self):
  rows=[{'rfilename':f'Q4/model-0000{i}-of-00002.gguf','size':i*100,'lfs':{'sha256':str(i)*64}} for i in [1,2]]
  rows.append({'rfilename':'mmproj-model.gguf','size':10})
  group=hub.groups(rows)[0]
  self.assertEqual(group['size'],300);self.assertEqual(len(group['files']),2)
 def test_incomplete_split_is_not_offered(self):
  self.assertEqual(hub.groups([{'rfilename':'m-00001-of-00002.gguf','size':10}]),[])
 def test_repo_links_normalize(self):
  self.assertEqual(hub.repo_id('https://huggingface.co/owner/repo/tree/main'),'owner/repo')
  with self.assertRaises(ValueError):hub.repo_id('https://evil.example/owner/repo')
 def test_local_and_non_https_downloads_rejected(self):
  for url in ['file:///etc/passwd','http://example.org/m.gguf','https://127.0.0.1/m.gguf','https://user:pass@example.org/m.gguf']:
   with self.assertRaises(ValueError):hub.validate_url(url)
 def test_safetensors_not_a_gguf_variant(self):
  self.assertEqual(hub.groups([{'rfilename':'model.safetensors','size':100}]),[])
 def test_archive_path_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('../escape','bad')
   with self.assertRaises(ValueError):bootstrap.extract(p,Path(d)/'out')
   self.assertFalse((Path(d)/'escape').exists())

class DataTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.patches=[patch.object(moderation,'CONFIG',self.root),patch.object(companion,'DATA',self.root),patch.object(companion,'DB_PATH',self.root/'chat.sqlite3')]
  for p in self.patches:p.start()
  companion.init()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def test_off_means_no_app_filter(self):
  self.assertIsNone(moderation.check('blocked',{'mode':'off','blocked_terms':['blocked']}))
 def test_policy_has_model_overrides(self):
  moderation.save({'mode':'strict','model':'a','topics':[],'blocked_terms':['запрет']})
  self.assertIsNotNone(moderation.check('ЗАПРЕТ',moderation.effective('a')))
  self.assertIsNone(moderation.check('ЗАПРЕТ',moderation.effective('b')))
 def test_unknown_topics_rejected(self):
  with self.assertRaises(ValueError):moderation.save({'mode':'strict','topics':['unknown']})
 def test_strict_mode_buffers(self):
  self.assertTrue(moderation.buffered({'mode':'strict'}))
  self.assertTrue(moderation.buffered({'mode':'custom','blocked_terms':['x']}))
  self.assertFalse(moderation.buffered({'mode':'off','blocked_terms':['x']}))
 def test_blocked_input_is_not_saved_as_message(self):
  moderation.save({'mode':'strict','topics':[],'blocked_terms':['секрет']})
  class FakeManager:
   @staticmethod
   def selected():return 'a'
  conv=companion.create();engine=companion.ChatEngine(FakeManager())
  with self.assertRaises(ValueError):engine.prepare(conv['id'],'Мой секрет')
  self.assertEqual(companion.overview(conv['id'])['messages'],[])
 def test_memory_and_history_survive_reinit(self):
  companion.save_memory('Мой язык — Rust.')
  conv=companion.create();companion.init()
  self.assertEqual(len(companion.memories()),1);self.assertEqual(companion.conversation(conv['id'])['id'],conv['id'])
 def test_buffered_banned_output_is_never_saved_raw(self):
  moderation.save({'mode':'strict','topics':[],'blocked_terms':['forbidden']})
  class FakeManager:
   selected=staticmethod(lambda:'a')
   lock=staticmethod(contextlib.nullcontext)
   model=staticmethod(lambda _:dict(id='a',alias='a',ctx=4096))
   api=staticmethod(lambda *a,**k:{'status':'ok'})
   wait_ready=staticmethod(lambda *a:None)
  conv=companion.create();engine=companion.ChatEngine(FakeManager());task=engine.prepare(conv['id'],'Hello')
  class Response:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def __iter__(self):
    for text in ['safe ','forbidden',' ending']:
     # No raw streaming content may reach the database before the final check.
     self_test.assertEqual(companion.overview(conv['id'])['messages'][-1]['content'],'')
     yield ('data: '+json.dumps({'choices':[{'delta':{'content':text}}]})+'\n').encode()
    yield b'data: [DONE]\n'
  class Opener:
   def open(self,*a,**k):return Response()
  self_test=self
  with patch.object(engine,'context',return_value=([{'role':'user','content':'Hello'}],[],128)),patch.object(companion.urllib.request,'build_opener',return_value=Opener()):
   result=engine.run(task)
  self.assertEqual(result['status'],'blocked')
  self.assertNotIn('forbidden',companion.overview(conv['id'])['messages'][-1]['content'])

class DistributionTests(unittest.TestCase):
 def test_manifest_has_no_missing_shards(self):
  rows=common.read_json(common.ROOT/'assets/catalog.json')['models']
  self.assertGreaterEqual(len(rows),30)
  self.assertTrue({'Kimi','GLM','DeepSeek'}<={r['family'] for r in rows})
  for row in rows:self.assertEqual(row['size'],sum(f['size'] for f in row['files']))
 def test_model_checksum_is_not_confused_with_local_hash(self):
  item={'id':'test','file':'m.gguf','size':4,'files':[{'name':'m.gguf','size':4,'sha256':'0'*64,'url':'https://example.org/m.gguf'}]}
  with tempfile.TemporaryDirectory() as d,patch.object(hub,'MODELS',Path(d)):
   dest=hub.paths(item)[0][0];dest.parent.mkdir();dest.with_suffix('.gguf.part').write_bytes(b'GGUF')
   with self.assertRaisesRegex(ValueError,'SHA-256'):hub.download(item)
   self.assertFalse(dest.exists())

if __name__=='__main__':unittest.main()
