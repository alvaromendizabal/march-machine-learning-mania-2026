"""Synthetic safety, formula, temporal, regression and checkpoint tests."""
from __future__ import annotations
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import schedule_features as sf
import schedule_workflow as sw
from fixtures import data,write_fixture
rf=sw.reference_features;wf=sw.reference_workflow

class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,cls.d,cls.s,cls.t=data(seasons=[2017,2018,2019])
        cls.b,_=rf.build_snapshot(cls.c,cls.d,cls.s,'M',2018)
        cls.f,cls.a=sf.build_schedule_snapshot(cls.c,cls.b,'M',2018)
    def test_seven_registered_features(self):
        self.assertEqual(len(sf.NEW_COLS),7);self.assertEqual(len(set(sf.NEW_COLS)),7)
    def test_seed_weights(self):
        self.assertTrue(np.isin(self.a.quality_points,[6.,4.,.25]).all())
        self.assertTrue((self.a.loc[self.a.opp_seed<=4,'quality_points']==6).all())
    def test_no_secondary_tournament_inputs(self):
        self.assertNotIn('secondary',','.join(sf.PARAMETERS))
    def test_sum_quality_wins(self):
        expected=self.a.assign(v=self.a.win*self.a.quality_points).groupby('TeamID').v.sum()
        np.testing.assert_allclose(self.f.set_index('TeamID').quality_points_won,expected)
    def test_nonhome_subset(self):
        self.assertTrue((self.f.quality_points_won_nonhome<=self.f.quality_points_won).all())
    def test_reference_surplus_formula(self):
        expected=self.a.groupby('TeamID').apply(lambda g: (g.win-g.reference_expectation).sum(),include_groups=False)
        np.testing.assert_allclose(self.f.set_index('TeamID').reference_surplus,expected,atol=1e-12)
    def test_zero_losses_bad_loss_zero(self):
        b=self.b.copy();b.loc[b.index[0],'seed']=np.nan
        f,a=sf.build_schedule_snapshot(self.c,b,'M',2018)
        self.assertTrue((f.quality_bad_losses>=0).all())
    def test_probability_range(self):
        self.assertTrue(self.a.reference_expectation.between(0,1,inclusive='neither').all())
    def test_venue_direction(self):
        a=self.a.iloc[0]
        from scipy.special import expit
        ref=self.f.reference_strength.iloc[0]
        self.assertGreater(expit((ref-a.opp_strength+3)/10),expit((ref-a.opp_strength-3)/10))
    def test_future_rows_ignored(self):
        c=self.c.copy();c.loc[c.Season==2019,'WScore']=10000
        f,_=sf.build_schedule_snapshot(c,self.b,'M',2018)
        pd.testing.assert_frame_equal(f,self.f)
    def test_postcutoff_rows_ignored(self):
        extra=self.c.iloc[:1].copy();extra['Season']=2018;extra['DayNum']=133;extra['WScore']=-1
        f,_=sf.build_schedule_snapshot(pd.concat([self.c,extra]),self.b,'M',2018)
        pd.testing.assert_frame_equal(f,self.f)
    def test_future_seeds_ignored(self):
        b=pd.concat([self.b,self.b.assign(Season=2019,strength=999,seed=99)])
        f,_=sf.build_schedule_snapshot(self.c,b,'M',2018)
        pd.testing.assert_frame_equal(f,self.f)
    def test_row_order_invariance(self):
        f,_=sf.build_schedule_snapshot(self.c.sample(frac=1,random_state=2),self.b.sample(frac=1,random_state=3),'M',2018)
        pd.testing.assert_frame_equal(f,self.f)
    def test_duplicate_game_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            sf.build_schedule_snapshot(pd.concat([self.c,self.c.loc[self.c.Season==2018].iloc[:1]]),self.b,'M',2018)
    def test_missing_strength_rejected(self):
        b=self.b.copy();b.loc[0,'strength']=np.nan
        with self.assertRaises(ValueError):sf.build_schedule_snapshot(self.c,b,'M',2018)
    def test_missing_opponent_rejected(self):
        with self.assertRaises(ValueError):sf.build_schedule_snapshot(self.c,self.b.iloc[1:],'M',2018)
    def test_wrong_cutoff_rejected(self):
        with self.assertRaises(ValueError):sf.build_schedule_snapshot(self.c,self.b.assign(snapshot_day=131),'M',2018)
    def test_missing_entire_field_rejected(self):
        with self.assertRaises(ValueError):sf.build_schedule_snapshot(self.c,self.b.assign(seed=np.nan),'M',2018)
    def test_cached_game_count_rejected(self):
        b=self.b.copy();b.loc[0,'games']+=1
        with self.assertRaises(ValueError):sf.build_schedule_snapshot(self.c,b,'M',2018)
    def test_current_2026_forbidden(self):
        with self.assertRaises(ValueError):sf.build_schedule_snapshot(self.c,self.b,'M',2026)
    def test_tournament_labels_rejected(self):
        with self.assertRaises(ValueError):sf.build_schedule_snapshot(self.c,self.b.assign(y=1),'M',2018)
    def test_feature_swap(self):
        pairs,_=rf.tournament_pairs(self.t,'M',[2018])
        x=sf.matchup_features(self.f,pairs)
        r=sf.matchup_features(self.f,pairs.rename(columns={'Team1ID':'Team2ID','Team2ID':'Team1ID'}))
        np.testing.assert_allclose(x[sf.NEW_COLS],-r[sf.NEW_COLS],atol=0)
    def test_feature_label_guard(self):
        pairs,y=rf.tournament_pairs(self.t,'M',[2018])
        with self.assertRaises(ValueError):sf.matchup_features(self.f,pairs.assign(y=y))
    def test_bad_matchup_rejected(self):
        pairs,_=rf.tournament_pairs(self.t,'M',[2018]);pairs['Team2ID']=9999
        with self.assertRaises(ValueError):sf.matchup_features(self.f,pairs)
    def test_fixed_input_sets(self):
        self.assertEqual([len(v) for v in sw.RECIPES.values()],[16,19,20,23])
    def test_old_flag_false_not_success(self):
        m=pd.read_csv(ROOT/'evidence/smoke_metrics.csv')
        result=sw.prior_screens(m)
        self.assertTrue(result['all_six_additions_worsened_2019'])
        self.assertFalse(result['old_clearly_unproductive_flag'])
    def test_scale_is_training_only(self):
        x=pd.DataFrame({'x':[-2.,1.,2.,-1.]});y=np.array([0,1,1,0])
        m=wf.fitted_model(x,y,['x'])
        self.assertAlmostEqual(m['scales'][0],np.sqrt(2.5))
        p=wf.predict(m,pd.DataFrame({'x':[100.]}));self.assertGreater(p[0],.5)
    def test_prediction_complements(self):
        x=pd.DataFrame({'x':[-2.,1.,2.,-1.]});y=np.array([0,1,1,0]);m=wf.fitted_model(x,y,['x'])
        np.testing.assert_allclose(wf.predict(m,x)+wf.predict(m,-x),1,atol=1e-14)

