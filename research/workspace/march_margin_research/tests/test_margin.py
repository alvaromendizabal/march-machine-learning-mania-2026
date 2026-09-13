from __future__ import annotations
import contextlib,copy,io,json,os,sys,tempfile,unittest,zipfile,hashlib,subprocess,fcntl
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from scipy import sparse
import margin_features as f
import margin_workflow as w
from fixtures import toy_data,build_fixture,manifest

class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw,cls.bases,_=toy_data()
        cls.models={k:f.fit_rating(cls.raw,2013,k)[0] for k in ['huber','compressed']}
    def test_huber_gradient(self):
        _,x,y,_,_=f.design(f.legal_results(self.raw,2013));t=np.linspace(-.5,.5,x.shape[1]);eps=1e-5
        g=f.objective(t,x,y)[1]
        numeric=[(f.objective(t+np.eye(len(t))[i]*eps,x,y)[0]-f.objective(t-np.eye(len(t))[i]*eps,x,y)[0])/(2*eps) for i in range(len(t))]
        np.testing.assert_allclose(g,numeric,rtol=1e-6,atol=1e-5)
    def test_certificate(self):
        for k in self.models:self.assertLessEqual(self.models[k]['diagnostics']['gradient_max_abs'],1e-5)
    def test_objective_monotone(self):
        _,tr=f.fit_rating(self.raw,2013,'huber');self.assertTrue((np.diff(tr.objective)<=1e-6).all())
    def test_prior_centers_abilities(self):
        for m in self.models.values():self.assertLess(abs(sum(m['theta'][:-1])),1e-7)
    def test_order_independence(self):
        for k in self.models:
            m,_=f.fit_rating(self.raw.sample(frac=1,random_state=9),2013,k)
            np.testing.assert_array_equal(m['theta'],self.models[k]['theta'])
    def test_future_rows_do_not_enter(self):
        raw=self.raw.copy();raw.loc[raw.Season.ne(2013),'WScore']=float('nan')
        extra=raw.iloc[[0]].copy();extra.DayNum=133;extra.WLoc='invalid'
        m,_=f.fit_rating(pd.concat([raw,extra]),2013,'huber');np.testing.assert_array_equal(m['theta'],self.models['huber']['theta'])
    def test_target_columns_do_not_enter(self):
        raw=self.raw.copy();raw['y']=np.nan;raw['TournamentWinner']='FAKE'
        m,_=f.fit_rating(raw,2013,'huber');np.testing.assert_array_equal(m['theta'],self.models['huber']['theta'])
    def test_duplicate_games_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):f.fit_rating(pd.concat([self.raw,self.raw.iloc[[0]]]),2013,'huber')
    def test_invalid_locations_rejected(self):
        raw=self.raw.copy();raw.loc[0,'WLoc']='X'
        with self.assertRaises(ValueError):f.fit_rating(raw,2013,'huber')
    def test_fractional_id_rejected(self):
        raw=self.raw.astype({'WTeamID':float});raw.loc[0,'WTeamID']+=.5
        with self.assertRaises(ValueError):f.fit_rating(raw,2013,'huber')
    def test_self_game_rejected(self):
        raw=self.raw.copy();raw.loc[0,'WTeamID']=raw.loc[0,'LTeamID']
        with self.assertRaises(ValueError):f.fit_rating(raw,2013,'huber')
    def test_nonfinite_score_rejected(self):
        raw=self.raw.astype({'WScore':float});raw.loc[0,'WScore']=np.inf
        with self.assertRaises(ValueError):f.fit_rating(raw,2013,'huber')
    def test_bad_season_rejected(self):
        with self.assertRaises(ValueError):f.fit_rating(self.raw,2026,'huber')
    def test_neutral_home_zero(self):
        raw=self.raw.copy();raw.WLoc='N'
        for k in self.models:self.assertEqual(f.fit_rating(raw,2013,k)[0]['theta'][-1],0)
    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):f.fit_rating(self.raw,2013,'other')
    def test_solver_budget_stops(self):
        _,x,y,_,_=f.design(f.legal_results(self.raw,2013))
        with self.assertRaisesRegex(ValueError,'stationarity'):f.solve_huber(x,y,max_steps=1,tolerance=1e-14)
    def test_invalid_solver_parameters(self):
        with self.assertRaises(ValueError):f.solve_huber(sparse.eye(2),np.ones(2),alpha=0)
    def test_large_delta_equals_ridge(self):
        _,x,y,_,_=f.design(f.legal_results(self.raw,2013))
        t,_=f.solve_huber(x,y,delta=1e6)
        expected=np.linalg.solve((x.T@x).toarray()+20*np.eye(x.shape[1]),x.T@y)
        np.testing.assert_allclose(t,expected,rtol=1e-10,atol=1e-10)
    def test_outlier_influence_reduced_not_win_removed(self):
        x=sparse.csr_matrix(np.ones((20,1)));y=np.r_[np.ones(19)*5,1000.]
        theta,_=f.solve_huber(x,y)
        self.assertLess(theta[0],y.sum()/40)
        self.assertGreater(theta[0],0.)
    def test_pair_count_and_control_parity(self):
        pairs,profiles,meta=f.build_matchups(self.bases[0],self.models)
        self.assertEqual(len(pairs),66);self.assertFalse(meta['label_inputs'])
        look=self.bases[0].set_index('TeamID')
        for feat in f.BASE:
            c=feat[5:];expect=look.loc[pairs.Team1ID,c].to_numpy()-look.loc[pairs.Team2ID,c].to_numpy()
            np.testing.assert_array_equal(pairs[feat],expect)
    def test_swap_antisymmetry_by_team_relabeling(self):
        base=self.bases[0].copy();models=copy.deepcopy(self.models)
        a,b=int(base.TeamID.iloc[0]),int(base.TeamID.iloc[1]);rename={a:b,b:a}
        original,_,_=f.build_matchups(base,models)
        base.TeamID=base.TeamID.map(lambda t:rename.get(int(t),int(t)))
        for m in models.values():m['teams']=[rename.get(t,t) for t in m['teams']]
        swapped,_,_=f.build_matchups(base,models)
        first=original.query('Team1ID==@a and Team2ID==@b')[f.ALL].to_numpy()
        second=swapped.query('Team1ID==@a and Team2ID==@b')[f.ALL].to_numpy()
        np.testing.assert_allclose(first,-second,atol=1e-12)
    def test_seed_dtype_does_not_change_values(self):
        a=self.bases[0].copy();a.seed=a.seed.astype(int)
        p,_,_=f.build_matchups(a,self.models);q,_,_=f.build_matchups(self.bases[0],self.models)
        np.testing.assert_array_equal(p[f.ALL].to_numpy(),q[f.ALL].to_numpy())
    def test_duplicate_snapshot_rejected(self):
        with self.assertRaises(ValueError):f.build_matchups(pd.concat([self.bases[0],self.bases[0].iloc[[0]]]),self.models)
    def test_missing_model_team_rejected(self):
        models=copy.deepcopy(self.models);models['huber']['teams'][0]=9999
        with self.assertRaisesRegex(ValueError,'Missing rating'):f.build_matchups(self.bases[0],models)
    def test_disconnected_seeded_teams_rejected(self):
        models=copy.deepcopy(self.models);models['huber']['graph_groups'][0]=1
        with self.assertRaisesRegex(ValueError,'disconnected'):f.build_matchups(self.bases[0],models)
    def test_registry_declares_exactly_two_candidates(self):
        self.assertEqual(f.registry().new_candidate.sum(),2);self.assertEqual(f.registry().swap_parity.unique().tolist(),[-1])

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.args,self.head=build_fixture(self.t.name)
        self.guard=patch.object(w.rf,'EXPECTED_SHA',self.head);self.guard.start()
        self.silence=contextlib.redirect_stdout(io.StringIO());self.silence.__enter__()
    def tearDown(self):self.silence.__exit__(None,None,None);self.guard.stop();self.t.cleanup()
    def ctx(self):return w.preflight(**self.args)
    def test_pipeline_repeat_reuses_all_and_preserves(self):
        c=self.ctx();w.prepare(c);w.evaluate(c);w.report(c)
        prep=w.read_json(c['directory']/'prepare.json');receipt=w.read_json(c['directory']/'evaluation_receipt.json')
        self.assertEqual(prep['new_rating_fits'],14);self.assertEqual(receipt['new_classifier_fits'],12)
        initial={str(p):w.sha(p) for p in c['directory'].rglob('*') if p.is_file() and (p.name=='complete.json' or p.name=='model.json' or p.name=='rating_model.json')}
        w.prepare(c);w.evaluate(c);w.report(c)
        self.assertEqual(w.read_json(c['directory']/'prepare.json')['rating_reuses'],14)
        self.assertEqual(w.read_json(c['directory']/'evaluation_receipt.json')['local_reuses'],12)
        self.assertEqual(initial,{str(p):w.sha(Path(p)) for p in initial})
        from margin_plots import figures
        self.assertEqual(len(figures(c['directory'],c['kit']/'evidence/round10')),10)
        report=c['kit']/'reports/milestone_11_return.zip'
        with zipfile.ZipFile(report) as z:
            self.assertIn('prior_milestone_10_return.zip',z.namelist())
            self.assertNotIn('predictions.csv',z.namelist())
            hashes=json.loads(z.read('return_integrity.json'))['sha256']
            self.assertTrue(all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in hashes.items()))
    def test_source_edit_stops(self):
        p=self.args['kit']/'margin_features.py';p.write_text(p.read_text()+'\n# edit')
        with self.assertRaisesRegex(ValueError,'Delivered source'):self.ctx()
    def test_raw_edit_stops(self):
        p=self.args['repo']/'data/kaggle/raw/MRegularSeasonCompactResults.csv';p.write_text(p.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'Raw input'):self.ctx()
    def test_environment_change_stops(self):
        with patch.object(w,'environment',return_value={'changed':True}):
            with self.assertRaisesRegex(ValueError,'Environment'):self.ctx()
    def test_missing_reference_stops(self):
        c=json.loads((self.args['kit']/'constraints.json').read_text());root=self.args['possession']/'private_runs'/c['fingerprints']['possession']
        (root/'fits/M_2016_anchor/model.json').unlink()
        with self.assertRaises(ValueError):self.ctx()
    def test_prior_report_checksum_stops(self):
        p=self.args['win_strength']/'reports/milestone_10_return.zip';p.write_bytes(p.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'Prior scientific'):self.ctx()
    def test_corrupt_completed_rating_stops(self):
        c=self.ctx();w.prepare(c);p=c['directory']/'ratings/M_2013_huber/rating_model.json';p.write_text('{}')
        with self.assertRaisesRegex(ValueError,'Corrupt'):w.prepare(c)
    def test_no_hidden_retraining_of_reference(self):
        c=self.ctx();w.prepare(c);bundle=w.matrices(c)
        with patch.object(w.rf,'fitted_model',side_effect=AssertionError('refit')):
            row,_,_,origin=w.obtain(c,2017,'anchor',bundle,0)
            self.assertEqual(origin,'upstream_replay');self.assertIn('log_loss',row)
    def test_budget_checked_before_classifier(self):
        c=self.ctx();w.prepare(c)
        with patch.object(w.rf,'fitted_model',side_effect=AssertionError('fit')):
            with self.assertRaisesRegex(ValueError,'budget'):w.obtain(c,2017,'anchor_huber',w.matrices(c),0)
    def test_changed_previous_report_during_run_stops(self):
        c=self.ctx();p=c['prior_zip'];p.write_bytes(p.read_bytes()+b'new')
        with self.assertRaisesRegex(ValueError,'Prior report'):w.preservation(c)
    def test_output_symlink_stops(self):
        p=self.args['kit']/'reports';p.symlink_to(self.args['repo'],target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'Unsafe'):self.ctx()
    def test_season_split_strict(self):
        c=self.ctx();w.prepare(c);_,_,x,_,_=w.matrices(c)
        for s in w.SEASONS:
            ti,vi=w.rf.split_indices(x,s);self.assertTrue((x.iloc[ti].Season<s).all());self.assertTrue((x.iloc[vi].Season==s).all())
    def test_both_gate_outcomes(self):
        good=pd.DataFrame([{'Season':s,'comparison':name,'delta_brier':-.002} for s in w.SEASONS for name in [w.CONFIG['primary'],w.CONFIG['secondary']]])
        self.assertTrue(all(r['decision'].startswith('CONSIDER') for r in w.decisions(good)['decisions']))
        good['delta_brier']=.002
        self.assertTrue(all(r['decision']=='DO_NOT_EXPAND_AUTOMATICALLY' for r in w.decisions(good)['decisions']))

class RunnerTests(unittest.TestCase):
    def test_limits_reject_before_execution(self):
        import run_round11 as r
        with self.assertRaises(ValueError):r.run_stage('evaluate',max_seconds=181)
    def test_stage_name_reject(self):
        import run_round11 as r
        with self.assertRaises(ValueError):r.run_stage('train_forever')
    def test_timeout_kills_child(self):
        import run_round11 as r
        with tempfile.TemporaryDirectory() as d:
            kit=Path(d);(kit/'margin_workflow.py').write_text('import time;time.sleep(30)')
            with patch.object(r,'__file__',str(kit/'run_round11.py')),contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(TimeoutError):r.run_stage('prepare',max_seconds=1)
            self.assertEqual(json.loads((kit/'reports/failure.json').read_text())['status'],'TIME_LIMIT')
    def test_concurrent_lock_reject(self):
        import run_round11 as r
        with tempfile.TemporaryDirectory() as d:
            kit=Path(d);(kit/'reports').mkdir()
            with (kit/'reports/execution.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(r,'__file__',str(kit/'run_round11.py')):
                    with self.assertRaisesRegex(RuntimeError,'Another'):r.run_stage('prepare',max_seconds=1)

if __name__=='__main__':unittest.main()
