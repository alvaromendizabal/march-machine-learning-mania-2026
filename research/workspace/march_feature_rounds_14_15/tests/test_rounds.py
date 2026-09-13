from pathlib import Path
import copy,hashlib,json,os,sys,tempfile,unittest,zipfile,subprocess
from unittest.mock import patch
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import feature_rounds as fr
import round_workflow as w
from research_io import rf,sf
import consensus_reference as cf
from fixtures import build_fixture,write_manifest


def rank_input():
    n=60;ids=np.arange(1101,1101+n)
    base=pd.DataFrame({'Gender':'M','Season':2025,'TeamID':ids,'seed':[1.,2.,3.,4.]+[np.nan]*(n-4),
                       'strength':np.linspace(-10,20,n),'adj_offense':np.linspace(-8,15,n),'adj_defense':np.linspace(-3,8,n)})
    panel=pd.DataFrame([{'Season':2025,'RankingDayNum':128,'SystemName':s,'TeamID':int(t),'OrdinalRank':int(i+1)}
                       for s in ['A','B','C'] for i,t in enumerate(ids)])
    # Use a realistic full-publication denominator with top-rank clipping.
    panel.loc[panel.TeamID==ids[-1],'OrdinalRank']=365
    panel,_=cf.publication_panel(panel,2025)
    pairs=pd.DataFrame([(1101,1102),(1101,1103),(1103,1104)],columns=['Team1ID','Team2ID'])
    pairs.insert(0,'Season',2025);pairs.insert(0,'Gender','M')
    for i,c in enumerate(fr.BASE):pairs[c]=np.array([.2,.4,.3])*(i+1)
    st=panel.groupby('TeamID').percentile.median();from scipy.special import logit
    pairs[cf.CONSENSUS]=logit(st.loc[pairs.Team1ID].clip(.01,.99).to_numpy())-logit(st.loc[pairs.Team2ID].clip(.01,.99).to_numpy())
    return base,panel,pairs


def context_input():
    _,_,p=rank_input();rows=[]
    for t in [1101,1102,1103,1104]:
        for opp in [1150,1151]:
            for h in [-1,1]:rows.append({'Season':2025,'TeamID':t,'OpponentID':opp,'home':h,
                'margin':float(t-1100+h),'win':.5+.05*(t-1100),'offense':100.+t-1100,
                'defense':-110.+t-1100,'games':2,'last_day':130,'detail_games':2})
    return pd.DataFrame(rows),p

