from __future__ import annotations
import contextlib, copy, fcntl, io, json, os, shutil, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
import win_strength_features as f
import strength_workflow as w
from strength_io import normalize_metric
from fixtures import toy_data, build_fixture, manifest, ROOT


class Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games, cls.bases, _ = toy_data()
        cls.model, cls.team, cls.diag = f.fit_season(cls.games,2013)
        cls.pairs = pd.DataFrame({'Gender':['M','M'],'Season':[2013,2013], 'Team1ID':[1101,1102],'Team2ID':[1102,1103]})

    def test_gradient_matches_finite_difference(self):
        _,_,_,x,p=f.design(f.legal_results(self.games,2013));t=np.linspace(-.4,.4,x.shape[1]);value,g=f.objective(t,x,p)
        eps=1e-5;num=[]
        for i in range(len(t)):
            d=np.zeros_like(t);d[i]=eps;num.append((f.objective(t+d,x,p)[0]-f.objective(t-d,x,p)[0])/(2*eps))
        np.testing.assert_allclose(g,num,rtol=1e-6,atol=1e-6)

    def test_hessian_matches_gradient_derivative(self):
        _,_,_,x,p=f.design(f.legal_results(self.games,2013));t=np.linspace(-.2,.2,x.shape[1]);H=f.hessian(t,x,p);eps=1e-5
        num=np.column_stack([(f.objective(t+np.eye(len(t))[i]*eps,x,p)[1]-f.objective(t-np.eye(len(t))[i]*eps,x,p)[1])/(2*eps) for i in range(len(t))])
        np.testing.assert_allclose(H,num,rtol=1e-6,atol=1e-6)

    def test_scores_have_no_effect(self):
        g=self.games.copy();g['WScore']=-np.inf;g['LScore']=np.nan
        m,_,_=f.fit_season(g,2013);np.testing.assert_array_equal(m['theta'],self.model['theta'])

    def test_no_score_columns_required(self):
        m,_,_=f.fit_season(self.games[f.INPUTS],2013);np.testing.assert_array_equal(m['theta'],self.model['theta'])

    def test_future_and_postcutoff_rows_ignored(self):
        g=self.games.copy();extra=g.iloc[:1].copy();extra['DayNum']=133;extra['WTeamID']=np.nan
        g.loc[g.Season.ne(2013),'WLoc']='INVALID';g=pd.concat([g,extra],ignore_index=True)
        m,_,_=f.fit_season(g,2013);np.testing.assert_array_equal(m['theta'],self.model['theta'])

    def test_order_invariance(self):
        m,_,_=f.fit_season(self.games.sample(frac=1,random_state=18),2013);np.testing.assert_array_equal(m['theta'],self.model['theta'])

    def test_duplicate_physical_game_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):f.fit_season(pd.concat([self.games,self.games.iloc[:1]]),2013)

    def test_invalid_location_rejected(self):
        g=self.games.copy();g.loc[0,'WLoc']='X'
        with self.assertRaisesRegex(ValueError,'location'):f.fit_season(g,2013)

    def test_self_game_rejected(self):
        g=self.games.copy();g.loc[0,'LTeamID']=g.loc[0,'WTeamID']
        with self.assertRaisesRegex(ValueError,'Self'):f.fit_season(g,2013)

    def test_fractional_identifiers_rejected(self):
        g=self.games.copy().astype({'WTeamID':float});g.loc[0,'WTeamID']+=.5
        with self.assertRaisesRegex(ValueError,'integer'):f.fit_season(g,2013)

    def test_unknown_season_rejected(self):
        with self.assertRaisesRegex(ValueError,'2013'):f.fit_season(self.games,2026)

    def test_undefeated_team_has_finite_rating(self):
        g=pd.DataFrame({'Season':[2013]*12,'DayNum':range(1,13),'WTeamID':[1]*12,'LTeamID':[2,3]*6,'WLoc':['N']*12})
        m,team,d=f.fit_season(g,2013);self.assertTrue(np.isfinite(m['theta']).all());self.assertGreater(team.iloc[0].bt_ability,0)

    def test_neutral_only_home_effect_zero(self):
        g=self.games.copy();g['WLoc']='N';m,_,_=f.fit_season(g,2013);self.assertEqual(m['theta'][-1],0.)

    def test_abilities_centered_by_prior(self):
        self.assertLess(abs(sum(self.model['theta'][:-1])),1e-8)

    def test_covariance_certificate(self):
        _,_,_,x,p=f.design(f.legal_results(self.games,2013));H=f.hessian(np.array(self.model['theta']),x,p)
        np.testing.assert_allclose(H@np.array(self.model['covariance']),np.eye(len(H)),atol=1e-10)

    def test_pair_variance_includes_covariance(self):
        _,d,_=f.pair_candidates(self.model,self.pairs);v=np.array(self.model['covariance'])
        self.assertAlmostEqual(d.pair_variance.iloc[0],v[0,0]+v[1,1]-2*v[0,1],places=14)

    def test_team_swap_antisymmetric(self):
        x,_,_=f.pair_candidates(self.model,self.pairs);p=self.pairs.copy();p[['Team1ID','Team2ID']]=p[['Team2ID','Team1ID']]
        rev,_,_=f.pair_candidates(self.model,p);np.testing.assert_allclose(x[f.ABILITY+f.UNCERTAINTY],-rev[f.ABILITY+f.UNCERTAINTY],atol=1e-12)

    def test_zero_variance_no_correction(self):
        c,e=f.uncertainty_features(np.array([-4.,0,3]),np.zeros(3));np.testing.assert_allclose(c,0,atol=1e-13)

    def test_zero_difference_no_correction(self):
        c,_=f.uncertainty_features(np.zeros(3),np.array([.1,1,3]));np.testing.assert_array_equal(c,0)

    def test_uncertainty_attenuates_magnitude(self):
        d=np.array([-2.,-1.,1.,2.]);c,_=f.uncertainty_features(d,np.ones(4));self.assertTrue((np.abs(d+c)<np.abs(d)).all())

    def test_invalid_variance_rejected(self):
        with self.assertRaisesRegex(ValueError,'variance'):f.uncertainty_features([1.],[-1.])

    def test_unknown_pair_team_rejected(self):
        p=self.pairs.copy();p.loc[0,'Team1ID']=999
        with self.assertRaisesRegex(ValueError,'no legal rating'):f.pair_candidates(self.model,p)

    def test_wrong_population_rejected(self):
        p=self.pairs.copy();p['Gender']='W'
        with self.assertRaisesRegex(ValueError,'population'):f.pair_candidates(self.model,p)

    def test_builds_all_pairs_without_labels(self):
        x,d,s=f.build_matchups(self.bases[0],self.model,self.team)
        self.assertEqual(len(x),66);self.assertNotIn('y',x);self.assertFalse(s['labels_used_to_build_pairs'])

    def test_disconnected_seeded_components_stop(self):
        team=self.team.copy();team.loc[0,'component']=99
        with self.assertRaisesRegex(ValueError,'disconnected'):f.build_matchups(self.bases[0],self.model,team)

    def test_missing_seeded_team_stops(self):
        with self.assertRaisesRegex(ValueError,'absent'):f.build_matchups(self.bases[0],self.model,self.team.iloc[1:])

    def test_reference_columns_retained_exactly(self):
        self.assertEqual(f.RECIPES['anchor'],w.sf.ANCHOR_COLS);self.assertEqual([len(v) for v in f.RECIPES.values()],[16,17,18])

    def test_no_validation_selected_features(self):
        self.assertEqual(f.registry().new_candidate.sum(),2);self.assertEqual(f.PARAMETERS['team_prior_sd'],2.)

    def test_nonconvergence_stops(self):
        from scipy.optimize import OptimizeResult
        with patch.object(f,'minimize',return_value=OptimizeResult(x=np.zeros(13),success=False,message='test',nit=1,fun=100)):
            with self.assertRaisesRegex(ValueError,'optimizer failed'):f.fit_season(self.games,2013)


