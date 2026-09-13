from __future__ import annotations
import ast, json, shutil, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import bracket_features as f
import bracket_workflow as w
import bracket_io as io
import run_round09 as runner
import bracket_plots as plots
from fixtures import toy_data,build_fixture

class Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seeds,cls.bases,cls.targets=toy_data();cls.base=pd.concat(cls.bases,ignore_index=True)
    def pair(self,s,sa,sb):
        p=self.seeds.query('Season==@s').set_index('Seed').TeamID
        return pd.DataFrame([{'Gender':'W','Season':s,'Team1ID':int(p[sa]),'Team2ID':int(p[sb])}])
    def test_top4_in_same_pod(self):
        x,_=f.pair_features(self.base,self.seeds,self.pair(2016,'W01','W09'));self.assertEqual(x[f.HOST[0]].iloc[0],1.)
    def test_reverse_sign(self):
        x,_=f.pair_features(self.base,self.seeds,self.pair(2016,'W09','W01'));self.assertEqual(x[f.HOST[0]].iloc[0],-1.)
    def test_different_pod_zero_not_status(self):
        x,_=f.pair_features(self.base,self.seeds,self.pair(2016,'W01','W12'));self.assertEqual(x[f.HOST[0]].iloc[0],0.);self.assertEqual(x[f.STATUS[0]].iloc[0],1.)
    def test_different_region_zero(self):
        x,_=f.pair_features(self.base,self.seeds,self.pair(2016,'W01','X09'));self.assertEqual(x[f.HOST[0]].iloc[0],0.)
    def test_nonhost_pod_pair_zero(self):
        x,_=f.pair_features(self.base,self.seeds,self.pair(2016,'W08','W09'));self.assertEqual(x[f.HOST[0]].iloc[0],0.)
    def test_pre2015_inapplicable(self):
        x,d=f.pair_features(self.base,self.seeds,self.pair(2014,'W01','W09'));self.assertEqual(x[f.HOST[0]].iloc[0],0.);self.assertEqual(d.cohort.iloc[0],'pre_policy_not_encoded')
    def test_policy_starts_2015(self):
        x,_=f.pair_features(self.base,self.seeds,self.pair(2015,'W01','W16'));self.assertEqual(x[f.HOST[0]].iloc[0],1.)
    def test_complete_pairs_and_counts(self):
        x,d,c=f.build_season(self.bases[-1],self.seeds,2019);self.assertEqual(len(x),2016);self.assertEqual(c['eligible_pairs'],48);self.assertEqual(c['same_pod_pairs'],96)
    def test_swap_all_columns(self):
        p=self.pair(2019,'W02','W07');x,_=f.pair_features(self.base,self.seeds,p);q,_=f.pair_features(self.base,self.seeds,p.rename(columns={'Team1ID':'Team2ID','Team2ID':'Team1ID'}));np.testing.assert_allclose(x[f.ALL],-q[f.ALL])
    def test_base_unchanged(self):
        p=self.pair(2017,'W01','W09');x,_=f.pair_features(self.base,self.seeds,p);old=w.sf.pair_features(self.base,p);np.testing.assert_array_equal(x[f.BASE],old[f.BASE])
    def test_row_order_invariance(self):
        p=self.pair(2017,'W01','W09');a,_=f.pair_features(self.base,self.seeds,p);b,_=f.pair_features(self.base.sample(frac=1,random_state=2),self.seeds.sample(frac=1,random_state=3),p);pd.testing.assert_frame_equal(a,b)
    def test_unknown_year_stops(self):
        with self.assertRaises(ValueError):f.seed_panel(self.seeds,2026)
    def test_future_rows_ignored(self):
        s=self.seeds.iloc[:1].copy();s.Season=2026;s.Seed='bad';a=f.seed_panel(self.seeds,2017);b=f.seed_panel(pd.concat([self.seeds,s]),2017);pd.testing.assert_frame_equal(a,b)
    def test_playin_rejected(self):
        s=self.seeds.copy();i=s.index[s.Season.eq(2017)][0];s.loc[i,'Seed']+='a'
        with self.assertRaises(ValueError):f.seed_panel(s,2017)
    def test_missing_seed_rejected(self):
        with self.assertRaises(ValueError):f.seed_panel(self.seeds.drop(self.seeds.query('Season==2017').index[0]),2017)
    def test_duplicate_seed_rejected(self):
        s=self.seeds.copy();inds=s.index[s.Season.eq(2017)];s.loc[inds[1],'Seed']=s.loc[inds[0],'Seed']
        with self.assertRaises(ValueError):f.seed_panel(s,2017)
    def test_seed_disagrees_with_cache(self):
        p=self.pair(2017,'W01','W09');b=self.base.copy();b.loc[(b.Season==2017)&(b.TeamID==p.Team1ID.iloc[0]),'seed']=2
        with self.assertRaises(ValueError):f.pair_features(b,self.seeds,p)
    def test_outcomes_and_locations_forbidden(self):
        for n in ['y','WLoc','DayNum','CityID','WScore']:
            with self.subTest(n=n):
                with self.assertRaises(ValueError):f.pair_features(self.base,self.seeds,self.pair(2017,'W01','W09').assign(**{n:1}))
    def test_men_not_supported(self):
        with self.assertRaises(ValueError):f.pair_features(self.base,self.seeds,self.pair(2017,'W01','W09').assign(Gender='M'))
    def test_scaled_eligibility_decreases_with_variability(self):
        p=self.pair(2017,'W01','W09');x,_=f.pair_features(self.base,self.seeds,p);b=self.base.copy();b['margin_sd']*=2;y,_=f.pair_features(b,self.seeds,p);self.assertLess(y[f.SCALED[0]].iloc[0],x[f.SCALED[0]].iloc[0])
    def test_invalid_variability_stops(self):
        b=self.base.copy();b['margin_sd']=-1
        with self.assertRaises(ValueError):f.pair_features(b,self.seeds,self.pair(2017,'W01','W09'))
    def test_feature_definitions_fixed(self):
        self.assertEqual([len(v) for v in f.RECIPES.values()],[16,17,18,19]);self.assertEqual(f.registry().novel.sum(),2)