class FeatureTests(unittest.TestCase):
    def test_four_each(self):
        self.assertEqual([len(fr.FEATURES[r]) for r in ['14','15']],[4,4])
    def test_same_arms_and_volume(self):
        for r in ['14','15']:self.assertEqual([len(c) for c in fr.recipes(r).values()],[17,19,19,21,21])
    def test_ranking_finite(self):
        b,p,x=rank_input();y,*_=fr.ranking_features(b,p,x);self.assertTrue(np.isfinite(y[fr.FEATURES['14']]).all().all())
    def test_top_ranks_separated(self):
        b,p,x=rank_input();y,*_=fr.ranking_features(b,p,x)
        self.assertEqual(x[cf.CONSENSUS].iloc[0],0.);self.assertNotEqual(y[fr.FEATURES['14'][0]].iloc[0],0.)
    def test_ranking_swap(self):
        b,p,x=rank_input();y,*_=fr.ranking_features(b,p,x);rev=x.copy();rev[['Team1ID','Team2ID']]=rev[['Team2ID','Team1ID']].to_numpy();rev[fr.BASE]=-rev[fr.BASE]
        z,*_=fr.ranking_features(b,p,rev);np.testing.assert_allclose(y[fr.FEATURES['14']],-z[fr.FEATURES['14']],atol=1e-12)
    def test_ranking_order_invariant(self):
        b,p,x=rank_input();a=fr.ranking_features(b,p,x)[0];z=fr.ranking_features(b.sample(frac=1,random_state=1),p.sample(frac=1,random_state=2),x)[0]
        pd.testing.assert_frame_equal(a,z)
    def test_ranking_illegal_date(self):
        b,p,x=rank_input();p.loc[0,'RankingDayNum']=150
        with self.assertRaises(ValueError):fr.ranking_features(b,p,x)
    def test_ranking_mixed_edition(self):
        b,p,x=rank_input();p.loc[0,'RankingDayNum']=124
        with self.assertRaises(ValueError):fr.ranking_features(b,p,x)
    def test_ranking_duplicate(self):
        b,p,x=rank_input()
        with self.assertRaises(ValueError):fr.ranking_features(b,pd.concat([p,p.iloc[:1]]),x)
    def test_missing_seeded_rank(self):
        b,p,x=rank_input();p=p.loc[p.TeamID!=1101]
        with self.assertRaises(ValueError):fr.ranking_features(b,p,x)
    def test_mapping_support(self):
        b,p,x=rank_input()
        with self.assertRaises(ValueError):fr.ranking_features(b.iloc[:4],p,x)
    def test_nonfinite_cardinal(self):
        b,p,x=rank_input();b.loc[0,'strength']=np.inf
        with self.assertRaises(ValueError):fr.ranking_features(b,p,x)
    def test_consensus_control_drift(self):
        b,p,x=rank_input();x.loc[0,cf.CONSENSUS]+=.01
        with self.assertRaises(ValueError):fr.ranking_features(b,p,x)
    def test_quantile_mapping_affine(self):
        b,p,x=rank_input();a=fr.ranking_features(b,p,x)[0];b.strength=2*b.strength+8;z=fr.ranking_features(b,p,x)[0]
        np.testing.assert_allclose(z.rank_mapped_margin_gap,2*a.rank_mapped_margin_gap,atol=1e-12)
    def test_no_tournament_argument(self):
        import inspect
        for fn in [fr.ranking_features,fr.common_context_table,fr.opponent_features]:self.assertNotIn('labels',inspect.signature(fn).parameters)
    def test_context_finite(self):
        c,p=context_input();x,*_=fr.opponent_features(c,p);self.assertTrue(np.isfinite(x[fr.FEATURES['15']]).all().all())
    def test_context_swap(self):
        c,p=context_input();a=fr.opponent_features(c,p)[0];rev=p.copy();rev[['Team1ID','Team2ID']]=rev[['Team2ID','Team1ID']].to_numpy();rev[fr.BASE]=-rev[fr.BASE]
        b=fr.opponent_features(c,rev)[0];np.testing.assert_allclose(a[fr.FEATURES['15']],-b[fr.FEATURES['15']],atol=1e-12)
    def test_context_order_invariant(self):
        c,p=context_input();a=fr.opponent_features(c,p)[0];b=fr.opponent_features(c.sample(frac=1,random_state=8),p)[0]
        pd.testing.assert_frame_equal(a,b)
    def test_exact_shrinkage(self):
        c,p=context_input();x,_,_,support=fr.opponent_features(c,p)
        self.assertEqual(support.matched_compact_opponents.iloc[0],2)
        self.assertAlmostEqual(x.common_venue_margin_gap.iloc[0],-2/6)
    def test_no_overlap_zero_not_missing(self):
        c,p=context_input();c.loc[c.TeamID==1101,'OpponentID']+=10
        x,_,_,s=fr.opponent_features(c,p);self.assertEqual(s.matched_compact_opponents.iloc[0],0)
        np.testing.assert_array_equal(x[fr.FEATURES['15']].iloc[0],np.zeros(4))
    def test_different_venue_not_matched(self):
        c,p=context_input();c=c.loc[((c.TeamID==1101)&(c.home==1))|((c.TeamID!=1101)&(c.home==-1))]
        x,_,_,s=fr.opponent_features(c,p);self.assertEqual(s.matched_compact_opponents.iloc[0],0)
    def test_missing_detail_separate_support(self):
        c,p=context_input();c.loc[c.TeamID==1101,['offense','defense']]=np.nan
        x,_,_,s=fr.opponent_features(c,p);self.assertEqual(s.matched_detailed_opponents.iloc[0],0)
        self.assertEqual(s.matched_compact_opponents.iloc[0],2);self.assertEqual(x.common_venue_offense_gap.iloc[0],0.)
    def test_defense_sign(self):
        c,p=context_input();x,*_=fr.opponent_features(c,p);self.assertLess(x.common_venue_defense_gap.iloc[0],0)
    def test_compact_detailed_duplicate_context(self):
        c,p=context_input()
        with self.assertRaises(ValueError):fr.opponent_features(pd.concat([c,c.iloc[:1]]),p)
    def test_self_opponent_rejected(self):
        c,p=context_input();c.loc[0,'OpponentID']=c.loc[0,'TeamID']
        with self.assertRaises(ValueError):fr.opponent_features(c,p)
    def test_future_context_stops(self):
        c,p=context_input();c.loc[0,'last_day']=133
        with self.assertRaises(ValueError):fr.opponent_features(c,p)
    def test_nonbinary_win_stops(self):
        c,p=context_input();c.loc[0,'win']=2
        with self.assertRaises(ValueError):fr.opponent_features(c,p)
    def test_duplicate_diagnostic_copies(self):
        b,p,x=rank_input();x=fr.ranking_features(b,p,x)[0];out=fr.finish_features(x,'14')
        for f in fr.DUPLICATE:np.testing.assert_array_equal(out[f],out[cf.CONSENSUS])
    def test_registry_no_count_inflation(self):
        for r in ['14','15']:self.assertEqual(int(fr.registry(r).new_candidate.sum()),4)
    def test_pair_id_fraction_rejected(self):
        b,p,x=rank_input();x['Team1ID']=x.Team1ID+.5
        with self.assertRaises(ValueError):fr.ranking_features(b,p,x)
    def test_labels_not_mutated(self):
        b,p,x=rank_input();copyx=x.copy(deep=True);fr.ranking_features(b,p,x);pd.testing.assert_frame_equal(x,copyx)
    def test_minute_strength_not_fitted(self):
        b,p,x=rank_input()
        with patch.object(sf,'compact_strength',side_effect=AssertionError('No rating fits')):fr.ranking_features(b,p,x)

