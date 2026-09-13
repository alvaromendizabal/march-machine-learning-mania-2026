from pathlib import Path
import importlib.abc,json,os,subprocess,sys,tempfile,unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import form_features as f
import form_workflow as w
from fixtures import data,build_fixture

class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,cls.d,cls.s,cls.t=data(seasons=[2017],gender='W')
        cls.base,_=w.sf.build_snapshot(cls.c,cls.d,cls.s,'W',2017)
        cls.model=f.fit_early(cls.d,2017)
        cls.feats,cls.games=f.build_snapshot(cls.d,cls.base,'W',2017,cls.model)
    def test_feature_count(self):self.assertEqual(len(f.ALL_COLS),4);self.assertEqual([len(x) for x in w.RECIPES.values()],[16,18,18,20])
    def test_early_max_day(self):self.assertLessEqual(self.model['max_training_day'],100)
    def test_late_boundaries(self):self.assertTrue(self.games.DayNum.between(101,132).all())
    def test_late_scores_cannot_change_early_model(self):
        d=self.d.copy();d.loc[d.DayNum>100,'WScore']+=100
        self.assertEqual(self.model,f.fit_early(d,2017))
    def test_future_rows_ignored(self):
        future=self.d.copy();future['Season']=2026;future['WScore']=-1
        self.assertEqual(self.model,f.fit_early(pd.concat([self.d,future]),2017))
    def test_post_cutoff_rows_ignored(self):
        future=self.d.copy();future['DayNum']=140;future['WScore']=-1
        x,_=f.build_snapshot(pd.concat([self.d,future]),self.base,'W',2017,self.model)
        pd.testing.assert_frame_equal(x,self.feats)
    def test_bad_legal_counts_rejected(self):
        d=self.d.copy();d.loc[d.index[0],'WFGM']=1000
        with self.assertRaises(ValueError):f.fit_early(d,2017)
    def test_input_order_invariance(self):self.assertEqual(self.model,f.fit_early(self.d.sample(frac=1,random_state=1),2017))
    def test_duplicate_games_rejected(self):
        with self.assertRaises(ValueError):f.fit_early(pd.concat([self.d,self.d.iloc[:1]]),2017)
    def test_zero_support_prior(self):
        base=self.base.copy();extra=base.iloc[[0]].copy();extra['TeamID']=3999;base=pd.concat([base,extra])
        x,_=f.build_snapshot(self.d,base,'W',2017,self.model)
        row=x.query('TeamID==3999').iloc[0];self.assertEqual(row['late_games'],0);self.assertTrue((row[f.FEATURES].to_numpy()==0).all())
    def test_shrinkage_formula(self):
        t=self.feats.TeamID.iloc[0];g=self.games.query('TeamID==@t and known_early==True')
        expected=(g.offense_surprise*g.weight).sum()/(g.weight.sum()+5)
        self.assertAlmostEqual(expected,self.feats.set_index('TeamID').loc[t,'late_offense_surprise'])
    def test_change_formula(self):
        t=self.feats.TeamID.iloc[0];g=self.games.query('TeamID==@t and known_early==True');a=g[g.DayNum<=116];b=g[g.DayNum>116]
        expected=b.defense_surprise.sum()/(len(b)+5)-a.defense_surprise.sum()/(len(a)+5)
        self.assertAlmostEqual(expected,self.feats.set_index('TeamID').loc[t,'late_defense_change'])
    def test_defense_sign(self):
        r=self.games.iloc[0];reverse=self.games.query('TeamID==@r.OpponentID and OpponentID==@r.TeamID and DayNum==@r.DayNum').iloc[0]
        self.assertAlmostEqual(r.defense_surprise,-reverse.offense_surprise)
    def test_swap(self):
        pairs,_=w.sf.tournament_pairs(self.t,'W',[2017]);a=f.pair_features(self.feats,pairs);b=f.pair_features(self.feats,pairs.rename(columns={'Team1ID':'Team2ID','Team2ID':'Team1ID'}))
        np.testing.assert_allclose(a[f.ALL_COLS],-b[f.ALL_COLS],atol=1e-12)
    def test_missing_team_rejected(self):
        pairs,_=w.sf.tournament_pairs(self.t,'W',[2017]);pairs.loc[0,'Team1ID']=9999
        with self.assertRaises(ValueError):f.pair_features(self.feats,pairs)
    def test_no_targets_in_registry(self):self.assertFalse(f.registry(w.ANCHOR).uses_tournament_outcomes.any())
    def test_illegal_season_rejected(self):
        with self.assertRaises(ValueError):f.fit_early(self.d,2026)
    def test_wrong_base_identity(self):
        with self.assertRaises(ValueError):f.build_snapshot(self.d,self.base,'M',2017,self.model)
    def test_no_jinja_notebook_cells(self):
        nb=json.loads((ROOT/'06_temporal_form_features.ipynb').read_text())
        for cell in nb['cells']:
            if cell['cell_type']=='code':self.assertNotIn('.style',''.join(cell['source']))

