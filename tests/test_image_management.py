import contextlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import imaging
import image_hub
import resources
from common import write_json

class GalleryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.gallery=self.root/'gallery';self.gallery.mkdir()
  self.patches=[patch.object(imaging,'GALLERY',self.gallery),patch.object(imaging,'STATE',self.root),patch.object(imaging,'named_lock',side_effect=lambda _:contextlib.nullcontext())]
  for p in self.patches:p.start()
  self.name='a'*32+'.png';(self.gallery/self.name).write_bytes(b'PNG fixture')
  write_json(self.root/'gallery.json',[{'file':self.name,'prompt':'test','created':1,'model':'test-model'}])
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def test_remove_and_restore_preserve_bytes_and_metadata(self):
  imaging.gallery_remove(self.name)
  self.assertFalse((self.gallery/self.name).exists());self.assertEqual(imaging.read_json(self.root/'gallery.json'),[])
  self.assertEqual(imaging.gallery_trash()[0]['model'],'test-model')
  imaging.gallery_restore(self.name)
  self.assertEqual((self.gallery/self.name).read_bytes(),b'PNG fixture');self.assertEqual(imaging.gallery_trash(),[])
  self.assertEqual(imaging.read_json(self.root/'gallery.json')[0]['model'],'test-model')
 def test_path_traversal_and_unknown_files_are_rejected(self):
  for value in ['../private.png','a.png',None,'b'*32+'.png']:
   with self.assertRaises(ValueError):imaging.gallery_remove(value)
  self.assertTrue((self.gallery/self.name).exists())
 def test_remove_does_not_follow_a_symlink(self):
  if not hasattr(__import__('os'),'symlink'):return
  path=self.gallery/self.name;path.unlink();outside=self.root/'outside';outside.write_text('keep')
  try:path.symlink_to(outside)
  except OSError:self.skipTest('Symlinks unavailable')
  with self.assertRaises(ValueError):imaging.gallery_remove(self.name)
  self.assertEqual(outside.read_text(),'keep')

class ImageHubTests(unittest.TestCase):
 def test_search_does_not_offer_encoders_or_lora_as_generators(self):
  rows=[{'id':'author/Image-Uncensored','pipeline_tag':'text-to-image'},{'id':'author/Text-Uncensored','pipeline_tag':'text-to-image','tags':['text-encoder']},{'id':'author/LoRA','pipeline_tag':'text-to-image','tags':['lora']},{'id':'author/Chat','pipeline_tag':'text-generation'}]
  with patch.object(image_hub.hub,'get_json',return_value=rows):result=image_hub.search('uncensored',True)
  self.assertEqual([r['repo'] for r in result],['author/Image-Uncensored'])
 def test_inspect_rejects_a_text_encoder_even_if_pipeline_claims_image_generation(self):
  with patch.object(image_hub.hub,'get_json',return_value={'pipeline_tag':'text-to-image','tags':['text-encoder']}):
   with self.assertRaises(ValueError):image_hub.inspect('author/encoder')
 def test_inspect_keeps_main_weights_and_pins_revision(self):
  data={'sha':'a'*40,'pipeline_tag':'text-to-image','cardData':{'base_model':'Qwen/Qwen-Image-2.1'},'siblings':[{'rfilename':'image-Q4.gguf','size':100,'lfs':{'sha256':'1'*64}},{'rfilename':'mmproj.gguf','size':30},{'rfilename':'vae/v.safetensors','size':40},{'rfilename':'x-00001-of-00002.gguf','size':50}]}
  with patch.object(image_hub.hub,'get_json',return_value=data):d=image_hub.inspect('author/My-Image-Uncensored')
  self.assertEqual(d['revision'],'a'*40);self.assertEqual(len(d['files']),1);self.assertEqual(d['files'][0]['recipe'],'qwen-image-21');self.assertTrue(d['uncensored'])
 def test_turbo_and_base_recipe_are_distinguished(self):
  self.assertEqual(image_hub.infer_recipe('Qwen-Image-2.1-Turbo'),'qwen-image-21-turbo')
  self.assertEqual(image_hub.infer_recipe('Qwen-Image-2.1'),'qwen-image-21')
 def test_download_only_does_not_start_or_switch_models(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);file={'file':'m.gguf','name':'m.gguf','size':4,'sha256':None,'recipe':'qwen-image-21'}
   info={'repo':'a/b','revision':'a'*40,'source':'https://huggingface.co/a/b','files':[file],'uncensored':True}
   with patch.object(image_hub,'inspect',return_value=info),patch.object(image_hub,'CONFIG',root),patch.object(image_hub,'named_lock',side_effect=lambda _:contextlib.nullcontext()),patch.object(imaging,'MODEL_DIR',root/'models'),patch.object(imaging,'download') as download,patch.object(imaging,'use_library') as use:
    result=image_hub.install({'repo':'a/b','file':'m.gguf'})
   use.assert_not_called();download.assert_called_once();self.assertTrue(result['id'].startswith('hf-image-'));self.assertTrue((root/'image-library.json').exists())

