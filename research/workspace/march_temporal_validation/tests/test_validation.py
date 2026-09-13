from __future__ import annotations
import ast, builtins, copy, importlib.abc, json, os, shutil, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import validation_workflow as w
import validation_plots as plots
import run_round07 as runner
from fixtures import build_fixture


def gate_data(a=-.001,b=-.002,discovery=10.):
    return pd.DataFrame([{'Gender':'W','Season':s,'recipe':'anchor_change','delta_vs_anchor':d}
                        for s,d in [(2016,a),(2018,b),(2017,discovery),(2019,discovery)]])


class Contracts(unittest.TestCase):
    def test_gate_pass(self):self.assertTrue(w.replication_gate(gate_data())['proceed_to_components'])
    def test_gate_excludes_discovery(self):self.assertEqual(w.replication_gate(gate_data(discovery=-10.)),w.replication_gate(gate_data()))
    def test_gate_one_season_worse(self):self.assertFalse(w.replication_gate(gate_data(.0001,-.01))['proceed_to_components'])
    def test_gate_zero_not_improvement(self):self.assertFalse(w.replication_gate(gate_data(0.,-.01))['proceed_to_components'])
    def test_gate_tiny_gains_insufficient(self):self.assertFalse(w.replication_gate(gate_data(-.0001,-.0001))['proceed_to_components'])
    def test_gate_nan_rejected(self):
        with self.assertRaises(ValueError):w.replication_gate(gate_data(float('nan'),-.1))
    def test_gate_duplicate_rejected(self):
        d=gate_data()
        with self.assertRaises(ValueError):w.replication_gate(pd.concat([d,d.iloc[:1]]))
    def test_gate_missing_season_rejected(self):
        with self.assertRaises(ValueError):w.replication_gate(gate_data().query('Season != 2018'))
    def test_controlled_drop_one(self):
        for columns in w.DROPS.values():
            self.assertEqual(columns[:len(w.ANCHOR)],w.ANCHOR)
            self.assertEqual(len(set(w.CHANGE)-set(columns)),1)
            self.assertEqual(len(columns),17)
    def test_frozen_parameters(self):
        self.assertEqual(w.CONFIG['feature_parameters'],w.ref.CONFIG['parameters'])
        self.assertEqual(w.RECIPES['anchor_change'],w.ref.RECIPES['anchor_change'])
    def test_no_validation_features_target_columns(self):
        self.assertFalse({'y','Season','DayNum','Team1ID','Team2ID'}&set(w.CONFIG['recipes']['anchor_change']))
    def test_budget_limits(self):
        for stage,n in [('prepare',181),('replicate',121),('components',181),('report',121)]:
            with self.assertRaises(ValueError):runner.run_stage(stage,max_seconds=n)
    def test_invalid_stage(self):
        with self.assertRaises(ValueError):runner.run_stage('train_everything')
    def test_notebook_no_styler(self):
        p=Path(w.__file__).parent/'07_womens_temporal_change_replication.ipynb'
        nb=json.loads(p.read_text());self.assertEqual(sum(c['cell_type']=='code' for c in nb['cells']),8)
        for c in nb['cells']:
            if c['cell_type']=='code':
                tree=ast.parse(''.join(c['source']))
                self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr=='style' for n in ast.walk(tree)))
    def test_no_rating_calls_in_workflow(self):
        tree=ast.parse(Path(w.__file__).read_text())
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('fit_early','build_snapshot') for n in ast.walk(tree)))
    def test_supervisor_timeout(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);shutil.copy2(Path(runner.__file__),root/'run_round07.py')
            (root/'validation_workflow.py').write_text('import time\ntime.sleep(8)\n')
            result=subprocess.run([sys.executable,str(root/'run_round07.py'),'replicate','--max-seconds','1'],capture_output=True,timeout=8)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(json.loads((root/'reports/failure.json').read_text())['status'],'TIME_LIMIT')
    def test_exclusive_lock(self):
        import fcntl
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);shutil.copy2(Path(runner.__file__),root/'run_round07.py');(root/'reports').mkdir()
            with (root/'reports/execution.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                r=subprocess.run([sys.executable,str(root/'run_round07.py'),'prepare'],capture_output=True,timeout=5)
                self.assertNotEqual(r.returncode,0);self.assertIn(b'Another stage',r.stderr)


class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=tempfile.TemporaryDirectory();cls.fixture=build_fixture(Path(cls.base.name)/'fixture')
    @classmethod
    def tearDownClass(cls):cls.base.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name)/'fixture'
        shutil.copytree(Path(self.base.name)/'fixture',root)
        self.args={k:root/Path(v).relative_to(Path(self.base.name)/'fixture') for k,v in self.fixture.items() if k!='head'}
        self.patch=patch.object(w.wf,'EXPECTED_SHA',self.fixture['head']);self.patch.start()
        self.ctx=w.preflight(**self.args)
    def tearDown(self):self.patch.stop();self.temp.cleanup()
    def test_preflight_no_mutation(self):w.preservation(self.ctx)
    def test_prepare_replays_six_no_training(self):
        with patch.object(w.wf,'fitted_model',side_effect=AssertionError('no fit')),patch.object(w.ff,'fit_early',side_effect=AssertionError('no rating')):
            w.prepare(self.ctx)
        self.assertEqual(w.read_json(self.ctx['directory']/'prepare.json')['prior_classifier_replays'],6)
    def test_two_new_fits_then_resume(self):
        w.prepare(self.ctx);w.replicate(self.ctx)
        self.assertEqual(w.read_json(self.ctx['directory']/'replication_receipt.json')['new_classifier_fits'],2)
        with patch.object(w.wf,'fitted_model',side_effect=AssertionError('no repeated fit')),patch.object(w.ff,'fit_early',side_effect=AssertionError('no rating')):
            w.replicate(self.ctx)
        r=w.read_json(self.ctx['directory']/'replication_receipt.json')
        self.assertEqual(r['new_classifier_fits'],0);self.assertEqual(r['upstream_classifier_replays'],6);self.assertEqual(r['local_checkpoint_reuses'],2)
    def test_missing_cache_stops(self):
        shutil.rmtree(self.ctx['temporal']/'snapshots/W_2015')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_corrupt_snapshot_stops(self):
        p=self.ctx['temporal']/'snapshots/W_2015/features.csv';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_changed_data_stops(self):
        p=self.ctx['raw']/'WNCAATourneyCompactResults.csv';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_changed_source_stops(self):
        p=self.args['kit']/'form_features.py';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_known_notebook_changes_preserved(self):
        before={p:w.sha(self.args['repo']/p) for p in w.wf.ALLOWED_DIRTY}
        w.prepare(self.ctx);w.replicate(self.ctx);w.preservation(self.ctx)
        self.assertEqual(before,{p:w.sha(self.args['repo']/p) for p in w.wf.ALLOWED_DIRTY})
    def test_extra_notebook_change_stops(self):
        p=self.args['repo']/next(iter(w.wf.ALLOWED_DIRTY));p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_bad_environment_stops(self):
        with patch.object(w.ref,'environment',return_value={}):
            with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_paths_traversal_and_symlink(self):
        with self.assertRaises(ValueError):w.safe_file(self.args['kit'],'../repo/.gitignore')
        p=self.args['kit']/'link';p.symlink_to(self.args['repo']/'.gitignore')
        with self.assertRaises(ValueError):w.safe_file(self.args['kit'],'link')
    def test_mirrored_feature_symmetry(self):
        _,_,x,x2=w.matrices(self.ctx)
        np.testing.assert_allclose(x[w.ANCHOR+w.CHANGE],-x2[w.ANCHOR+w.CHANGE],atol=1e-12)
    def test_future_tournament_outcome_not_feature(self):
        _,_,x,_=w.matrices(self.ctx)
        p=self.ctx['raw']/'WNCAATourneyCompactResults.csv';f=w.read_csv(p);extra=f.iloc[:1].copy();extra['Season']=2026
        w.atomic_csv(p,pd.concat([f,extra],ignore_index=True))
        _,_,x2,_=w.matrices(self.ctx)
        pd.testing.assert_frame_equal(x,x2)
    def test_split_earlier_seasons_only(self):
        _,_,x,_=w.matrices(self.ctx)
        for s in w.SEASONS:
            ti,vi=w.ref.split(x,s);self.assertTrue((x.iloc[ti].Season<s).all());self.assertTrue((x.iloc[vi].Season==s).all())
    def test_fit_budget_before_training(self):
        bundle=w.matrices(self.ctx)
        with patch.object(w.wf,'fitted_model',side_effect=AssertionError('must not fit')):
            with self.assertRaises(ValueError):w.obtain_fit(self.ctx,2016,'anchor_change',w.RECIPES['anchor_change'],bundle,0)
    def test_replication_output_tampering_stops(self):
        w.prepare(self.ctx);w.replicate(self.ctx);p=self.ctx['directory']/'gate.json';p.write_text('{}')
        with self.assertRaises(ValueError):w.components(self.ctx)
    def test_skipped_components_no_training(self):
        forced=w.replication_gate(gate_data(.01,.02))
        with patch.object(w,'replication_gate',return_value=forced):
            w.prepare(self.ctx);w.replicate(self.ctx)
            with patch.object(w.wf,'fitted_model',side_effect=AssertionError('no component fit')):w.components(self.ctx)
            self.assertEqual(w.read_json(self.ctx['directory']/'component_receipt.json')['status'],'SKIPPED_BY_GATE')
            w.report(self.ctx);self.assertEqual(len(plots.figures(self.ctx['directory'],self.ctx['kit']/'evidence')),10)
    def test_passed_gate_eight_components_and_resume(self):
        forced=w.replication_gate(gate_data())
        with patch.object(w,'replication_gate',return_value=forced):
            w.prepare(self.ctx);w.replicate(self.ctx);w.components(self.ctx)
            self.assertEqual(w.read_json(self.ctx['directory']/'component_receipt.json')['new_classifier_fits'],8)
            with patch.object(w.wf,'fitted_model',side_effect=AssertionError('no repeated fit')):w.components(self.ctx)
            r=w.read_json(self.ctx['directory']/'component_receipt.json');self.assertEqual(r['new_classifier_fits'],0);self.assertEqual(r['local_checkpoint_reuses'],8)
            w.report(self.ctx);self.assertEqual(len(plots.figures(self.ctx['directory'],self.ctx['kit']/'evidence')),12)
    def test_return_archive_excludes_private_files(self):
        w.prepare(self.ctx);w.replicate(self.ctx);w.components(self.ctx);w.report(self.ctx)
        z=self.ctx['kit']/'reports/milestone_07_return.zip'
        with zipfile.ZipFile(z) as archive:
            names=archive.namelist();self.assertIn('summary.json',names)
            self.assertFalse(any('predictions' in n or 'model.json' in n or 'late_residuals' in n or '.ipynb' in n for n in names))
    def test_plots_without_jinja(self):
        w.prepare(self.ctx);w.replicate(self.ctx);w.components(self.ctx)
        original=builtins.__import__
        def blocked(name,*args,**kwargs):
            if name.startswith('jinja2'):raise ImportError('Jinja2 deliberately blocked')
            return original(name,*args,**kwargs)
        with patch('builtins.__import__',side_effect=blocked):w.report(self.ctx)
        self.assertTrue((self.ctx['directory']/'temporal_validation.html').is_file())
    def test_stage_order_enforced(self):
        with self.assertRaises(ValueError):w.replicate(self.ctx)
        with self.assertRaises(ValueError):w.components(self.ctx)
    def test_corrupted_new_classifier_stops(self):
        w.prepare(self.ctx);w.replicate(self.ctx)
        p=self.ctx['directory']/'fits/W_2016_anchor_change/model.json';p.write_text('{}')
        with self.assertRaises(ValueError):w.replicate(self.ctx)

if __name__=='__main__':unittest.main()