class IOandDecisions(unittest.TestCase):
    def test_legacy_sparse_metrics_recomputed(self):
        p=np.array([.2,.8]);y=np.array([0,1]);m=normalize_metric({'brier':.04},y,p,'M',2016)
        self.assertAlmostEqual(m['log_loss'],-np.log(.8));self.assertEqual(m['Gender'],'M')

    def test_inconsistent_saved_diagnostic_stops(self):
        with self.assertRaisesRegex(ValueError,'log loss'):normalize_metric({'brier':.04,'log_loss':100},np.array([0,1]),np.array([.2,.8]),'M',2016)

    def test_metric_identity_mismatch_stops(self):
        with self.assertRaisesRegex(ValueError,'identity'):normalize_metric({'brier':.04,'Gender':'W'},np.array([0,1]),np.array([.2,.8]),'M',2016)

    def test_primary_not_replaced_by_secondary(self):
        e=pd.DataFrame([{'Season':s,'comparison':c,'delta_brier':v} for s in w.SEASONS for c,v in [(w.CONFIG['primary'],.005),(w.CONFIG['secondary'],-.005)]])
        d=w.decisions(e)['decisions'];self.assertEqual(d[0]['decision'],'DO_NOT_EXPAND_AUTOMATICALLY');self.assertEqual(d[1]['decision'],'CONSIDER_UNCHANGED_LATER_ERA_TEST')

    def test_gate_requires_three_seasons(self):
        e=pd.DataFrame([{'Season':s,'comparison':c,'delta_brier':v} for s,v in zip(w.SEASONS,[-.01,-.01,.001,.001]) for c in [w.CONFIG['primary'],w.CONFIG['secondary']]])
        self.assertEqual(w.decisions(e)['decisions'][0]['decision'],'DO_NOT_EXPAND_AUTOMATICALLY')

    def test_incomplete_gate_stops(self):
        e=pd.DataFrame([{'Season':2016,'comparison':w.CONFIG['primary'],'delta_brier':-.01}])
        with self.assertRaisesRegex(ValueError,'Incomplete'):w.decisions(e)

    def test_output_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'target').write_text('private');(p/'bad').symlink_to(p/'target')
            with self.assertRaises(ValueError):w.atomic_json(p/'bad',{})

    def test_checkpoint_corruption_stops(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);w.atomic_json(p/'a.json',{});w.seal(p,['a.json']);(p/'a.json').write_text('changed')
            with self.assertRaisesRegex(ValueError,'Corrupt'):w.checkpoint(p,['a.json'])

    def test_missing_checkpoint_is_not_valid(self):
        with tempfile.TemporaryDirectory() as t:self.assertFalse(w.checkpoint(Path(t),['a']))

    def test_return_source_hashes_match(self):
        p=ROOT/'evidence/round09';m=w.read_json(p/'return_integrity.json')['sha256']
        self.assertTrue(all(w.sha(p/n)==h for n,h in m.items()))

    def test_notebook_has_no_styler_or_control_characters(self):
        n=json.loads((ROOT/'10_mens_win_strength.ipynb').read_text())
        self.assertEqual(sum(c['cell_type']=='code' for c in n['cells']),9)
        for c in n['cells']:
            text=''.join(c['source']);self.assertNotIn('.style',text)
            self.assertFalse(any(ord(ch)<32 and ch not in '\n\t\r' for ch in text))