class GateTests(unittest.TestCase):
    def effects(self,d=(-.001,-.002,-.001,.001),du=(-.001,-.001,-.001,-.001)):
        return pd.DataFrame([{'Season':s,'comparison':c,'delta_brier':v} for c,seq in [('both_given_reference',d),('both_given_duplicate',du)] for s,v in zip(fr.VALIDATION,seq)])
    def test_gate_pass(self):self.assertTrue(w.decision(self.effects(),'14')['decision'].startswith('CONSIDER'))
    def test_gate_fail_season_consistency(self):self.assertEqual(w.decision(self.effects(d=(-.004,.001,.001,.001)),'14')['decision'],'DO_NOT_PROMOTE')
    def test_gate_fail_duplicate(self):self.assertEqual(w.decision(self.effects(du=(.001,)*4),'15')['decision'],'DO_NOT_PROMOTE')
    def test_gate_fail_worst(self):self.assertEqual(w.decision(self.effects(d=(-.005,-.005,-.005,.004)),'15')['decision'],'DO_NOT_PROMOTE')
    def test_gate_reject_missing_year(self):
        with self.assertRaises(ValueError):w.decision(self.effects().iloc[1:],'14')
    def test_gate_reject_nan(self):
        e=self.effects();e.loc[0,'delta_brier']=np.nan
        with self.assertRaises(ValueError):w.decision(e,'14')
    def test_round_independence(self):
        self.assertNotIn('round14_results',w.config('15'));self.assertTrue(set(fr.FEATURES['14']).isdisjoint(set(sum(w.config('15')['recipes'].values(),[]))))

class IOTests(unittest.TestCase):
    def test_checkpoint_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);w.atomic_json(p/'a.json',{'x':1});w.seal(p,['a.json']);self.assertTrue(w.checkpoint(p,['a.json']))
            (p/'a.json').write_text('{}')
            with self.assertRaises(ValueError):w.checkpoint(p,['a.json'])
    def test_csv_inference_valid(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.csv';w.atomic_csv(p,pd.DataFrame({'diff_seed':[1.,2.]}));a=w.read_csv(p)
            np.testing.assert_array_equal(a.diff_seed.to_numpy(),[1.,2.])
    def test_metric_missing_logloss(self):
        y=np.array([0,1]);p=np.array([.2,.8]);m=w.normalize_metric({'brier':.04},y,p,'M',2025);self.assertIn('log_loss',m)
    def test_metric_disagreement_rejected(self):
        with self.assertRaises(ValueError):w.normalize_metric({'brier':.04,'log_loss':0},np.array([0,1]),np.array([.2,.8]),'M',2025)
    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'a').write_text('a');(p/'b').symlink_to(p/'a')
            with self.assertRaises(ValueError):w.safe_file(p,'b')
    def test_traversal_input_rejected(self):
        with self.assertRaises(ValueError):w.safe_file(Path('/tmp'),'../etc/passwd')
    def test_stage_seal_corruption(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);w.atomic_json(p/'m.json',{'a':1});w.stage_seal(p,'stage',['m.json']);(p/'m.json').write_text('bad')
            with self.assertRaises(ValueError):w.stage_check(p,'stage',['m.json'])
    def test_runner_bad_round(self):
        from run_round import run_stage
        with self.assertRaises(ValueError):run_stage('16','prepare',1)
    def test_runner_bad_limit(self):
        from run_round import run_stage
        with self.assertRaises(ValueError):run_stage('14','evaluate',999)
    def test_frozen_no_style(self):
        for n in ['14_ranking_resolution.ipynb','15_common_opponents.ipynb']:
            p=Path(__file__).resolve().parents[1]/n
            if p.exists():self.assertNotIn('.style',p.read_text())