class Contracts(unittest.TestCase):
    def test_gate_pass(self):
        d=pd.DataFrame([{'Season':s,'comparison':'scaled_given_status','delta_brier':-.001} for s in w.SEASONS]);self.assertEqual(w.decision(d)['decision'],'CONSIDER_CONFIRMED_VENUE_REPLICATION')
    def test_gate_wrong_comparison_not_substituted(self):
        d=pd.DataFrame([{'Season':s,'comparison':c,'delta_brier':v} for s in w.SEASONS for c,v in [('scaled_given_status',.001),('status_vs_anchor',-.01)]]);self.assertEqual(w.decision(d)['decision'],'DO_NOT_EXPAND_AUTOMATICALLY')
    def test_gate_incomplete_stops(self):
        with self.assertRaises(ValueError):w.decision(pd.DataFrame([{'Season':2016,'comparison':'scaled_given_status','delta_brier':-.1}]))
    def test_gate_worst_season_limit(self):
        d=pd.DataFrame([{'Season':s,'comparison':'scaled_given_status','delta_brier':v} for s,v in zip(w.SEASONS,[-.02,-.02,-.02,.004])]);self.assertEqual(w.decision(d)['decision'],'DO_NOT_EXPAND_AUTOMATICALLY')
    def test_missing_old_logloss_recomputed(self):
        y=np.array([0,1]);p=np.array([.2,.8]);m={'brier':.04};n=io.normalize_metric(m,y,p,'W',2017);self.assertAlmostEqual(n['log_loss'],-np.log(.8));self.assertNotIn('log_loss',m)
    def test_inconsistent_stored_logloss_stops(self):
        with self.assertRaises(ValueError):io.normalize_metric({'brier':.04,'log_loss':0},np.array([0,1]),np.array([.2,.8]),'W',2017)
    def test_probability_endpoints_stopped(self):
        with self.assertRaises(ValueError):io.normalize_metric({'brier':0},np.array([0,1]),np.array([0.,1.]),'W',2017)
    def test_notebook_has_no_styler(self):
        nb=json.loads((ROOT/'09_womens_bracket_context.ipynb').read_text());self.assertEqual(sum(c['cell_type']=='code' for c in nb['cells']),9)
        for c in nb['cells']:
            if c['cell_type']=='code':self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr=='style' for n in ast.walk(ast.parse(''.join(c['source'])))))
    def test_hard_caps(self):
        for stage,n in [('prepare',181),('evaluate',181),('report',121)]:
            with self.assertRaises(ValueError):runner.run_stage(stage,max_seconds=n)
    def test_invalid_stage(self):
        with self.assertRaises(ValueError):runner.run_stage('train_forever')
    def test_process_timeout(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);shutil.copy2(ROOT/'run_round09.py',r/'run_round09.py');(r/'bracket_workflow.py').write_text('import time\ntime.sleep(9)\n')
            p=subprocess.run([sys.executable,str(r/'run_round09.py'),'prepare','--max-seconds','1'],capture_output=True,timeout=8);self.assertNotEqual(p.returncode,0);self.assertEqual(json.loads((r/'reports/failure.json').read_text())['status'],'TIME_LIMIT')
    def test_concurrent_run_rejected(self):
        import fcntl
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);shutil.copy2(ROOT/'run_round09.py',r/'run_round09.py');(r/'reports').mkdir()
            with (r/'reports/execution.lock').open('a') as f_:
                fcntl.flock(f_,fcntl.LOCK_EX|fcntl.LOCK_NB)
                p=subprocess.run([sys.executable,str(r/'run_round09.py'),'prepare'],capture_output=True,timeout=5);self.assertNotEqual(p.returncode,0);self.assertIn(b'Another stage',p.stderr)