class Integration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.args,self.head=build_fixture(Path(self.tmp.name))
        self.patch=patch.object(w.rf,'EXPECTED_SHA',self.head);self.patch.start()
        self.quiet=contextlib.redirect_stdout(io.StringIO());self.quiet.__enter__()
    def tearDown(self):
        self.quiet.__exit__(None,None,None);self.patch.stop();self.tmp.cleanup()
    def ctx(self):return w.preflight(**self.args)

    def test_complete_pipeline_resumes_without_fitting(self):
        ctx=self.ctx();w.prepare(ctx);w.evaluate(ctx);w.report(ctx)
        out=ctx['directory'];self.assertEqual(w.read_json(out/'prepare.json')['new_rating_fits'],7)
        self.assertEqual(w.read_json(out/'evaluation_receipt.json')['new_classifier_fits'],8)
        before={k:w.sha(p) for k,root in [('repo',self.args['repo'])] for p in root.rglob('*') if p.is_file() for k in [str(p)]}
        with patch.object(w.wf,'fit_season',side_effect=AssertionError('rating retrained')),patch.object(w.rf,'fitted_model',side_effect=AssertionError('classifier retrained')):
            w.prepare(ctx);w.evaluate(ctx);w.report(ctx)
        self.assertEqual(w.read_json(out/'prepare.json')['rating_reuses'],7)
        self.assertEqual(w.read_json(out/'evaluation_receipt.json')['local_reuses'],8)
        self.assertTrue(all(w.sha(Path(p))==h for p,h in before.items()))
        with zipfile.ZipFile(self.args['kit']/'reports/milestone_10_return.zip') as z:
            self.assertNotIn('predictions.csv',z.namelist());self.assertNotIn('team_profiles.csv',z.namelist())
            m=json.loads(z.read('return_integrity.json'));self.assertTrue(all(__import__('hashlib').sha256(z.read(n)).hexdigest()==h for n,h in m['sha256'].items()))
        from strength_plots import figures
        self.assertEqual(len(figures(out,self.args['kit']/'evidence/round09')),10)

    def test_partial_rating_resume(self):
        ctx=self.ctx();original=w.wf.fit_season;count=[0]
        def interrupt(*a,**k):
            count[0]+=1
            if count[0]==3:raise RuntimeError('synthetic interruption')
            return original(*a,**k)
        with patch.object(w.wf,'fit_season',side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError,'interruption'):w.prepare(ctx)
        with patch.object(w.wf,'fit_season',wraps=original) as wrapped:
            w.prepare(ctx);self.assertEqual(wrapped.call_count,5)
        self.assertEqual(w.read_json(ctx['directory']/'prepare.json')['rating_reuses'],2)

    def test_partial_classifier_resume(self):
        ctx=self.ctx();w.prepare(ctx);original=w.rf.fitted_model;count=[0]
        def interrupt(*a,**k):
            count[0]+=1
            if count[0]==3:raise RuntimeError('synthetic interruption')
            return original(*a,**k)
        with patch.object(w.rf,'fitted_model',side_effect=interrupt):
            with self.assertRaisesRegex(RuntimeError,'interruption'):w.evaluate(ctx)
        with patch.object(w.rf,'fitted_model',wraps=original) as wrapped:
            w.evaluate(ctx);self.assertEqual(wrapped.call_count,6)
        self.assertEqual(w.read_json(ctx['directory']/'evaluation_receipt.json')['local_reuses'],2)

    def test_raw_tamper_stops(self):
        p=self.args['repo']/'data/kaggle/raw/MRegularSeasonCompactResults.csv';p.write_text(p.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'Raw'):self.ctx()

    def test_environment_mismatch_stops(self):
        with patch.object(w,'environment',return_value={}):
            with self.assertRaisesRegex(ValueError,'Environment'):self.ctx()

    def test_code_tamper_stops(self):
        p=self.args['kit']/'win_strength_features.py';p.write_text(p.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'source/evidence'):self.ctx()

    def test_missing_anchor_cache_stops(self):
        c=w.read_json(self.args['kit']/'constraints.json');p=self.args['possession']/'private_runs'/c['fingerprints']['possession']/'fits/M_2016_anchor/complete.json';p.unlink()
        with self.assertRaisesRegex(ValueError,'Missing reference'):self.ctx()

    def test_corrupt_upstream_anchor_stops(self):
        c=w.read_json(self.args['kit']/'constraints.json');p=self.args['possession']/'private_runs'/c['fingerprints']['possession']/'fits/M_2016_anchor/model.json';p.write_text('{}')
        with self.assertRaisesRegex(ValueError,'Corrupt'):self.ctx()

    def test_unexpected_tracked_source_edit_stops(self):
        (self.args['repo']/'src/value.py').write_text('VALUE=2\n')
        with self.assertRaisesRegex(ValueError,'tracked changes'):self.ctx()

    def test_missing_preparation_stops_evaluation(self):
        ctx=self.ctx()
        with self.assertRaises(ValueError):w.evaluate(ctx)

    def test_corrupt_new_rating_stops_reuse(self):
        ctx=self.ctx();w.prepare(ctx);(ctx['directory']/'ratings/M_2013/rating_model.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Corrupt'):w.prepare(ctx)

    def test_corrupt_new_classifier_stops_reuse(self):
        ctx=self.ctx();w.prepare(ctx);w.evaluate(ctx);(ctx['directory']/'fits/M_2016_anchor_bt/model.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Corrupt'):w.evaluate(ctx)

    def test_budget_prevents_fit(self):
        ctx=self.ctx();w.prepare(ctx)
        with patch.object(w.rf,'fitted_model',side_effect=AssertionError('Should not fit')):
            with self.assertRaisesRegex(ValueError,'budget'):w.obtain(ctx,2016,'anchor_bt',w.matrices(ctx),0)


class Supervisor(unittest.TestCase):
    def setup_runner(self, root, body):
        root=Path(root);shutil.copy2(ROOT/'run_round10.py',root/'run_round10.py');(root/'strength_workflow.py').write_text(body);return root

    def test_hard_timeout(self):
        with tempfile.TemporaryDirectory() as t:
            p=self.setup_runner(t,'import time\ntime.sleep(30)\n')
            r=subprocess.run([sys.executable,str(p/'run_round10.py'),'prepare','--max-seconds','1'],capture_output=True,timeout=8)
            self.assertNotEqual(r.returncode,0);self.assertEqual(json.loads((p/'reports/failure.json').read_text())['status'],'TIME_LIMIT')

    def test_concurrent_run_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=self.setup_runner(t,'print("not launched")\n');(p/'reports').mkdir()
            with (p/'reports/execution.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                r=subprocess.run([sys.executable,str(p/'run_round10.py'),'prepare'],capture_output=True,timeout=8)
                self.assertNotEqual(r.returncode,0);self.assertIn(b'Another stage',r.stderr)

    def test_invalid_limit_rejected(self):
        import run_round10 as r
        with self.assertRaises(ValueError):r.run_stage('prepare',max_seconds=301)

if __name__=='__main__':unittest.main()
