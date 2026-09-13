from __future__ import annotations
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

KIT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(KIT));sys.path.insert(0,str(Path(__file__).resolve().parent))
import shot_features as sf
import research_workflow as rw
from fixtures import data,write_fixture


class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compact,cls.detail,cls.seeds,cls.targets=data([2018,2019])
        cls.snapshot,cls.audit=sf.build_snapshot(cls.compact,cls.detail,cls.seeds,'M',2019)
        cls.pairs,cls.y=sf.tournament_pairs(cls.targets,'M',[2019])
        cls.features=sf.pair_features(cls.snapshot,cls.pairs)

    def test_candidate_count_and_control(self):
        self.assertEqual(len(sf.ANCHOR_COLS),16);self.assertEqual(len(sf.ALL_FEATURES),30)
        self.assertEqual(len(sf.RESIDUAL_COLS)+len(sf.PROFILE_COLS),14)
        self.assertEqual(len(set(sf.ALL_FEATURES)),30)

    def test_features_are_finite(self):
        self.assertTrue(np.isfinite(self.features[sf.ALL_FEATURES]).all().all())

    def test_all_swap_parities(self):
        swapped=self.pairs.rename(columns={'Team1ID':'Team2ID','Team2ID':'Team1ID'})
        reverse=sf.pair_features(self.snapshot,swapped)
        np.testing.assert_allclose(self.features[sf.ALL_FEATURES],-reverse[sf.ALL_FEATURES],atol=1e-12)

    def test_pair_function_rejects_labels(self):
        bad=self.pairs.copy();bad['y']=self.y
        with self.assertRaisesRegex(ValueError,'Labels'):sf.pair_features(self.snapshot,bad)

    def test_current_and_future_target_labels_not_feature_inputs(self):
        # The snapshot API has no target argument; poisoning all separate target rows changes nothing.
        target=self.targets.copy();target[['WScore','LScore']]=[999,0]
        new,_=sf.build_snapshot(self.compact,self.detail,self.seeds,'M',2019)
        pd.testing.assert_frame_equal(self.snapshot,new)

    def test_post_cutoff_poison_ignored(self):
        c=self.compact.iloc[[0]].copy();c['Season']=2019;c['DayNum']=133;c['WScore']=-99
        d=self.detail.iloc[[0]].copy();d['Season']=2019;d['DayNum']=133;d['WFGM']=-99
        new,_=sf.build_snapshot(pd.concat([self.compact,c]),pd.concat([self.detail,d]),self.seeds,'M',2019)
        pd.testing.assert_frame_equal(self.snapshot,new)

    def test_future_regular_season_poison_ignored(self):
        c=self.compact.iloc[[0]].copy();c['Season']=2026;c['WScore']=-99
        d=self.detail.iloc[[0]].copy();d['Season']=2026;d['WFGM']=-99
        new,_=sf.build_snapshot(pd.concat([self.compact,c]),pd.concat([self.detail,d]),self.seeds,'M',2019)
        pd.testing.assert_frame_equal(self.snapshot,new)

    def test_shuffle_invariance(self):
        new,_=sf.build_snapshot(self.compact.sample(frac=1,random_state=3),self.detail.sample(frac=1,random_state=5),
                                self.seeds.sample(frac=1,random_state=7),'M',2019)
        pd.testing.assert_frame_equal(self.snapshot,new)

    def test_duplicate_physical_game_rejected(self):
        d=self.detail.loc[self.detail.Season==2019]
        with self.assertRaisesRegex(ValueError,'Duplicate physical'):sf.legal_games(pd.concat([d,d.iloc[[0]]]),2019,detailed=True)

    def test_impossible_two_point_shooting_rejected(self):
        d=self.detail.copy();mask=d.Season==2019;idx=d.index[mask][0]
        d.loc[idx,'WFGA3']=d.loc[idx,'WFGA']
        with self.assertRaisesRegex(ValueError,'two-point'):sf.legal_games(d,2019,detailed=True)

    def test_detailed_compact_disagreement(self):
        c=self.compact.copy();idx=c.index[c.Season==2019][0];c.loc[idx,'WScore']+=1
        with self.assertRaisesRegex(ValueError,'disagree'):sf.build_snapshot(c,self.detail,self.seeds,'M',2019)

    def test_duplicate_seeds_rejected(self):
        s=pd.concat([self.seeds,self.seeds.loc[self.seeds.Season==2019].iloc[[0]]])
        with self.assertRaisesRegex(ValueError,'Duplicate seed'):sf.build_snapshot(self.compact,self.detail,s,'M',2019)

    def test_bad_seed_rejected(self):
        s=self.seeds.copy();s.loc[s.Season==2019,'Seed']='bad'
        with self.assertRaisesRegex(ValueError,'Invalid seed'):sf.build_snapshot(self.compact,self.detail,s,'M',2019)

    def test_missing_seed_rejected(self):
        s=self.snapshot.copy();s.loc[s.TeamID==self.pairs.Team1ID.iloc[0],'seed']=np.nan
        with self.assertRaisesRegex(ValueError,'Missing team'):sf.pair_features(s,self.pairs)

    def test_inadequate_coverage_rejected(self):
        s=self.snapshot.copy();s['detailed_coverage']=.2
        with self.assertRaisesRegex(ValueError,'coverage'):sf.pair_features(s,self.pairs)

    def test_opponent_exclusion_includes_repeat_meetings_and_prior(self):
        long=sf.long_games(sf.legal_games(self.detail,2019,detailed=True),detailed=True)
        _,before=sf.opponent_residuals(long)
        a,b=int(long.TeamID.iloc[0]),int(long.OpponentID.iloc[0])
        mod=long.copy()
        m=(mod.TeamID==b)&(mod.OpponentID==a)
        rev=(mod.TeamID==a)&(mod.OpponentID==b)
        mod.loc[m,'FGM3']+=1;mod.loc[rev,'opp_FGM3']+=1
        _,after=sf.opponent_residuals(mod)
        # All same-opponent meetings must have the same excluded baseline, unaffected by those makes.
        np.testing.assert_allclose(before.loc[rev,'three_expected_pct'],after.loc[rev,'three_expected_pct'],atol=1e-12)
        self.assertGreater(after.loc[rev,'three_residual_makes'].sum(),before.loc[rev,'three_residual_makes'].sum())

    def test_zero_three_attempts_finite(self):
        long=sf.long_games(sf.legal_games(self.detail,2019,detailed=True),detailed=True)
        long[['FGM3','FGA3','opp_FGM3','opp_FGA3']]=0
        residual,_=sf.opponent_residuals(long)
        self.assertTrue(np.isfinite(residual.select_dtypes('number')).all().all())

    def test_zero_opportunity_rate_fit_stops(self):
        long=sf.long_games(sf.legal_games(self.detail,2019,detailed=True),detailed=True)
        with self.assertRaisesRegex(ValueError,'positive-opportunity'):
            sf.additive_fit(long,np.full(len(long),np.nan),np.zeros(len(long)))

    def test_target_year_firewall(self):
        with self.assertRaisesRegex(ValueError,'2022'):sf.tournament_pairs(self.targets,'M',[2026])

    def test_main_draw_filter(self):
        extra=self.targets.iloc[[0]].copy();extra['DayNum']=134
        pairs,_=sf.tournament_pairs(pd.concat([self.targets,extra]),'M',[2019])
        self.assertEqual(len(pairs),len(self.pairs))

    def test_registry_has_temporal_contract(self):
        r=sf.feature_registry();self.assertEqual(int(r.new_candidate.sum()),14)
        self.assertTrue((r.swap_parity==-1).all());self.assertFalse(r.tournament_labels_used.any())


