import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import record_workflow as r
from pipeline_fixture import build_fixture
from fixtures import data


class GateTests(unittest.TestCase):
    def metrics(self,d=(-.001,-.002,-.001),discovery=-.0014):
        return pd.DataFrame({'Season':[2016,2017,2018,2019],'recipe':['anchor_record']*4,
                             'delta_vs_anchor':[d[0],d[1],discovery,d[2]]})
    def test_unchanged_four_record_columns(self):
        self.assertEqual(len(r.RECORD),4)
        self.assertEqual(len(r.BASE_RECIPES['anchor_record']),20)
    def test_no_quality_columns_in_any_recipe(self):
        for cols in r.CONFIG['recipes'].values():self.assertFalse(set(cols)&set(r.sf.QUALITY_COLS))
    def test_drop_one_keeps_every_anchor(self):
        for cols in r.DROP_RECIPES.values():
            self.assertEqual(len(cols),19);self.assertTrue(set(r.ANCHOR)<=set(cols))
            self.assertEqual(len(set(r.RECORD)-set(cols)),1)
    def test_replication_pass(self):
        self.assertTrue(r.replication_gate(self.metrics())['proceed_to_ablation'])
    def test_discovery_cannot_rescue_failure(self):
        self.assertFalse(r.replication_gate(self.metrics((.01,.01,.01),-1))['proceed_to_ablation'])
    def test_discovery_cannot_fail_replication(self):
        self.assertTrue(r.replication_gate(self.metrics(discovery=1))['proceed_to_ablation'])
    def test_two_of_three_required(self):
        self.assertFalse(r.replication_gate(self.metrics((-.01,.0001,.0001)))['proceed_to_ablation'])
    def test_worst_year_guard(self):
        self.assertFalse(r.replication_gate(self.metrics((-.01,-.01,.004)))['proceed_to_ablation'])
    def test_mean_gain_guard(self):
        self.assertFalse(r.replication_gate(self.metrics((-.00001,-.00001,-.00001)))['proceed_to_ablation'])
    def test_missing_replication_year_rejected(self):
        with self.assertRaises(ValueError):r.replication_gate(self.metrics().iloc[:3])
    def test_nonfinite_gate_rejected(self):
        with self.assertRaises(ValueError):r.replication_gate(self.metrics((float('nan'),0,0)))
    def test_duplicate_year_rejected(self):
        m=self.metrics();m.loc[m.Season==2019,'Season']=2017
        with self.assertRaises(ValueError):r.replication_gate(m)
    def test_future_validation_forbidden(self):
        with self.assertRaises(ValueError):r.temporal_split(pd.DataFrame({'Season':[2013,2014,2015,2026]}),2026)
    def test_frozen_model_training_scale(self):
        m=r.wf.fitted_model(pd.DataFrame({'a':[-2.,-1.,1.,2.]}),np.array([0,0,1,1]),['a'])
        self.assertAlmostEqual(m['scales'][0],np.sqrt(2.5))
    def test_complementary_probability(self):
        x=pd.DataFrame({'a':[-2.,-1.,1.,2.]});m=r.wf.fitted_model(x,np.array([0,0,1,1]),['a'])
        np.testing.assert_allclose(r.wf.predict(m,x)+r.wf.predict(m,-x),1,atol=1e-14)
    def test_no_style_access_in_delivered_notebook(self):
        n=json.loads((ROOT/'05_womens_record_replication.ipynb').read_text())
        for c in n['cells']:
            if c['cell_type']=='code':
                tree=ast.parse(''.join(c['source']))
                self.assertFalse(any(isinstance(v,ast.Attribute) and v.attr=='style' for v in ast.walk(tree)))
    def test_no_cloud_or_pickle_clients(self):
        s=(ROOT/'record_workflow.py').read_text()
        for token in ['import boto3','import kaggle','pickle.load','git push','git reset']:
            self.assertNotIn(token,s)