class ResourceTests(unittest.TestCase):
 def test_live_identity_and_process_memory_come_from_engine_not_selected_model(self):
  def text(path,**kwargs):return {'data':[{'id':'really-loaded'}]}
  with patch.object(resources.hardware,'command',return_value='42, 1024\n43, 2048'),patch.object(resources.runtime,'api',side_effect=text),patch.object(resources.imaging,'api',return_value={'state':'ready','models':{'diffusion_model':'diffusion_models/actual.gguf'},'recipe':'qwen-image-21'}),patch.object(resources,'process_port',side_effect=lambda pid,exe,*args:pid==(42 if exe=='llama-server' else 43)):
   d=resources.snapshot(refresh=True)
  self.assertEqual(d['text']['name'],'really-loaded');self.assertEqual(d['text']['vram_mib'],1024);self.assertEqual(d['image']['name'],'actual.gguf');self.assertEqual(d['image']['vram_mib'],2048);self.assertEqual(d['active'],['text','image'])
 def test_offline_engine_has_no_stale_selected_name(self):
  with patch.object(resources.hardware,'command',return_value=''),patch.object(resources.runtime,'api',side_effect=OSError()),patch.object(resources.imaging,'api',side_effect=OSError()),patch.object(resources,'process_port',return_value=False):
   d=resources.snapshot(refresh=True)
  self.assertEqual(d['active'],[]);self.assertIsNone(d['image']['name']);self.assertIsNone(d['text']['vram_mib'])


class EngineWorkflowTests(unittest.TestCase):
 def test_generation_reloads_last_image_model_after_using_text_chat(self):
  selected={'recipe':'qwen-image-21','models':{'diffusion_model':'main','llm':'enc','vae':'vae'}}
  calls=[]
  def api(path,payload=None,**kwargs):
   calls.append((path,payload))
   return {'state':'empty'} if path.endswith('/status') else {'state':'ready'}
  with patch.object(imaging,'read_json',return_value=selected),patch.object(imaging,'api',side_effect=api),patch.object(imaging,'start') as start:
   imaging.ensure_generation_model()
  start.assert_called_once();self.assertEqual(calls[-1][1],selected)
 def test_generation_without_any_selected_image_model_gives_useful_message(self):
  with patch.object(imaging,'read_json',return_value={}),patch.object(imaging,'api',side_effect=OSError()),patch.object(imaging,'start') as start:
   with self.assertRaisesRegex(ValueError,'Мои модели'):imaging.ensure_generation_model()
  start.assert_not_called()
 def test_preset_download_does_not_switch_or_start_either_engine(self):
  entry={'id':'example','components':[{'file':'model.gguf'}],'recipe':'unknown','fits_disk':True}
  with patch.object(imaging,'library',return_value=[entry]),patch.object(imaging,'read_json',return_value={'recipes':{}}),patch.object(imaging,'component_path',return_value=None),patch.object(imaging,'download') as download,patch.object(imaging,'start') as start:
   imaging.download_preset('example')
  download.assert_called_once();start.assert_not_called()

if __name__=='__main__':unittest.main()