class ModelTests(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(42)
        self.x=pd.DataFrame(rng.normal(size=(90,3)),columns=['a','b','c'])
        self.y=(self.x.a+self.x.b+rng.normal(size=90)>0).to_numpy(dtype=int)

    def test_probability_complement(self):
        m=rw.fitted_model(self.x,self.y,list(self.x))
        np.testing.assert_allclose(rw.predict(m,self.x)+rw.predict(m,-self.x),1.,atol=1e-12)

    def test_model_deterministic(self):
        a=rw.fitted_model(self.x,self.y,list(self.x));b=rw.fitted_model(self.x,self.y,list(self.x))
        self.assertEqual(a,b)

    def test_training_only_constant_screen(self):
        x=self.x.copy();x['constant']=0
        m=rw.fitted_model(x,self.y,list(x));self.assertEqual(m['removed_training_constant'],['constant'])
        v=x.copy();v['constant']=1000
        np.testing.assert_allclose(rw.predict(m,x),rw.predict(m,v))

    def test_temporal_splits(self):
        f=pd.DataFrame({'Season':[2013,2014,2015,2016,2017]})
        tr,va=rw.split_indices(f,2016)
        self.assertEqual(f.iloc[tr].Season.max(),2015);self.assertEqual(len(va),1)

    def test_short_history_stops(self):
        with self.assertRaisesRegex(ValueError,'three prior'):
            rw.split_indices(pd.DataFrame({'Season':[2013,2014,2015]}),2015)

    def test_invalid_class_values_stop(self):
        y=self.y.copy();y[0]=2
        with self.assertRaisesRegex(ValueError,'both classes'):rw.fitted_model(self.x,y,list(self.x))

    def test_game_weighted_combined_brier(self):
        frame=pd.DataFrame([{'Gender':'M','recipe':'anchor','Season':2019,'games':5,'brier':.1,'delta_vs_anchor':0},
                            {'Gender':'W','recipe':'anchor','Season':2019,'games':15,'brier':.3,'delta_vs_anchor':0}])
        combined=rw.aggregate(frame).query("Gender=='combined'").iloc[0]
        self.assertAlmostEqual(combined.game_weighted_brier,.25)

    def test_conditional_ablation_sign(self):
        f=pd.DataFrame([dict(Gender='M',Season=2019,recipe=r,brier=v) for r,v in
                        [('anchor',.2),('anchor_residual',.19),('anchor_profile',.18),('anchor_both',.17)]])
        a=rw.ablation_effects(f).set_index('comparison')
        self.assertAlmostEqual(a.loc['residual_given_profile','delta_brier'],-.01)
        self.assertAlmostEqual(a.loc['profile_given_residual','delta_brier'],-.02)


class WorkflowTests(unittest.TestCase):
    def test_checkpoint_corruption_detected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'x.csv').write_text('a\n1\n');rw.finish_checkpoint(p,['x.csv'])
            self.assertTrue(rw.checkpoint_ok(p/'complete.json'))
            (p/'x.csv').write_text('changed')
            with self.assertRaisesRegex(ValueError,'Corrupt checkpoint'):rw.checkpoint_ok(p/'complete.json')

    def test_resume_preservation_and_eight_smoke_fits(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);repo=root/'repo';repo.mkdir();kit=root/'kit';kit.mkdir()
            for name in ['shot_features.py','research_workflow.py','run_round02.py']:
                shutil.copy(KIT/name,kit/name)
            head=write_fixture(repo,kit)
            raw_before={p.name:rw.sha(p) for p in (repo/'data/kaggle/raw').glob('*.csv')}
            with patch.object(rw,'EXPECTED_SHA',head),contextlib.redirect_stdout(io.StringIO()):
                ctx=rw.preflight(kit,repo)
                original=pd.read_csv;reads=[]
                def reader(p,*args,**kw):reads.append(str(p));return original(p,*args,**kw)
                with patch.object(rw.pd,'read_csv',side_effect=reader):rw.prepare(ctx,'smoke')
                self.assertFalse(any('NCAATourneyCompactResults' in p for p in reads))
                rw.evaluate(ctx,'smoke')
                first=json.loads((ctx['directory']/'smoke_summary.json').read_text())
                self.assertEqual(first['new_tournament_classifier_fits'],8)
                rw.prepare(ctx,'smoke');rw.evaluate(ctx,'smoke');rw.final_preservation(repo,ctx)
                resumed=json.loads((ctx['directory']/'smoke_summary.json').read_text())
                self.assertEqual(resumed['new_tournament_classifier_fits'],0)
                self.assertEqual(resumed['reused_tournament_classifier_fits'],8)
                summary=json.loads((ctx['directory']/'prepare_smoke.json').read_text())
                self.assertEqual(summary['new_snapshots'],0);self.assertEqual(summary['reused_snapshots'],14)
            self.assertEqual(raw_before,{p.name:rw.sha(p) for p in (repo/'data/kaggle/raw').glob('*.csv')})

    def test_new_unreviewed_source_change_stops(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);repo=root/'repo';repo.mkdir();kit=root/'kit';kit.mkdir()
            head=write_fixture(repo,kit)
            (repo/'.gitignore').write_text('changed')
            with patch.object(rw,'EXPECTED_SHA',head):
                with self.assertRaisesRegex(ValueError,'Unexpected tracked'):rw.repository_state(repo)

    def test_raw_hash_mismatch_stops(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);repo=root/'repo';repo.mkdir();kit=root/'kit';kit.mkdir()
            head=write_fixture(repo,kit)
            p=repo/'data/kaggle/raw/MNCAATourneySeeds.csv';p.write_text(p.read_text()+'\n')
            with patch.object(rw,'EXPECTED_SHA',head),contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(ValueError,'Raw snapshot changed'):rw.preflight(kit,repo)

    def test_supervisor_hard_timeout(self):
        with tempfile.TemporaryDirectory() as t:
            kit=Path(t);shutil.copy(KIT/'run_round02.py',kit/'run_round02.py')
            (kit/'research_workflow.py').write_text('import time\nprint("test started",flush=True)\ntime.sleep(30)\n')
            p=subprocess.run([sys.executable,str(kit/'run_round02.py'),'prepare','--max-seconds','1'],capture_output=True,timeout=10)
            self.assertNotEqual(p.returncode,0)
            self.assertEqual(json.loads((kit/'reports/failure.json').read_text())['status'],'TIME_LIMIT')

if __name__=='__main__':unittest.main()