class SafetyTests(unittest.TestCase):
    def test_checkpoint_reuse(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'x').write_text('a');r.seal(p,['x']);self.assertTrue(r.verify_checkpoint(p,['x']))
    def test_corrupt_checkpoint_stops(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'x').write_text('a');r.seal(p,['x']);(p/'x').write_text('b')
            with self.assertRaises(ValueError):r.verify_checkpoint(p,['x'])
    def test_path_traversal_stops(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):r.safe_file(Path(t),'../x')
    def test_symlink_stops(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'x').write_text('a');(p/'y').symlink_to(p/'x')
            with self.assertRaises(ValueError):r.safe_file(p,'y')
    def test_unsafe_receipt_stops(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);r.atomic_json(p/'complete.json',{'complete':True,'outputs':{'../x':'foo'}})
            with self.assertRaises(ValueError):r.verify_checkpoint(p,[])
    def test_output_missing_stops(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);r.seal(p,[])
            with self.assertRaises(ValueError):r.verify_checkpoint(p,['x'])
    def test_limit_cannot_increase(self):
        from run_round05 import run_stage
        with self.assertRaises(ValueError):run_stage('replicate',max_seconds=181)
    def test_supervisor_stops_child_at_time_limit(self):
        import run_round05 as runner
        with tempfile.TemporaryDirectory() as t, contextlib.redirect_stdout(io.StringIO()):
            p=Path(t)
            (p/'record_workflow.py').write_text('import time; time.sleep(30)')
            with patch.object(runner,'__file__',str(p/'run_round05.py')):
                with self.assertRaises(TimeoutError):runner.run_stage('replicate',max_seconds=1)
            self.assertEqual(json.loads((p/'reports/failure.json').read_text())['status'],'TIME_LIMIT')
    def test_supervisor_refuses_concurrent_stage(self):
        import run_round05 as runner
        import fcntl
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'reports').mkdir()
            with (p/'reports/execution.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(runner,'__file__',str(p/'run_round05.py')):
                    with self.assertRaisesRegex(RuntimeError,'Another stage'):runner.run_stage('prepare',max_seconds=1)
    def test_invalid_stage_stops(self):
        from run_round05 import run_stage
        with self.assertRaises(ValueError):run_stage('submit',max_seconds=1)


class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,cls.d,cls.s,cls.t=data(seasons=[2018,2019],gender='W')
        cls.b,_=r.rf.build_snapshot(cls.c,cls.d,cls.s,'W',2019)
        cls.f,cls.g=r.sf.build_schedule_snapshot(cls.c,cls.b,'W',2019)
    def test_postcutoff_games_do_not_enter(self):
        c=self.c.iloc[:1].copy();c['Season']=2019;c['DayNum']=133;c['WScore']=-9
        f,_=r.sf.build_schedule_snapshot(pd.concat([self.c,c]),self.b,'W',2019)
        pd.testing.assert_frame_equal(f,self.f)
    def test_future_seasons_do_not_enter(self):
        f,_=r.sf.build_schedule_snapshot(pd.concat([self.c,self.c.assign(Season=2026,WScore=-99)]),self.b,'W',2019)
        pd.testing.assert_frame_equal(f,self.f)
    def test_no_same_season_tournament_targets(self):
        with self.assertRaises(ValueError):r.sf.build_schedule_snapshot(self.c,self.b.assign(y=1),'W',2019)
    def test_swap_antisymmetry(self):
        p,_=r.rf.tournament_pairs(self.t,'W',[2019])
        a=r.sf.matchup_features(self.f,p);b=r.sf.matchup_features(self.f,p.rename(columns={'Team1ID':'Team2ID','Team2ID':'Team1ID'}))
        np.testing.assert_allclose(a[r.RECORD],-b[r.RECORD],atol=0)
    def test_unchanged_record_formula(self):
        expected=self.g.groupby('TeamID').apply(lambda g:(g.win-g.reference_expectation).sum(),include_groups=False)
        np.testing.assert_allclose(self.f.set_index('TeamID').reference_surplus,expected,atol=1e-12)
    def test_input_row_order_does_not_matter(self):
        f,_=r.sf.build_schedule_snapshot(self.c.sample(frac=1,random_state=9),self.b.sample(frac=1,random_state=9),'W',2019)
        pd.testing.assert_frame_equal(f,self.f)


class IntegrationTests(unittest.TestCase):
    def test_pipeline_replay_resume_gate_and_both_ablation_branches(self):
        with tempfile.TemporaryDirectory() as t,contextlib.redirect_stdout(io.StringIO()):
            paths=build_fixture(Path(t))
            roots=['repo','schedule','shooting']
            before={key:{str(p.relative_to(paths[key])):r.sha(p) for p in paths[key].rglob('*') if p.is_file()} for key in roots}
            with patch.object(r.wf,'EXPECTED_SHA',paths['head']):
                ctx=r.preflight(paths['kit'],paths['repo'],paths['schedule'],paths['shooting'])
                with patch.object(r.rf,'build_snapshot',side_effect=AssertionError('No rating rebuild allowed')):
                    r.prepare(ctx)
                r.replicate(ctx)
                out=ctx['directory'];receipt=r.read_json(out/'replication_receipt.json')
                self.assertEqual(receipt['new_classifier_fits'],5)
                self.assertEqual(receipt['upstream_classifier_fits_replayed'],3)
                real_gate=r.read_json(out/'gate.json')
                # Unit exercise skip branch regardless of fixture's accidental statistical result.
                with patch.object(r,'checked_replication'):
                    forced=dict(real_gate,proceed_to_ablation=False,decision='STOP_EXPANSION')
                    r.atomic_json(out/'gate.json',forced)
                    with patch.object(r.wf,'fitted_model',side_effect=AssertionError('Skipped gate must not fit')):
                        r.ablate(ctx)
                    self.assertEqual(r.read_json(out/'ablation_receipt.json')['status'],'SKIPPED_BY_GATE')
                    forced=dict(real_gate,proceed_to_ablation=True,decision='RUN_BOUNDED_ABLATIONS')
                    r.atomic_json(out/'gate.json',forced);r.ablate(ctx)
                    r.report(ctx)
                    self.assertEqual(r.read_json(out/'plot_manifest.json')['count'],10)
                    self.assertEqual(r.read_json(out/'ablation_receipt.json')['new_classifier_fits'],16)
                    with patch.object(r.wf,'fitted_model',side_effect=AssertionError('Valid checkpoint must be reused')):
                        r.ablate(ctx)
                    self.assertEqual(r.read_json(out/'ablation_receipt.json')['new_classifier_fits'],0)
                r.atomic_json(out/'gate.json',real_gate)
                with patch.object(r.wf,'fitted_model',side_effect=AssertionError('Prior fit must not repeat')):
                    r.replicate(ctx)
                self.assertEqual(r.read_json(out/'replication_receipt.json')['new_classifier_fits'],0)
                r.ablate(ctx);r.report(ctx);r.preservation(ctx)
                self.assertTrue((paths['kit']/'reports/milestone_05_return.zip').is_file())
                import zipfile
                with zipfile.ZipFile(paths['kit']/'reports/milestone_05_return.zip') as z:
                    self.assertNotIn('replication_predictions.csv',z.namelist())
                    self.assertFalse(any('model' in n for n in z.namelist()))
                after={key:{str(p.relative_to(paths[key])):r.sha(p) for p in paths[key].rglob('*') if p.is_file()} for key in roots}
                self.assertEqual(before,after)
                # Expected data mismatch must fail before fitting.
                p=paths['repo']/'data/kaggle/raw/WRegularSeasonCompactResults.csv';p.write_bytes(p.read_bytes()+b'\n')
                with self.assertRaisesRegex(ValueError,'Raw data differs'):
                    r.preflight(paths['kit'],paths['repo'],paths['schedule'],paths['shooting'])

if __name__=='__main__':unittest.main()