class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.args,cls.head=build_fixture(Path(cls.tmp.name))
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_both_rounds_and_reuse(self):
        before={str(p):w.sha(p) for k in ['repo','shooting','rankings','consensus'] for p in self.args[k].rglob('*') if p.is_file()}
        with patch.object(rf,'EXPECTED_SHA',self.head):
            for rid in ['14','15']:
                c=w.preflight(**self.args,round_id=rid);w.prepare(c);w.evaluate(c);w.report(c)
                out=c['directory'];receipt=w.read_json(out/'evaluation_receipt.json')
                self.assertEqual(receipt['new_classifier_fits'],16);self.assertEqual(receipt['total_comparisons'],20)
                hashes={str(p.relative_to(out)):w.sha(p) for p in out.rglob('*') if p.is_file() and ('fits' in p.parts or 'snapshots' in p.parts or 'contexts' in p.parts)}
                w.prepare(c);w.evaluate(c);w.report(c)
                self.assertEqual(w.read_json(out/'evaluation_receipt.json')['new_classifier_fits'],0)
                self.assertEqual(w.read_json(out/'prepare.json')['feature_snapshot_reuses'],12)
                for n,h in hashes.items():self.assertEqual(w.sha(out/n),h)
                self.assertTrue((c['reports']/f'milestone_{rid}_return.zip').exists())
            from package_returns import package
            self.assertTrue(package(self.args['kit']).exists())
        for p,h in before.items():self.assertEqual(w.sha(Path(p)),h)
    def test_changed_environment_stops(self):
        with patch.object(rf,'EXPECTED_SHA',self.head),patch.object(w,'environment',return_value={}):
            with self.assertRaises(ValueError):w.preflight(**self.args,round_id='14')
    def test_future_games_excluded(self):
        raw=self.args['repo']/'data/kaggle/raw';a=w.read_csv(raw/'MRegularSeasonCompactResults.csv');b=w.read_csv(raw/'MRegularSeasonDetailedResults.csv')
        c=fr.common_context_table(a,b,2025);bad=a.iloc[:1].copy();bad.Season=2026;bad.WScore=-9
        d=fr.common_context_table(pd.concat([a,bad]),b,2025);pd.testing.assert_frame_equal(c,d)
    def test_post_cutoff_games_excluded(self):
        raw=self.args['repo']/'data/kaggle/raw';a=w.read_csv(raw/'MRegularSeasonCompactResults.csv');b=w.read_csv(raw/'MRegularSeasonDetailedResults.csv')
        c=fr.common_context_table(a,b,2025);bad=a.iloc[:1].copy();bad.Season=2025;bad.DayNum=150;bad.WScore=-9
        d=fr.common_context_table(pd.concat([a,bad]),b,2025);pd.testing.assert_frame_equal(c,d)
    def test_2021_no_contest_excluded(self):
        raw=self.args['repo']/'data/kaggle/raw';_,_,a=cf.tournament_labels(w.read_csv(raw/'MNCAATourneyCompactResults.csv'),w.read_csv(raw/'MNCAATourneySeeds.csv'),w.read_csv(raw/'MTeams.csv'))
        self.assertEqual(a.query('Season==2021').played_main_draw_games.iloc[0],62)
    def test_expected_later_counts(self):
        raw=self.args['repo']/'data/kaggle/raw';p,_,_=cf.tournament_labels(w.read_csv(raw/'MNCAATourneyCompactResults.csv'),w.read_csv(raw/'MNCAATourneySeeds.csv'),w.read_csv(raw/'MTeams.csv'))
        self.assertEqual([int((p.Season<s).sum()) for s in fr.VALIDATION],[503,566,629,692])



