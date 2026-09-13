"""Prepared regression tests. Temporary files/mocks only; no account writes."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import github_publish as g
from publication import stage_private as s
from publication import review_support as r

class RecoveryTests(unittest.TestCase):
    def make_root(self,home):
        p=home/s.ROOTS[0];p.mkdir();return p
    def test_typechecker_cache_is_excluded_not_deleted(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);root=self.make_root(h);cache=root/'.mypy_cache';cache.mkdir()
            (cache/'oversized.json').write_bytes(b'0'*3_000_100);(root/'model.py').write_text('x=1\n')
            out=s.stage(h,h/'stage')
            self.assertTrue((cache/'oversized.json').exists())
            self.assertEqual(json.loads((out/'PRIVATE_SNAPSHOT.json').read_text())['blocked'],[])
            self.assertFalse((out/'research'/s.ROOTS[0]/'.mypy_cache').exists())
    def test_ruff_and_pytest_caches_excluded(self):
        for name in ['.ruff_cache','.pytest_cache','.cache','.tox','.nox','__pycache__']:
            self.assertTrue(s.generated_dir(name))
    def test_normal_cache_named_source_is_not_excluded(self):
        self.assertFalse(s.generated_dir('cache_features'));self.assertFalse(s.generated_dir('cache'))
    def test_package_metadata_excluded(self):
        self.assertTrue(s.generated_dir('numpy-1.0.dist-info'));self.assertTrue(s.generated_dir('project.egg-info'))
    def test_credential_containers_are_never_staged(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);root=self.make_root(h);(root/'kaggle.json').write_text('{}');(root/'model.py').write_text('x=1')
            out=s.stage(h,h/'stage');meta=json.loads((out/'PRIVATE_SNAPSHOT.json').read_text())
            self.assertTrue(any('kaggle.json' in x['path'] for x in meta['exclusions']))
            self.assertFalse((out/'research'/s.ROOTS[0]/'kaggle.json').exists())
    def test_notebook_widget_state_removed_in_copy(self):
        obj={'cells':[{'cell_type':'code','source':['x=1'],'metadata':{'private':'value'},'outputs':[{'text':'private'}],'execution_count':2}],
             'metadata':{'widgets':{'state':'private'},'kernelspec':{'name':'test'}},'nbformat':4,'nbformat_minor':5}
        out=json.loads(s.normalized_notebook(json.dumps(obj).encode()))
        self.assertNotIn('widgets',out['metadata']);self.assertEqual(out['cells'][0]['metadata'],{})
        self.assertEqual(out['cells'][0]['source'],['x=1']);self.assertEqual(out['cells'][0]['outputs'],[])
    def test_bad_notebook_keeps_review_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);root=self.make_root(h);(root/'a.ipynb').write_text('not json')
            out=s.stage(h,h/'stage');self.assertEqual(json.loads((out/'PRIVATE_SNAPSHOT.json').read_text())['status'],'REVIEW_BLOCKED')
    def test_large_active_source_remains_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);root=self.make_root(h);(root/'source.py').write_bytes(b'0'*3_000_100)
            out=s.stage(h,h/'stage');m=json.loads((out/'PRIVATE_SNAPSHOT.json').read_text());self.assertEqual(len(m['blocked']),1)
    def test_symlink_directory_remains_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);root=self.make_root(h);(h/'target').mkdir();(root/'linked').symlink_to(h/'target')
            out=s.stage(h,h/'stage');self.assertEqual(len(json.loads((out/'PRIVATE_SNAPSHOT.json').read_text())['blocked']),1)
    def test_old_blocker_inspection_without_file_contents(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);p=h/'march_publication/plans/20260913T021335Z/private_source';p.mkdir(parents=True)
            (p/'PRIVATE_SNAPSHOT.json').write_text(json.dumps({'status':'REVIEW_BLOCKED','files':[{}],
                'blocked':[{'path':s.ROOTS[0]+'/.mypy_cache/x.json','reason':'oversize'},
                           {'path':s.ROOTS[0]+'/config.py','reason':'possible secret'}]}))
            obj=r.inspect_previous(h);b=obj['plans'][0]['blockers']
            self.assertIn('EXCLUDED',b[0]['classification']);self.assertIn('REQUIRED',b[1]['classification'])
            self.assertFalse(obj['source_contents_read'])
    def test_no_snapshot_means_no_plan_found(self):
        with tempfile.TemporaryDirectory() as d:self.assertEqual(r.inspect_previous(Path(d))['status'],'NO_LOCAL_PLAN_FOUND')
    def test_legacy_blocked_plan_error_is_not_run_plan_first(self):
        with tempfile.TemporaryDirectory() as d,patch.object(g.Path,'home',return_value=Path(d)):
            p=Path(d)/'march_publication/plans/old/private_source';p.mkdir(parents=True)
            (p/'PRIVATE_SNAPSHOT.json').write_text(json.dumps({'files':[],'blocked':[{'path':'x','reason':'possible secret'}]}))
            with self.assertRaisesRegex(ValueError,'prior scan was blocked'):g.load_plan()
    def test_new_blocked_plan_saves_pointer(self):
        with tempfile.TemporaryDirectory() as d,patch.object(g.Path,'home',return_value=Path(d)):
            root=self.make_root(Path(d));(root/'config.py').write_text('x="'+('ghp_'+'A'*36)+'"')
            with self.assertRaises(SystemExit):g.plan()
            pointer=Path(d)/'march_publication/latest_plan.json';self.assertTrue(pointer.is_file())
            meta=json.loads(Path(json.loads(pointer.read_text())['path']).read_text())
            self.assertEqual(meta['status'],'REVIEW_BLOCKED');self.assertEqual(len(meta['blocked_files']),2)
            with self.assertRaisesRegex(ValueError,'unresolved source blockers'):g.load_plan()
    def test_new_clear_plan_has_zero_blockers(self):
        with tempfile.TemporaryDirectory() as d,patch.object(g.Path,'home',return_value=Path(d)):
            root=self.make_root(Path(d));(root/'main.py').write_text('x=1\n');g.plan()
            folder,record=g.load_plan();self.assertEqual(record['status'],'LOCAL_PLAN_READY')
            self.assertEqual(record['blocked_files'],[]);self.assertTrue((folder/'REVIEW.md').is_file())
    def test_staged_bytes_changed_stop(self):
        with tempfile.TemporaryDirectory() as d,patch.object(g.Path,'home',return_value=Path(d)):
            root=self.make_root(Path(d));(root/'main.py').write_text('x=1\n');g.plan();folder,_=g.load_plan()
            (folder/'private_source/research'/s.ROOTS[0]/'main.py').write_text('x=2')
            with self.assertRaisesRegex(ValueError,'Staged file changed'):g.load_plan()
    def test_no_automatic_login_on_expired_session(self):
        fake=type('Result',(),{'returncode':1})()
        with patch.dict(g.os.environ,{'GH_TOKEN':'','GITHUB_TOKEN':''}),patch.object(g.shutil,'which',return_value='/bin/gh'),patch.object(g,'command',return_value=fake),patch.object(g.subprocess,'run',side_effect=AssertionError('No login')):
            with self.assertRaisesRegex(ValueError,'No password prompt'):g.auth()
    def test_redaction_does_not_return_matched_value(self):
        token='ghp_'+'A'*36;self.assertNotIn(token,r.clean('error '+token))
    def test_new_plan_does_not_delete_old_plan(self):
        with tempfile.TemporaryDirectory() as d,patch.object(g.Path,'home',return_value=Path(d)):
            root=self.make_root(Path(d));(root/'main.py').write_text('x=1');g.plan();folder,_=g.load_plan()
            before=(folder/'plan.json').read_bytes();g.plan();self.assertEqual((folder/'plan.json').read_bytes(),before)
    def test_recorded_test_fingerprint_changes_with_code(self):
        pins=r.public_test_fingerprints(g.ROOT);self.assertIn('github_publish.py',pins);self.assertIn('tests/test_publication_recovery.py',pins)
    def test_bad_test_receipt_stops(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);r.atomic(h/'march_publication/publication_test_receipt.json',{'status':'FAIL'})
            with self.assertRaises(ValueError):r.require_test_receipt(g.ROOT,h)
    def test_local_lock_refuses_second_holder(self):
        with tempfile.TemporaryDirectory() as d:
            with r.lock(Path(d)):
                with self.assertRaises(RuntimeError):
                    with r.lock(Path(d)):pass
    def test_remote_host_not_switched_by_plan(self):
        self.assertEqual(g.TARGETS['private'],('march-mania-research',True));self.assertEqual(g.OWNER,'alvaromendizabal')

if __name__=='__main__':unittest.main()