class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)/'fixture';cls.args,cls.head=build_fixture(cls.root)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();r=Path(self.temp.name)/'fixture';shutil.copytree(self.root,r);self.args={k:r/p.relative_to(self.root) for k,p in self.__class__.args.items()};self.patch=patch.object(w.rf,'EXPECTED_SHA',self.head);self.patch.start();self.ctx=w.preflight(**self.args)
    def tearDown(self):self.patch.stop();self.temp.cleanup()
    def test_prepare_no_fits(self):
        with patch.object(w.rf,'fitted_model',side_effect=AssertionError('No classifier fitting')):w.prepare(self.ctx)
        self.assertEqual(w.read_json(self.ctx['directory']/'prepare.json')['baseline_replays'],4)
    def test_full_run_checkpoint_reuse_and_report(self):
        w.prepare(self.ctx);w.evaluate(self.ctx);r=w.read_json(self.ctx['directory']/'evaluation_receipt.json');self.assertEqual(r['new_classifier_fits'],12);self.assertEqual(r['upstream_replays'],4)
        with patch.object(w.rf,'fitted_model',side_effect=AssertionError('No refits')),patch.object(f,'build_season',side_effect=AssertionError('No rebuilds')):w.prepare(self.ctx);w.evaluate(self.ctx)
        self.assertEqual(w.read_json(self.ctx['directory']/'evaluation_receipt.json')['local_reuses'],12);w.report(self.ctx)
        self.assertEqual(len(plots.figures(self.ctx['directory'],self.ctx['kit']/'evidence/round08')),10)
        with zipfile.ZipFile(self.ctx['kit']/'reports/milestone_09_return.zip') as z:self.assertNotIn('predictions.csv',z.namelist());self.assertNotIn('model.json',z.namelist())
    def test_raw_change_rejected(self):
        p=self.ctx['raw']/'WNCAATourneySeeds.csv';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_upstream_corruption_rejected(self):
        p=self.ctx['shooting']/'snapshots/W_2013/teams.csv';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_missing_reference_rejected(self):
        (self.ctx['record']/'fits/W_2016_anchor/model.json').unlink()
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_source_change_rejected(self):
        p=self.ctx['kit']/'bracket_features.py';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_environment_change_rejected(self):
        with patch.object(w,'environment',return_value={}):
            with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_known_notebook_edits_preserved(self):
        before={n:w.sha(self.ctx['repo']/n) for n in w.rf.ALLOWED_DIRTY};w.prepare(self.ctx);w.preservation(self.ctx);self.assertEqual(before,{n:w.sha(self.ctx['repo']/n) for n in w.rf.ALLOWED_DIRTY})
    def test_new_notebook_edit_rejected(self):
        p=self.ctx['repo']/next(iter(w.rf.ALLOWED_DIRTY));p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_fit_budget_stops_before_fit(self):
        w.prepare(self.ctx)
        with patch.object(w.rf,'fitted_model',side_effect=AssertionError('Budget did not stop')):
            with self.assertRaises(ValueError):w.obtain(self.ctx,2016,'seed_status',w.matrices(self.ctx),0)
    def test_changed_stage_artifact_rejected(self):
        w.prepare(self.ctx);p=self.ctx['directory']/'prepare.json';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.evaluate(self.ctx)
    def test_future_tournament_rows_not_used(self):
        w.prepare(self.ctx);b=w.matrices(self.ctx);p=self.ctx['raw']/'WNCAATourneyCompactResults.csv';d=w.read_csv(p);e=d.iloc[:1].copy();e.Season=2026;w.atomic_csv(p,pd.concat([d,e]));q=w.matrices(self.ctx);pd.testing.assert_frame_equal(b[2],q[2]);np.testing.assert_array_equal(b[1],q[1])
    def test_unsafe_paths_rejected(self):
        with self.assertRaises(ValueError):w.safe_file(self.ctx['kit'],'../repo/.gitignore')
        p=self.ctx['kit']/'link';p.symlink_to(self.ctx['repo']/'.gitignore')
        with self.assertRaises(ValueError):w.safe_file(self.ctx['kit'],'link')
    def test_no_direct_repository_import(self):self.assertFalse(w.read_json(self.ctx['directory']/'preflight.json')['repository_source_imported'])
    def test_chronological_training(self):
        w.prepare(self.ctx);x=w.matrices(self.ctx)[2]
        for s in w.SEASONS:
            ti,vi=w.rf.split_indices(x,s);self.assertTrue((x.iloc[ti].Season<s).all());self.assertTrue((x.iloc[vi].Season==s).all())

if __name__=='__main__':unittest.main()
