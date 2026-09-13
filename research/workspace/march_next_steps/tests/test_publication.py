"""User-run tests of local publication safeguards; never contacts GitHub."""
import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import github_publish as g
from publication import stage_private as s

class PublicationTests(unittest.TestCase):
    def test_targets_separated(self):
        self.assertEqual(g.TARGETS['private'],('march-mania-research',True));self.assertEqual(g.TARGETS['public'],('march-mania-portfolio',False))
    def test_public_refuses_private_file(self):
        with self.assertRaises(ValueError):g.public_publish_allowed('public',{'feature_rounds.py':'x'})
    def test_public_accepts_only_allowlist(self):g.public_publish_allowed('public',{x:'x' for x in g.PUBLIC_FILES})
    def test_public_no_training_script(self):self.assertNotIn('feature_rounds.py',g.PUBLIC_FILES)
    def test_plan_missing_refused(self):
        with tempfile.TemporaryDirectory() as d,patch.object(g.Path,'home',return_value=Path(d)):
            with self.assertRaises(ValueError):g.load_plan()
    def test_nested_snapshot_refused(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);(home/s.ROOTS[0]).mkdir()
            with self.assertRaises(ValueError):s.stage(home,home/s.ROOTS[0]/'snapshot')
    def test_existing_destination_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):s.stage(d,d)
    def test_snapshot_strips_outputs_and_keeps_original(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);root=home/s.ROOTS[0];root.mkdir();nb={'cells':[{'cell_type':'code','source':['x=1'],'outputs':[{'text':'private'}],'execution_count':9}], 'metadata':{},'nbformat':4,'nbformat_minor':5}
            (root/'a.ipynb').write_text(json.dumps(nb));old=(root/'a.ipynb').read_bytes()
            out=s.stage(home,home/'publication_copy');saved=json.loads((out/'research'/s.ROOTS[0]/'a.ipynb').read_text())
            self.assertEqual(saved['cells'][0]['outputs'],[]);self.assertEqual((root/'a.ipynb').read_bytes(),old)
    def test_snapshot_excludes_private_models(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);root=home/s.ROOTS[0];(root/'private_runs').mkdir(parents=True);(root/'private_runs/model.json').write_text('{}');(root/'main.py').write_text('x=1\n')
            out=s.stage(home,home/'publication_copy');self.assertFalse((out/'research'/s.ROOTS[0]/'private_runs').exists())
    def test_secret_like_file_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d);root=home/s.ROOTS[0];root.mkdir();(root/'config.py').write_text('value="'+('ghp_'+'A'*36)+'"')
            out=s.stage(home,home/'publication_copy');record=json.loads((out/'PRIVATE_SNAPSHOT.json').read_text());self.assertEqual(record['status'],'REVIEW_BLOCKED');self.assertEqual(len(record['blocked']),1)
    def test_auth_missing_cli_no_network(self):
        with tempfile.TemporaryDirectory() as d,patch.object(g.Path,'home',return_value=Path(d)),patch.object(g.shutil,'which',return_value=None):
            with self.assertRaises(ValueError):g.auth()
    def test_wrong_account_refused(self):
        fake=type('Result',(),{'returncode':0})()
        with patch.dict(g.os.environ,{'GH_TOKEN':'','GITHUB_TOKEN':''}),patch.object(g.shutil,'which',return_value='/tmp/gh'),patch.object(g,'command',return_value=fake),patch.object(g,'gh_json',return_value={'login':'other'}):
            with self.assertRaises(ValueError):g.auth()
    def test_authenticated_correct_account_skip_login(self):
        fake=type('Result',(),{'returncode':0})()
        with patch.dict(g.os.environ,{'GH_TOKEN':'','GITHUB_TOKEN':''}),patch.object(g.shutil,'which',return_value='/tmp/gh'),patch.object(g,'command',return_value=fake),patch.object(g,'gh_json',return_value={'login':g.OWNER}),patch.object(g.subprocess,'run',side_effect=AssertionError('Should not log in again')):g.auth()
    def test_atomic_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'target').write_text('keep');(p/'link.json').symlink_to(p/'target')
            with self.assertRaises(ValueError):g.atomic(p/'link.json',{})
            self.assertEqual((p/'target').read_text(),'keep')
    def test_public_manifest_pinned(self):
        pins=json.loads((g.ROOT/'PUBLIC_MANIFEST.json').read_text())['sha256'];self.assertEqual(set(pins),set(g.PUBLIC_FILES))
        for n,h in pins.items():self.assertEqual(g.digest(g.ROOT/'public_portfolio'/n),h)
if __name__=='__main__':unittest.main()
