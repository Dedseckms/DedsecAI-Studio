import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import imaging

class ImageLibraryTests(unittest.TestCase):
 def test_catalog_has_complete_single_file_presets_and_checksums(self):
  rows=imaging.read_json(imaging.ROOT/'assets/image-catalog.json')['models']
  self.assertEqual({r['id'] for r in rows},{'sd-turbo','sd15','sdxl-turbo'})
  for row in rows:
   self.assertEqual(row['components'][0]['slot'],'model')
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

if __name__=='__main__':unittest.main()