class ExtraContractTests(unittest.TestCase):
    def test_ranking_fractional_rank_stops(self):
        b,p,x=rank_input();p['OrdinalRank']=p.OrdinalRank.astype(float);p.loc[0,'OrdinalRank']=1.5
        with self.assertRaises(ValueError):fr.ranking_features(b,p,x)
    def test_ranking_zero_rank_stops(self):
        b,p,x=rank_input();p.loc[0,'OrdinalRank']=0
        with self.assertRaises(ValueError):fr.ranking_features(b,p,x)
    def test_future_base_season_stops(self):
        b,p,x=rank_input();b['Season']=2026
        with self.assertRaises(ValueError):fr.ranking_features(b,p,x)
    def test_duplicate_pair_stops(self):
        b,p,x=rank_input()
        with self.assertRaises(ValueError):fr.ranking_features(b,p,pd.concat([x,x.iloc[:1]]))
    def test_reference_unchanged_after_builder(self):
        b,p,x=rank_input();y=fr.ranking_features(b,p,x)[0]
        pd.testing.assert_frame_equal(x[fr.BASE],y[fr.BASE])
    def test_pair_context_preserves_order(self):
        c,p=context_input();a=fr.opponent_features(c,p)[0]
        rev=p.iloc[::-1];b=fr.opponent_features(c,rev)[0]
        np.testing.assert_allclose(a[fr.FEATURES['15']].iloc[::-1],b[fr.FEATURES['15']])
    def test_vectorized_context_matches_pairwise_definition(self):
        c,p=context_input();x,*_=fr.opponent_features(c,p)
        for i,row in p.iterrows():
            a=c.loc[c.TeamID==row.Team1ID].drop(columns=['TeamID','Season']);b=c.loc[c.TeamID==row.Team2ID].drop(columns=['TeamID','Season'])
            compact,_=fr.context_contrast(a,b,['margin','win']);detail,_=fr.context_contrast(a,b,['offense','defense'])
            np.testing.assert_allclose(x.loc[i,fr.FEATURES['15']].to_numpy(dtype=float),np.r_[compact,detail])
    def test_prediction_swap_fitted_classifier(self):
        rng=np.random.default_rng(7);x=pd.DataFrame(rng.normal(size=(80,3)),columns=['a','b','c']);y=rng.integers(0,2,80)
        m=rf.fitted_model(x,y,['a','b','c']);np.testing.assert_allclose(rf.predict(m,x)+rf.predict(m,-x),1,atol=1e-14)
    def test_train_only_constant_dropped(self):
        x=pd.DataFrame({'a':np.linspace(-1,1,20),'constant':np.zeros(20)});m=rf.fitted_model(x,np.tile([0,1],10),list(x))
        self.assertEqual(m['removed_training_constant'],['constant'])
    def test_round15_duplicate_source(self):
        c,p=context_input();x=fr.finish_features(fr.opponent_features(c,p)[0],'15')
        for f in fr.DUPLICATE:np.testing.assert_array_equal(x[f],x.diff_strength)
    def test_safe_output_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'real').write_text('keep');(p/'bad.json').symlink_to(p/'real')
            with self.assertRaises(ValueError):w.atomic_json(p/'bad.json',{})
            self.assertEqual((p/'real').read_text(),'keep')
    def test_runner_same_kit_lock(self):
        import fcntl,run_round
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'reports').mkdir()
            with (p/'reports/execution.lock').open('w') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(run_round,'__file__',str(p/'run_round.py')):
                    with self.assertRaises(RuntimeError):run_round.run_stage('15','prepare',1)
    def test_runner_actual_timeout(self):
        import run_round
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'round_workflow.py').write_text('import time\ntime.sleep(20)\n')
            with patch.object(run_round,'__file__',str(p/'run_round.py')):
                with self.assertRaises(TimeoutError):run_round.run_stage('14','prepare',1)
            self.assertTrue((p/'reports/round14/milestone_14_failure.zip').exists())
    def test_package_missing_second_report_stops(self):
        from package_returns import package
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):package(Path(td))

if __name__=='__main__':unittest.main()
