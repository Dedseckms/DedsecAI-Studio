import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import imaging

class ImageLibraryTests(unittest.TestCase):
 def test_catalog_has_complete_single_file_presets_and_checksums(self):
  rows=imaging.read_json(imaging.ROOT/'assets/image-catalog.json')['models']
  self.assertTrue({'sd-turbo','sd15','sdxl-turbo'}<={r['id'] for r in rows})
  self.assertGreaterEqual(sum(bool(r.get('uncensored')) for r in rows),4)
  for row in rows:
   self.assertIn(row['components'][0]['slot'],{'model','diffusion_model'})
   self.assertEqual(len(row['components'][0]['sha256']),64)
   self.assertIn('/resolve/',row['components'][0]['url'])
 def test_own_files_and_recipe_are_found_without_link_entry(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);models=root/'models';p=models/'checkpoints'/'my-sdxl-model.safetensors';p.parent.mkdir(parents=True);p.write_bytes(b'model')
   with patch.object(imaging,'MODEL_DIR',models),patch.object(imaging,'CONFIG',root),patch('manager.raw_catalog',return_value=[]):
    rows=imaging.library();own=next(r for r in rows if r.get('path')==str(p))
   self.assertEqual(own['recipe'],'sdxl-checkpoint');self.assertTrue(own['installed'])
 def test_custom_checkpoint_recipe_uses_metadata_when_filename_is_arbitrary(self):
  import json,struct
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'my-favourite.safetensors';header=json.dumps({'cond_stage_model.transformer.text_model.embeddings.token_embedding.weight':{'shape':[49408,768]}}).encode();path.write_bytes(struct.pack('<Q',len(header))+header)
   self.assertEqual(imaging.guess_recipe(path),'sd1-checkpoint')
 def test_unsupported_file_is_not_imported(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'script.py';path.write_text('x')
   with self.assertRaises(ValueError):imaging.import_model(str(path))
 def test_one_click_supplies_recipe_and_opaque_file_id(self):
  entry={'id':'sd-turbo','recipe':'sd-turbo','fits_disk':True,'components':[{'slot':'model','category':'checkpoints','file':'m.gguf','url':'https://example.org/m.gguf'}]}
  def fake_api(path,*args,**kwargs):
   if path.endswith('/recipes'):return {'recipes':[{'id':'sd-turbo','slots':[]}]}
   if path.endswith('/model-files'):return {'files':[{'id':'opaque-actual-id','relative_path':'checkpoints/m.gguf'}]}
   return {}
  with tempfile.TemporaryDirectory() as d,patch.object(imaging,'CONFIG',Path(d)),patch.object(imaging,'library',return_value=[entry]),patch.object(imaging,'download') as download,patch.object(imaging,'binary',return_value='server'),patch.object(imaging,'start') as start,patch.object(imaging,'api',side_effect=fake_api),patch.object(imaging,'run',return_value={'message':'ready'}) as run:
   result=imaging.use_library('sd-turbo')
   run.assert_called_once_with('image_load',{'recipe':'sd-turbo','models':{'model':'opaque-actual-id'}})
   self.assertEqual(result['message'],'ready');download.assert_called_once();start.assert_called_once()
 def test_wrong_file_collision_does_not_silently_use_other_model(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'sd-turbo.gguf';p.write_bytes(b'one');dest=root/'models/checkpoints/sd-turbo.gguf';dest.parent.mkdir(parents=True);dest.write_bytes(b'two')
   entry={'id':'mine','recipe':'sd-turbo','fits_disk':True,'path':str(p)}
   with patch.object(imaging,'library',return_value=[entry]),patch.object(imaging,'MODEL_DIR',root/'models'):
    with self.assertRaises(ValueError):imaging.use_library('mine')


class DependencyTests(unittest.TestCase):
 def recipe(self):
  return {'id':'qwen-image-21','slots':[{'id':'diffusion_model','required':True},{'id':'llm','required':True,'label':'Encoder'},{'id':'vae','required':False},{'id':'tae','required':False}], 'required_any':[['vae','tae']]}
 def test_decoder_alternative_is_required_even_when_slots_are_optional(self):
  missing=imaging.missing_components(self.recipe(),{'diffusion_model':'main','llm':'encoder'})
  self.assertEqual(missing,['vae / tae'])
  self.assertEqual(imaging.missing_components(self.recipe(),{'diffusion_model':'main','llm':'encoder','tae':'tiny'}),[])
 def test_encoder_and_vae_download_and_use_runtime_ids(self):
  components=[{'slot':'llm','category':'text_encoders','file':'encoder.gguf','size':4},{'slot':'vae','category':'vae','file':'decoder.safetensors','size':4}]
  files=[]
  def downloaded(component):
   relative=component['category']+'/'+component['file'];files.append({'id':'opaque-'+component['slot'],'relative_path':relative})
  with patch.object(imaging,'read_json',return_value={'recipes':{'qwen-image-21':components}}),patch.object(imaging,'download',side_effect=downloaded) as download,patch.object(imaging,'api',side_effect=lambda path,*a,**k: {'files':files} if path.endswith('/model-files') else {}):
   result=imaging.resolve_components(self.recipe(),{'diffusion_model':'main'},[])
  self.assertEqual(result,{'diffusion_model':'main','llm':'opaque-llm','vae':'opaque-vae'});self.assertEqual(download.call_count,2)
 def test_selected_tiny_decoder_does_not_trigger_full_vae_download(self):
  components=[{'slot':'vae','category':'vae','file':'decoder.safetensors','size':4}]
  with patch.object(imaging,'read_json',return_value={'recipes':{'qwen-image-21':components}}),patch.object(imaging,'download') as download:
   result=imaging.resolve_components(self.recipe(),{'diffusion_model':'main','llm':'enc','tae':'already-selected'},[])
  download.assert_not_called();self.assertEqual(result['tae'],'already-selected')
 def test_other_architecture_never_uses_qwen21_components(self):
  with patch.object(imaging,'read_json',return_value={'recipes':{'qwen-image-21':[]}}),patch.object(imaging,'download') as download:
   result=imaging.resolve_components({'id':'qwen-image','slots':[]},{'diffusion_model':'main'},[])
  download.assert_not_called();self.assertEqual(result,{'diffusion_model':'main'})
 def test_advanced_load_also_resolves_dependencies(self):
  recipe=self.recipe();resolved={'diffusion_model':'main','llm':'encoder','vae':'decoder'};payloads=[]
  def fake_api(path,payload=None,**kwargs):
   if path.endswith('/recipes'):return {'recipes':[recipe]}
   if path.endswith('/model-files'):return {'files':[]}
   if path.endswith('/models/load'):payloads.append(payload);return {'state':'ready'}
   return {}
  with patch.object(imaging,'read_json',return_value={'recipes':{'qwen-image-21':[]}}),patch.object(imaging,'api',side_effect=fake_api),patch.object(imaging,'resolve_components',return_value=resolved),patch.object(imaging,'generate',return_value={'seconds':1}):
   imaging.run('image_load',{'recipe':'qwen-image-21','models':{'diffusion_model':'main'}})
  self.assertEqual(payloads[0]['models'],resolved)
 def test_complete_partial_download_can_finish_without_another_http_request(self):
  import hashlib
  with tempfile.TemporaryDirectory() as d,patch.object(imaging,'MODEL_DIR',Path(d)),patch.object(imaging,'api',side_effect=OSError('offline')),patch('hub.HTTP.open') as open_http:
   p=Path(d)/'text_encoders/encoder.gguf.part';p.parent.mkdir();p.write_bytes(b'GGUF')
   imaging.download({'url':'https://example.org/encoder.gguf','category':'text_encoders','size':4,'sha256':hashlib.sha256(b'GGUF').hexdigest()})
   self.assertEqual(p.with_suffix('').read_bytes(),b'GGUF');open_http.assert_not_called()

if __name__=='__main__':unittest.main()