class InfrastructureTests(unittest.TestCase):
    def test_csv_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.csv';df=pd.DataFrame({'x':[0.17320192076291752]});w.atomic_csv(p,df);pd.testing.assert_frame_equal(df,w.read_csv(p))
    def test_corrupt_checkpoint_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);w.atomic_json(p/'x.json',{'ok':1});w.seal(p,['x.json']);(p/'x.json').write_text('{}')
            with self.assertRaises(ValueError):w.verify_checkpoint(p,['x.json'])
    def test_partial_checkpoint_not_reused(self):
        with tempfile.TemporaryDirectory() as d:self.assertFalse(w.verify_checkpoint(Path(d),['x.json']))
    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):w.safe_file(Path(d),'../x')
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'a').write_text('a');(p/'b').symlink_to(p/'a')
            with self.assertRaises(ValueError):w.safe_file(p,'b')
    def test_temporal_split(self):
        x=pd.DataFrame({'Season':[2013,2014,2015,2016,2017,2018,2019]});ti,vi=w.split(x,2017)
        self.assertTrue((x.iloc[ti].Season<2017).all());self.assertEqual(list(x.iloc[vi].Season),[2017])
    def test_decision_requires_both_seasons(self):
        rows=[{'Gender':g,'recipe':r,'delta_vs_anchor':d} for g in w.CONFIG['genders'] for r in list(w.RECIPES)[1:] for d in [-.01,.001]]
        self.assertTrue(all(x['decision']=='DO_NOT_EXPAND_AUTOMATICALLY' for x in w.review_decisions(pd.DataFrame(rows))))
    def test_positive_rule_not_promotion(self):
        rows=[{'Gender':g,'recipe':r,'delta_vs_anchor':d} for g in w.CONFIG['genders'] for r in list(w.RECIPES)[1:] for d in [-.002,-.001]]
        result=w.review_decisions(pd.DataFrame(rows));self.assertTrue(all(not r['automatic_promotion'] for r in result))
        self.assertTrue(all(r['decision']=='CONSIDER_UNCHANGED_REPLICATION' for r in result))
    def test_invalid_limit(self):
        from run_round06 import run_stage
        with self.assertRaises(ValueError):run_stage('prepare',max_seconds=999)
    def test_invalid_stage(self):
        from run_round06 import run_stage
        with self.assertRaises(ValueError):run_stage('train',max_seconds=1)

