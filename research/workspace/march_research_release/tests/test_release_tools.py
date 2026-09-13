"""User-run, temporary-file tests for publication and packaging; no account access."""
from pathlib import Path
import json,tempfile,unittest,zipfile,hashlib,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import collect_reports as c
import repair_notebook17 as r
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'publication'))
import stage_private as p
class ReleaseTools(unittest.TestCase):
 def test_empty_collection_explicitly_partial(self):
  with tempfile.TemporaryDirectory() as d:
   # Existing user round17 is not examined in this fixture: use injected collector home.
   path,status=c.collect(Path(d),home=Path(d)/'home')
   self.assertEqual(status['complete'],[]);self.assertEqual(status['missing'],['16','17','18','19'])
 def test_collector_rejects_corrupted_member(self):
  with tempfile.TemporaryDirectory() as d:
   z=Path(d)/'a.zip'
   with zipfile.ZipFile(z,'w') as f:
    f.writestr('m.json','{}');f.writestr('return_integrity.json',json.dumps({'sha256':{'m.json':'0'*64}}))
   with self.assertRaises(ValueError):c.verify(z)
 def test_collector_accepts_verified_archive(self):
  with tempfile.TemporaryDirectory() as d:
   z=Path(d)/'a.zip';b=b'{}'
   with zipfile.ZipFile(z,'w') as f:
    f.writestr('m.json',b);f.writestr('return_integrity.json',json.dumps({'sha256':{'m.json':hashlib.sha256(b).hexdigest()}}))
   self.assertEqual(c.verify(z),hashlib.sha256(z.read_bytes()).hexdigest())
 def test_notebook_packaging_only(self):
  with tempfile.TemporaryDirectory() as d:
   kit=Path(d)/'march_feature_rounds_16_17';kit.mkdir();f=kit/'17_blocks_and_foul_pressure.ipynb'
   science={'cell_type':'code','source':['print(1)'],'outputs':[{'output_type':'stream','name':'stdout','text':['1']}],'execution_count':1}
   n={'cells':[science,{'cell_type':'code','source':r.OLD.splitlines(True),'execution_count':2,'outputs':[{'output_type':'error','ename':'FileNotFoundError','evalue':'Missing 16','traceback':[]}]}]}
   raw=json.dumps(n).encode();f.write_bytes(raw);result=r.update(d)
   self.assertEqual(result['models_fitted'],0);self.assertEqual(json.loads(f.read_text())['cells'][0],science)
   self.assertEqual(r.update(d)['status'],'ALREADY_UPDATED')
   self.assertEqual(next((kit/'reports/notebook_backups').rglob('*.ipynb')).read_bytes(),raw)
 def test_notebook_edits_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   k=Path(d)/'march_feature_rounds_16_17';k.mkdir();f=k/'17_blocks_and_foul_pressure.ipynb';f.write_text('{"cells":[]}')
   before=f.read_bytes()
   with self.assertRaises(ValueError):r.update(d)
   self.assertEqual(before,f.read_bytes())
 def test_private_stage_preserves_original_outputs(self):
  with tempfile.TemporaryDirectory() as d:
   home=Path(d);k=home/'march_shooting_research';k.mkdir();f=k/'example.ipynb'
   n={'cells':[{'cell_type':'code','source':['x=1'],'outputs':[{'output_type':'stream','name':'stdout','text':['private output']}],'execution_count':2}]}
   f.write_text(json.dumps(n));b=f.read_bytes();dest=p.stage(home,home/'snapshot')
   copied=json.loads((dest/'research/march_shooting_research/example.ipynb').read_text())
   self.assertEqual(copied['cells'][0]['outputs'],[]);self.assertEqual(f.read_bytes(),b)
 def test_private_stage_blocks_secrets(self):
  with tempfile.TemporaryDirectory() as d:
   home=Path(d);k=home/'march_shooting_research';k.mkdir();(k/'s.py').write_text('credential="'+'AKIA'+'Z'*16+'"')
   with self.assertRaises(SystemExit):p.stage(home,home/'snapshot')
 def test_private_stage_refuses_source_destination(self):
  with tempfile.TemporaryDirectory() as d:
   home=Path(d)
   with self.assertRaises(ValueError):p.stage(home,home/'march_shooting_research/snapshot')
if __name__=='__main__':unittest.main()