class IntegrityTests(unittest.TestCase):
    def test_corrupt_checkpoint_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'x.csv').write_text('x\n1');sw.seal(p,['x.csv']);(p/'x.csv').write_text('x\n2')
            with self.assertRaisesRegex(ValueError,'Corrupt'):sw.verify_checkpoint(p,['x.csv'])
    def test_unsafe_checkpoint_path_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);sw.atomic_json(p/'complete.json',{'complete':True,'outputs':{'../x':'bad'}})
            with self.assertRaises(ValueError):sw.verify_checkpoint(p,[])
    def test_checkpoint_missing_output_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'x').write_text('ok');sw.seal(p,['x'])
            with self.assertRaises(ValueError):sw.verify_checkpoint(p,['y'])
    def test_checkpoint_reuse(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'x').write_text('ok');sw.seal(p,['x']);self.assertTrue(sw.verify_checkpoint(p,['x']))
    def test_no_pickle_loading(self):
        self.assertNotIn('pickle.load',(ROOT/'schedule_workflow.py').read_text())
    def test_no_rating_fits_in_new_features(self):
        self.assertNotIn('.fit(', (ROOT/'schedule_features.py').read_text())
    def test_no_panel_cli(self):
        self.assertNotIn("choices=['smoke','panel']",(ROOT/'run_round04.py').read_text())

class PipelineTests(unittest.TestCase):
    def test_full_pipeline_reuses_snapshots_models_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as t,contextlib.redirect_stdout(io.StringIO()):
            root=Path(t);repo=root/'repo';old=root/'old';kit=root/'kit';repo.mkdir();old.mkdir();kit.mkdir()
            for n in ['shot_features.py','research_workflow.py','run_round02.py']:
                shutil.copy2(ROOT/'reference'/n,old/n)
            for n in ['schedule_features.py','schedule_workflow.py','schedule_plots.py','run_round04.py']:
                shutil.copy2(ROOT/n,kit/n)
            shutil.copytree(ROOT/'reference',kit/'reference')
            (kit/'evidence').mkdir()
            head=write_fixture(repo,old)
            with patch.object(wf,'EXPECTED_SHA',head):
                parent=wf.preflight(old,repo);wf.prepare(parent,'smoke');wf.evaluate(parent,'smoke')
                for n in ['manifest.json','preflight.json','smoke_metrics.csv']:
                    shutil.copy2(parent['directory']/n,kit/'evidence'/n)
                before={str(p.relative_to(repo)):sw.sha(p) for p in repo.rglob('*') if p.is_file()}
                ctx=sw.preflight(kit,repo,old)
                with patch.object(rf,'build_snapshot',side_effect=AssertionError('No old rebuild allowed')):
                    sw.prepare(ctx);sw.evaluate(ctx);sw.report(ctx)
                self.assertEqual(sw.read_json(ctx['directory']/'summary.json')['new_classifier_fits'],8)
                self.assertEqual(sw.read_json(ctx['directory']/'prepare.json')['upstream_snapshots_reused'],14)
                sw.prepare(ctx)
                with patch.object(wf,'fitted_model',side_effect=AssertionError('No repeated fits allowed')):
                    sw.evaluate(ctx)
                self.assertEqual(sw.read_json(ctx['directory']/'summary.json')['new_classifier_fits'],0)
                self.assertEqual(sw.read_json(ctx['directory']/'summary.json')['reused_classifier_fits'],8)
                after={str(p.relative_to(repo)):sw.sha(p) for p in repo.rglob('*') if p.is_file()}
                self.assertEqual(before,after)
                from schedule_plots import figures
                self.assertEqual(len(figures(ctx['directory'])),10)
                self.assertTrue((kit/'reports/milestone_04_return.zip').is_file())

if __name__=='__main__':unittest.main()