class AdditionalSafetyTests(unittest.TestCase):
    def test_future_tournament_targets_excluded(self):
        _,_,_,t=data(seasons=[2017],gender='W')
        future=t.copy();future['Season']=2026;future['WScore']=-100
        p1,y1=w.sf.tournament_pairs(t,'W',[2017]);p2,y2=w.sf.tournament_pairs(pd.concat([t,future]),'W',[2017])
        pd.testing.assert_frame_equal(p1,p2);np.testing.assert_array_equal(y1,y2)
    def test_wrong_early_model_season_rejected(self):
        _,d,_,_=data(seasons=[2017],gender='W');m=f.fit_early(d,2017);m['Season']=2016
        with self.assertRaises(ValueError):f.late_residuals(d,2017,m)
    def test_supervisor_stops_process_at_limit(self):
        import importlib.util,shutil
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);shutil.copy2(ROOT/'run_round06.py',p/'run_round06.py')
            (p/'form_workflow.py').write_text('import time\ntime.sleep(10)\n')
            spec=importlib.util.spec_from_file_location('bounded_test_runner',p/'run_round06.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            with self.assertRaises(TimeoutError):module.run_stage('prepare',max_seconds=1)
            self.assertEqual(json.loads((p/'reports/failure.json').read_text())['status'],'TIME_LIMIT')
    def test_supervisor_rejects_concurrent_run(self):
        import importlib.util,shutil,fcntl
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);shutil.copy2(ROOT/'run_round06.py',p/'run_round06.py');(p/'reports').mkdir()
            spec=importlib.util.spec_from_file_location('locked_test_runner',p/'run_round06.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            with (p/'reports/execution.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaises(RuntimeError):module.run_stage('prepare',max_seconds=1)

class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.fixture=build_fixture(Path(cls.tmp.name));cls.fixture_head=cls.fixture.pop('head')
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_full_run_then_reuse(self):
        with patch.object(w.wf,'EXPECTED_SHA',self.fixture_head):
            ctx=w.preflight(**self.fixture)
            w.prepare(ctx);w.evaluate(ctx);w.report(ctx);w.preservation(ctx)
            r=w.read_json(ctx['directory']/'evaluation_receipt.json');self.assertEqual(r['new_classifier_fits'],13);self.assertEqual(r['upstream_anchor_replays'],3)
            self.assertEqual(w.read_json(ctx['directory']/'prepare.json')['new_early_rating_fits'],14)
            self.assertEqual(w.read_json(ctx['directory']/'plot_manifest.json')['count'],10)
            from zipfile import ZipFile
            with ZipFile(ctx['kit']/'reports/milestone_06_return.zip') as z:
                self.assertNotIn('predictions.csv',z.namelist());self.assertNotIn('model.json',z.namelist());self.assertIn('metrics.csv',z.namelist())
            with (patch.object(w.wf,'fitted_model',side_effect=AssertionError('duplicate classifier fit')),
                  patch.object(w.ff,'fit_early',side_effect=AssertionError('duplicate early rating fit'))):
                w.prepare(ctx);w.evaluate(ctx)
            self.assertEqual(w.read_json(ctx['directory']/'evaluation_receipt.json')['new_classifier_fits'],0)
            self.assertEqual(w.read_json(ctx['directory']/'evaluation_receipt.json')['local_checkpoint_reuses'],13)
            self.assertEqual(w.read_json(ctx['directory']/'prepare.json')['early_rating_checkpoint_reuses'],14)
    def test_changed_raw_stops(self):
        p=self.fixture['repo']/'data/kaggle/raw/WRegularSeasonCompactResults.csv';before=p.read_bytes();p.write_bytes(before+b'\n')
        try:
            with patch.object(w.wf,'EXPECTED_SHA',self.fixture_head),self.assertRaises(ValueError):w.preflight(**self.fixture)
        finally:p.write_bytes(before)
    def test_changed_source_stops(self):
        p=self.fixture['repo']/'src/constant.py';before=p.read_bytes();p.write_text('VALUE=2\n')
        try:
            with patch.object(w.wf,'EXPECTED_SHA',self.fixture_head),self.assertRaises(ValueError):w.preflight(**self.fixture)
        finally:p.write_bytes(before)
    def test_environment_change_stops(self):
        with patch.object(w.wf,'EXPECTED_SHA',self.fixture_head),patch.object(w,'environment',return_value={'bad':'version'}),self.assertRaises(ValueError):
            w.preflight(**self.fixture)
    def test_missing_cache_stops(self):
        p=self.fixture['shooting']/'private_runs'/('a'*64)/'snapshots/M_2017/complete.json';before=p.read_bytes();p.unlink()
        try:
            with patch.object(w.wf,'EXPECTED_SHA',self.fixture_head),self.assertRaises(ValueError):w.preflight(**self.fixture)
        finally:p.write_bytes(before)

if __name__=='__main__':unittest.main()
