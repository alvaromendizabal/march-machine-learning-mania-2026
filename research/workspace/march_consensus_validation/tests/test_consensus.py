from __future__ import annotations
import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import consensus_features as f
import consensus_workflow as w
from research_io import sf,rf
from fixtures import toy_data,build_fixture,write_manifest

class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,cls.d,cls.s,cls.y,cls.names,cls.r=toy_data()
        cls.games,cls.long=f.reference_inputs(cls.c,cls.d,2022)
        cls.strength=sf.compact_strength(cls.games);cls.shoot=sf.standard_control(cls.long)
        cls.base=f.finish_reference(cls.strength,cls.shoot,cls.long,cls.s,2022)
        cls.panel,_=f.publication_panel(cls.r,2022)
    def test_only_two_recipes(self):
        self.assertEqual([len(v) for v in f.RECIPES.values()],[16,17]);self.assertEqual(set(f.ALL)-set(f.BASE),{f.CONSENSUS})
    def test_later_years_explicit(self):self.assertEqual(f.VALIDATION,[2022,2023,2024,2025]);self.assertNotIn(2020,f.YEARS);self.assertNotIn(2026,f.YEARS)
    def test_future_games_excluded(self):
        bad=self.c.iloc[:1].copy();bad['Season']=2026;bad['WScore']=-1
        g,_=f.reference_inputs(pd.concat([self.c,bad]),self.d,2022);pd.testing.assert_frame_equal(g,self.games)
    def test_post_cutoff_games_excluded(self):
        bad=self.c.iloc[:1].copy();bad['Season']=2022;bad['DayNum']=150;bad['WScore']=-1
        g,_=f.reference_inputs(pd.concat([self.c,bad]),self.d,2022);pd.testing.assert_frame_equal(g,self.games)
    def test_reference_equal_full_builder(self):
        full,_=sf.build_snapshot(self.c,self.d,self.s,'M',2022)
        pd.testing.assert_frame_equal(full[['TeamID']+sf.CONTROL],self.base[['TeamID']+sf.CONTROL])
    def test_no_failed_shooting_families_needed(self):
        with patch.object(sf,'adjusted_profiles',side_effect=AssertionError('must not run')),patch.object(sf,'opponent_residuals',side_effect=AssertionError('must not run')):
            f.finish_reference(self.strength,self.shoot,self.long,self.s,2022)
    def test_seed_duplicate_rejected(self):
        with self.assertRaises(ValueError):f.seed_table(pd.concat([self.s,self.s.query('Season==2022').iloc[:1]]),2022)
    def test_seed_missing_rejected(self):
        with self.assertRaises(ValueError):f.seed_table(self.s.drop(self.s.query('Season==2022').index[0]),2022)
    def test_seed_malformed_rejected(self):
        s=self.s.copy();s.loc[s.Season.eq(2022),'Seed']='invalid'
        with self.assertRaises(ValueError):f.seed_table(s,2022)
    def test_seed_2026_rejected(self):
        with self.assertRaises(ValueError):f.seed_table(self.s,2026)
    def test_base_support_enforced(self):
        b=self.base.copy();b.loc[b.seed.notna(),'clean_games']=0
        with self.assertRaises(ValueError):f.validate_reference(b)
    def test_base_duplicate_rejected(self):
        with self.assertRaises(ValueError):f.validate_reference(pd.concat([self.base,self.base.iloc[:1]]))
    def test_panel_matches_frozen_implementation(self):
        import ranking_features_round12 as old
        a,b=f.publication_panel(self.r,2018);c,d=old.publication_panel(self.r,2018)
        pd.testing.assert_frame_equal(a,c);self.assertEqual(b,d)
    def test_future_rankings_excluded(self):
        r=self.r.copy();r.loc[r.RankingDayNum.gt(132),'OrdinalRank']=-100
        p,_=f.publication_panel(r,2022);pd.testing.assert_frame_equal(p,self.panel)
    def test_newest_edition_no_backfill(self):
        r=self.r.copy();r=r.loc[~(r.Season.eq(2022)&r.SystemName.eq('S00')&r.RankingDayNum.eq(128)&r.TeamID.eq(1101))]
        p,_=f.publication_panel(r,2022);self.assertTrue(p.loc[p.SystemName.eq('S00')&p.TeamID.eq(1101)].empty)
    def test_duplicate_rank_rejected(self):
        r=pd.concat([self.r,self.r.query('Season==2022 and RankingDayNum==128').iloc[:1]])
        with self.assertRaises(ValueError):f.publication_panel(r,2022)
    def test_rank_float_rejected(self):
        r=self.r.copy();r['OrdinalRank']=r.OrdinalRank.astype(float);r.loc[r.Season.eq(2022)&r.RankingDayNum.eq(128),'OrdinalRank']+=.5
        with self.assertRaises(ValueError):f.publication_panel(r,2022)
    def test_missing_latest_system_coverage(self):
        p=self.panel.loc[self.panel.SystemName.eq('S00')]
        with self.assertRaises(ValueError):f.build_matchups(self.base,p)
    def test_control_matches_round12(self):
        import ranking_features_round12 as old
        old.YEARS.append(2022)
        try:
            p,_,_=f.build_matchups(self.base,self.panel);q,_,_,_=old.build_matchups(self.base,self.panel)
            np.testing.assert_allclose(p[f.ALL],q[f.ALL],atol=0,rtol=0)
        finally:old.YEARS.remove(2022)
    def test_possible_pairs_before_labels(self):
        p,_,_=f.build_matchups(self.base,self.panel);self.assertEqual(len(p),2278);self.assertNotIn('y',p);self.assertNotIn('DayNum',p)
    def test_team_swap_antisymmetry(self):
        p,profile,_=f.build_matchups(self.base,self.panel);lookup=profile.set_index('TeamID')
        reverse=lookup.loc[p.Team2ID,'consensus_logit'].to_numpy()-lookup.loc[p.Team1ID,'consensus_logit'].to_numpy()
        np.testing.assert_allclose(p[f.CONSENSUS]+reverse,0,atol=1e-14)
    def test_csv_numeric_representation(self):
        p,_,_=f.build_matchups(self.base,self.panel);read=pd.read_csv(io.StringIO(p.to_csv(index=False,float_format='%.17g')),float_precision='round_trip')
        np.testing.assert_array_equal(read[f.KEYS[1:]],p[f.KEYS[1:]]);np.testing.assert_allclose(read[f.ALL],p[f.ALL],atol=0,rtol=0)
    def test_label_counts_and_2021(self):
        p,y,a=f.tournament_labels(self.y,self.s,self.names);self.assertEqual(a.query('Season==2021').played_main_draw_games.iloc[0],62)
        self.assertEqual(len(p),sum(f.EXPECTED_MAIN_DRAW.values()));self.assertNotIn(2026,p.Season.values)
    def test_first_four_2021_day136_excluded(self):
        p,y,a=f.tournament_labels(self.y,self.s,self.names,[2021]);self.assertEqual(a.first_four_max_day.iloc[0],136);self.assertEqual(a.main_draw_min_day.iloc[0],137);self.assertEqual(len(p),62)
    def test_no_contest_absent_also_supported(self):
        y=self.y.loc[~(self.y.Season.eq(2021)&self.y.LScore.eq(0))]
        p,_,a=f.tournament_labels(y,self.s,self.names,[2021]);self.assertEqual(len(p),62);self.assertEqual(a.no_contest_rows_excluded.iloc[0],0)
    def test_targets_2026_ignored(self):
        bad=self.y.iloc[:1].copy();bad['Season']=2026;bad['WScore']=-20
        a,y,_=f.tournament_labels(self.y,self.s,self.names);b,z,_=f.tournament_labels(pd.concat([self.y,bad]),self.s,self.names)
        pd.testing.assert_frame_equal(a,b);np.testing.assert_array_equal(y,z)
    def test_labels_wrong_count_stop(self):
        y=self.y.drop(self.y.query('Season==2022').index[-1])
        with self.assertRaises(ValueError):f.tournament_labels(y,self.s,self.names)
    def test_labels_2026_request_stop(self):
        with self.assertRaises(ValueError):f.tournament_labels(self.y,self.s,self.names,[2026])
    def test_old_labels_match_saved_protocol(self):
        a,y,_=f.tournament_labels(self.y,self.s,self.names,f.OLD_YEARS);b,z=sf.tournament_pairs(self.y,'M',f.OLD_YEARS)
        pd.testing.assert_frame_equal(a,b);np.testing.assert_array_equal(y,z)
    def test_training_split_isolation(self):
        p,y,_=f.tournament_labels(self.y,self.s,self.names);ti,vi=rf.split_indices(p,2023)
        self.assertLess(p.iloc[ti].Season.max(),2023);self.assertTrue(p.iloc[vi].Season.eq(2023).all());self.assertNotIn(2020,p.iloc[ti].Season.values)
    def test_streaming_same_panel(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'r.csv';self.r.to_csv(path,index=False)
            with contextlib.redirect_stdout(io.StringIO()):raw=f.read_rankings(path,[2022],500)
            p,_=f.publication_panel(raw,2022);pd.testing.assert_frame_equal(p,self.panel)
    def test_primary_gate_pass(self):
        e=pd.DataFrame({'Season':f.VALIDATION,'delta_brier':[-.002,-.001,-.001,.001]})
        self.assertEqual(w.decision(e)['decision'],'CONSIDER_FIXED_PRODUCTION_RECIPE_TEST')
    def test_primary_gate_fail_mean(self):
        e=pd.DataFrame({'Season':f.VALIDATION,'delta_brier':[-.0001,-.0001,-.0001,.0001]})
        self.assertEqual(w.decision(e)['decision'],'DO_NOT_PROMOTE_TO_PRODUCTION')
    def test_primary_gate_fail_stability(self):
        e=pd.DataFrame({'Season':f.VALIDATION,'delta_brier':[-.01,-.01,.001,.001]})
        self.assertEqual(w.decision(e)['decision'],'DO_NOT_PROMOTE_TO_PRODUCTION')
    def test_no_promotion_on_gate(self):
        e=pd.DataFrame({'Season':f.VALIDATION,'delta_brier':[-.002]*4})
        self.assertFalse(w.decision(e)['automatic_promotion']);self.assertFalse(w.decision(e)['significance_claim'])
    def test_wrong_decision_year_rejected(self):
        with self.assertRaises(ValueError):w.decision(pd.DataFrame({'Season':[2016,2017,2018,2019],'delta_brier':[-.002]*4}))

class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        with contextlib.redirect_stdout(io.StringIO()):cls.args,cls.head=build_fixture(cls.root)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def context(self):
        with patch.object(rf,'EXPECTED_SHA',self.head),contextlib.redirect_stdout(io.StringIO()):return w.preflight(**self.args)
    def test_01_end_to_end_and_resume(self):
        with patch.object(rf,'EXPECTED_SHA',self.head),contextlib.redirect_stdout(io.StringIO()):
            ctx=w.preflight(**self.args);w.prepare(ctx);w.evaluate(ctx);w.report(ctx)
            a=w.read_json(ctx['directory']/'prepare.json');self.assertEqual(a['new_rating_fits'],10);self.assertEqual(a['new_matchup_tables'],5)
            e=w.read_json(ctx['directory']/'evaluation_receipt.json');self.assertEqual(e['new_classifier_fits'],8)
            before={str(p):w.sha(p) for p in (ctx['directory']/'fits').rglob('*') if p.is_file()}
            with patch.object(rf,'fitted_model',side_effect=AssertionError('unexpected refit')),patch.object(sf,'compact_strength',side_effect=AssertionError('unexpected rating')),patch.object(sf,'standard_control',side_effect=AssertionError('unexpected rating')):
                w.prepare(ctx);w.evaluate(ctx);w.report(ctx)
            self.assertEqual(w.read_json(ctx['directory']/'prepare.json')['new_rating_fits'],0)
            self.assertEqual(w.read_json(ctx['directory']/'evaluation_receipt.json')['new_classifier_fits'],0)
            self.assertEqual(before,{str(p):w.sha(p) for p in (ctx['directory']/'fits').rglob('*') if p.is_file()})
            w.preservation(ctx)
    def test_02_report_has_only_aggregate_returns(self):
        import zipfile
        report=self.args['kit']/'reports/milestone_13_return.zip'
        with zipfile.ZipFile(report) as z:
            names=z.namelist();self.assertNotIn('predictions.csv',names);self.assertNotIn('model.json',names);self.assertNotIn('team_profiles.csv',names)
            pin=json.loads(z.read('return_integrity.json'))['sha256']
            import hashlib
            for n,h in pin.items():self.assertEqual(hashlib.sha256(z.read(n)).hexdigest(),h)
    def test_03_expected_training_counts(self):
        ctx=self.context();m=w.read_csv(ctx['directory']/'metrics.csv')
        self.assertEqual(m.query("recipe=='anchor'").train_games.tolist(),[503,566,629,692])
    def test_04_plotly_ten(self):
        from consensus_plots import figures
        ctx=self.context();self.assertEqual(len(figures(ctx['directory'],ctx['kit']/'evidence/round12')),10)
    def test_05_changed_kit_stops(self):
        p=self.args['kit']/'consensus_features.py';old=p.read_bytes()
        try:
            p.write_bytes(old+b'\n# edited\n')
            with self.assertRaises(ValueError):self.context()
        finally:p.write_bytes(old)
    def test_06_changed_raw_stops(self):
        p=self.args['repo']/'data/kaggle/raw/MTeams.csv';old=p.read_bytes()
        try:
            p.write_bytes(old+b'\n')
            with self.assertRaises(ValueError):self.context()
        finally:p.write_bytes(old)
    def test_07_changed_checkpoint_stops(self):
        ctx=self.context();p=ctx['rankings']/'snapshots/M_2013/matchups.csv';old=p.read_bytes()
        try:
            p.write_bytes(old+b'\n')
            with self.assertRaises(ValueError):self.context()
        finally:p.write_bytes(old)
    def test_08_repository_edit_stops(self):
        p=self.args['repo']/'src/example.py';old=p.read_bytes()
        try:
            p.write_text('VALUE=2\n')
            with self.assertRaises(ValueError):self.context()
        finally:p.write_bytes(old)
    def test_09_wrong_environment_stops(self):
        with patch.object(w,'environment',return_value={}):
            with self.assertRaises(ValueError):self.context()
    def test_10_missing_input_stops(self):
        p=self.args['repo']/'data/kaggle/raw/MTeams.csv';b=p.with_suffix('.backup');p.rename(b)
        try:
            with self.assertRaises(ValueError):self.context()
        finally:b.rename(p)
    def test_11_symlink_input_stops(self):
        p=self.args['repo']/'data/kaggle/raw/MTeams.csv';b=p.with_suffix('.backup');p.rename(b);p.symlink_to(b)
        try:
            with self.assertRaises(ValueError):self.context()
        finally:p.unlink();b.rename(p)
    def test_12_corrupt_local_model_stops(self):
        ctx=self.context();p=ctx['directory']/'fits/M_2022_anchor/model.json';old=p.read_bytes()
        try:
            p.write_bytes(old+b'\n')
            with patch.object(rf,'EXPECTED_SHA',self.head),contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(ValueError):w.evaluate(ctx)
        finally:p.write_bytes(old)

class RunnerTests(unittest.TestCase):
    def test_invalid_stage_no_start(self):
        from run_round13 import run_stage
        with self.assertRaises(ValueError):run_stage('unknown')
    def test_limit_not_silently_expanded(self):
        from run_round13 import run_stage
        with self.assertRaises(ValueError):run_stage('evaluate',max_seconds=181)
    def test_real_stage_timeout_and_failure_export(self):
        import run_round13 as runner
        with tempfile.TemporaryDirectory() as d:
            kit=Path(d);(kit/'run_round13.py').write_text('# synthetic runner location')
            (kit/'consensus_workflow.py').write_text('import time;time.sleep(20)')
            with patch.object(runner,'__file__',str(kit/'run_round13.py')),contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(TimeoutError):runner.run_stage('prepare',max_seconds=1)
            self.assertTrue((kit/'reports/milestone_13_failure.zip').is_file())
    def test_concurrent_run_rejected(self):
        import run_round13 as runner
        import fcntl
        with tempfile.TemporaryDirectory() as d:
            kit=Path(d);(kit/'reports').mkdir()
            with (kit/'reports/execution.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(runner,'__file__',str(kit/'run_round13.py')):
                    with self.assertRaises(RuntimeError):runner.run_stage('prepare',max_seconds=1)
    def test_failure_log_contains_stage_error(self):
        import run_round13 as runner
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            kit=Path(d);(kit/'consensus_workflow.py').write_text('raise ValueError("synthetic preflight failure")')
            with patch.object(runner,'__file__',str(kit/'run_round13.py')),contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(RuntimeError):runner.run_stage('prepare',max_seconds=5)
            with zipfile.ZipFile(kit/'reports/milestone_13_failure.zip') as z:
                self.assertIn('synthetic preflight failure',z.read('consensus_validation_prepare.log').decode())
    def test_no_style_notebook_calls(self):
        import nbformat
        nb=nbformat.read(Path(__file__).parents[1]/'13_consensus_later_era.ipynb',as_version=4)
        for c in nb.cells:
            if c.cell_type=='code':self.assertNotIn('.style',c.source);compile(c.source,'notebook','exec')

if __name__=='__main__':unittest.main()
