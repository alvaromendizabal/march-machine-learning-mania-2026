from __future__ import annotations
import contextlib,copy,io,json,sys,tempfile,unittest,zipfile,hashlib,fcntl
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
import ranking_features as f
import ranking_workflow as w
from fixtures import toy_data,toy_rankings,build_fixture,manifest

class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.bases,_=toy_data();cls.raw=toy_rankings(cls.bases)
        cls.panel,cls.info=f.publication_panel(cls.raw,2013)
    def test_published_edition_is_latest_per_system(self):
        self.assertTrue(self.panel.RankingDayNum.eq(128).all())
    def test_normalization_matches_existing_repository_formula(self):
        raw=self.raw.query('Season==2013 and RankingDayNum==128').sort_values(['SystemName','TeamID'])
        p=1-(raw.OrdinalRank-1)/(raw.groupby('SystemName').OrdinalRank.transform('max')-1).clip(lower=1)
        np.testing.assert_array_equal(self.panel.percentile,p.to_numpy())
    def test_future_and_other_year_rows_ignored(self):
        extra=self.raw.iloc[[0]].copy();extra.RankingDayNum=133;extra.OrdinalRank=np.nan
        future=extra.copy();future.RankingDayNum=128;future.Season=2026
        p,_=f.publication_panel(pd.concat([self.raw,extra,future]),2013)
        pd.testing.assert_frame_equal(p,self.panel)
    def test_old_editions_ignored(self):
        raw=self.raw.copy();raw.loc[raw.RankingDayNum.eq(110),'OrdinalRank']=np.nan
        pd.testing.assert_frame_equal(f.publication_panel(raw,2013)[0],self.panel)
    def test_outcome_columns_ignored(self):
        raw=self.raw.copy();raw['y']=1;raw['Champion']='not-an-input'
        pd.testing.assert_frame_equal(f.publication_panel(raw,2013)[0],self.panel)
    def test_row_order_independence(self):
        pd.testing.assert_frame_equal(f.publication_panel(self.raw.sample(frac=1,random_state=4),2013)[0],self.panel)
    def test_float_integer_representation_parity(self):
        raw=self.raw.astype({'TeamID':'float64','OrdinalRank':'float64','Season':'float64','RankingDayNum':'float64'})
        pd.testing.assert_frame_equal(f.publication_panel(raw,2013)[0],self.panel)
    def test_missing_latest_team_not_backfilled(self):
        t=int(self.panel.TeamID.iloc[0]);raw=self.raw.loc[~(self.raw.Season.eq(2013)&self.raw.SystemName.eq('S00')&self.raw.RankingDayNum.eq(128)&self.raw.TeamID.eq(t))]
        p,_=f.publication_panel(raw,2013)
        self.assertFalse(((p.TeamID==t)&(p.SystemName=='S00')).any())
    def test_duplicate_legal_entry_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):f.publication_panel(pd.concat([self.raw,self.raw.query('RankingDayNum==128').iloc[[0]]]),2013)
    def test_fractional_rank_rejected(self):
        raw=self.raw.astype({'OrdinalRank':float});idx=raw.query('Season==2013 and RankingDayNum==128').index[0];raw.loc[idx,'OrdinalRank']+=.5
        with self.assertRaises(ValueError):f.publication_panel(raw,2013)
    def test_zero_rank_rejected(self):
        raw=self.raw.copy();raw.loc[raw.index[raw.RankingDayNum.eq(128)][0],'OrdinalRank']=0
        with self.assertRaises(ValueError):f.publication_panel(raw,2013)
    def test_empty_system_rejected(self):
        raw=self.raw.copy();raw.loc[raw.index[raw.RankingDayNum.eq(128)][0],'SystemName']=' '
        with self.assertRaises(ValueError):f.publication_panel(raw,2013)
    def test_missing_season_rejected(self):
        with self.assertRaises(ValueError):f.publication_panel(self.raw,2026)
    def test_missing_schema_rejected(self):
        with self.assertRaises(ValueError):f.publication_panel(self.raw.drop(columns='OrdinalRank'),2013)
    def test_empty_legal_panel_rejected(self):
        with self.assertRaises(ValueError):f.publication_panel(self.raw.query('RankingDayNum==110'),2013)
    def test_pair_control_preserved(self):
        pairs,_,_,_=f.build_matchups(self.bases[0],self.panel);base=self.bases[0].set_index('TeamID')
        self.assertEqual(len(pairs),66)
        for col in f.sf.CONTROL:
            expected=base.loc[pairs.Team1ID,col].to_numpy()-base.loc[pairs.Team2ID,col].to_numpy()
            np.testing.assert_array_equal(pairs['diff_'+col],expected)
    def test_pair_swap(self):
        a=np.array([1101,1102,1104]);b=np.array([1103,1105,1107]);x,_=f.pair_ranking_signals(self.panel,a,b);y,_=f.pair_ranking_signals(self.panel,b,a)
        np.testing.assert_allclose(x,-y,rtol=0,atol=1e-12)
    def test_missing_team_rejected(self):
        with self.assertRaisesRegex(ValueError,'no legal'):f.pair_ranking_signals(self.panel,np.array([9999]),np.array([1101]))
    def test_insufficient_common_rejected(self):
        p=self.panel.query("SystemName in ['S00','S01']")
        with self.assertRaisesRegex(ValueError,'Insufficient'):f.pair_ranking_signals(p,np.array([1101]),np.array([1102]))
    def test_self_pair_rejected(self):
        with self.assertRaises(ValueError):f.pair_ranking_signals(self.panel,np.array([1101]),np.array([1101]))
    def test_duplicate_base_rejected(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):f.build_matchups(pd.concat([self.bases[0],self.bases[0].iloc[[0]]]),self.panel)
    def test_wrong_gender_rejected(self):
        base=self.bases[0].copy();base.Gender='W'
        with self.assertRaises(ValueError):f.build_matchups(base,self.panel)
    def test_seed_dtype_parity(self):
        base=self.bases[0].copy();base.seed=base.seed.astype(int)
        x=f.build_matchups(base,self.panel)[0];y=f.build_matchups(self.bases[0],self.panel)[0]
        np.testing.assert_array_equal(x[f.ALL].to_numpy(),y[f.ALL].to_numpy())
    def test_future_team_not_in_pair_catalog(self):
        pairs,_,_,_=f.build_matchups(self.bases[0],self.panel)
        self.assertFalse((pairs.Team1ID==9999).any())
    def test_tied_ranks_count_half(self):
        p=self.panel.copy();p['OrdinalRank']=2;p['percentile']=.5;p['system_logit']=0
        x,d=f.pair_ranking_signals(p,np.array([1101]),np.array([1102]))
        self.assertEqual(x[f.VOTES[0]].iloc[0],0);self.assertEqual(d.fraction_ties.iloc[0],1)
    def test_logit_clipping_does_not_create_fake_vote_ties(self):
        rows=[]
        for s in range(3):
            for t,r in [(1101,1),(1102,2),(9999,1000)]:rows.append(dict(Season=2013,RankingDayNum=128,SystemName=str(s),TeamID=t,OrdinalRank=r))
        p,_=f.publication_panel(pd.DataFrame(rows),2013);x,d=f.pair_ranking_signals(p,np.array([1101]),np.array([1102]))
        self.assertAlmostEqual(x[f.VOTES[0]].iloc[0],np.log(4));self.assertEqual(d.fraction_ties.iloc[0],0)
    def test_exact_vote_formula(self):
        rows=[]
        for s,(ra,rb) in enumerate([(1,2),(2,1),(1,1),(1,2)]):
            for t,r in [(1101,ra),(1102,rb),(1112,10)]:rows.append(dict(Season=2013,RankingDayNum=128,SystemName=str(s),TeamID=t,OrdinalRank=r))
        p,_=f.publication_panel(pd.DataFrame(rows),2013);x,_=f.pair_ranking_signals(p,np.array([1101]),np.array([1102]))
        self.assertAlmostEqual(x[f.VOTES[0]].iloc[0],np.log(3.5/2.5))
    def test_shared_median_adds_information_beyond_marginal_medians(self):
        rows=[]
        for system,(a,b) in enumerate([(1,3),(2,1),(3,2)]):
            for t,rank in [(1101,a),(1102,b),(1110,3)]:
                rows.append(dict(Season=2013,RankingDayNum=128,SystemName=str(system),TeamID=t,OrdinalRank=rank))
        p,_=f.publication_panel(pd.DataFrame(rows),2013)
        x,_=f.pair_ranking_signals(p,np.array([1101]),np.array([1102]))
        self.assertAlmostEqual(x[f.CONSENSUS[0]].iloc[0],0)
        self.assertLess(x[f.MEDIAN[0]].iloc[0],-1.)
    def test_registry_only_two_novel_claims(self):
        reg=f.registry();self.assertEqual(int(reg.new_candidate.sum()),2);self.assertEqual(len(reg),19)
    def test_chunk_boundaries_preserve_panel(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            p=Path(d)/'r.csv';self.raw.to_csv(p,index=False)
            loaded=f.read_legal_rankings(p,[2013],chunksize=101)
            pd.testing.assert_frame_equal(f.publication_panel(loaded,2013)[0],self.panel)
    def test_no_outcome_input_in_registry(self):
        self.assertTrue(f.registry().cutoff_day.eq(132).all())

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.args,self.head=build_fixture(self.t.name)
        self.guard=patch.object(w.rf,'EXPECTED_SHA',self.head);self.guard.start()
        self.silence=contextlib.redirect_stdout(io.StringIO());self.silence.__enter__()
    def tearDown(self):self.silence.__exit__(None,None,None);self.guard.stop();self.t.cleanup()
    def ctx(self):return w.preflight(**self.args)
    def test_full_pipeline_and_resume(self):
        c=self.ctx();w.prepare(c);w.evaluate(c);w.report(c)
        self.assertEqual(w.read_json(c['directory']/'prepare.json')['new_rating_fits'],0)
        self.assertEqual(w.read_json(c['directory']/'evaluation_receipt.json')['new_classifier_fits'],16)
        first={str(p):w.sha(p) for p in c['directory'].rglob('*') if p.is_file() and p.name in ['model.json','matchups.csv','panel.csv','complete.json']}
        with patch.object(w.rf,'fitted_model',side_effect=AssertionError('Unexpected fit')):
            w.prepare(c);w.evaluate(c);w.report(c)
        self.assertEqual(first,{p:w.sha(Path(p)) for p in first})
        self.assertEqual(w.read_json(c['directory']/'prepare.json')['panel_reuses'],7)
        self.assertEqual(w.read_json(c['directory']/'evaluation_receipt.json')['local_reuses'],16)
        from ranking_plots import figures
        self.assertEqual(len(figures(c['directory'],c['kit']/'evidence/round11')),10)
        with zipfile.ZipFile(c['kit']/'reports/milestone_12_return.zip') as z:
            self.assertNotIn('predictions.csv',z.namelist());self.assertNotIn('pair_support.csv',z.namelist())
            hashes=json.loads(z.read('return_integrity.json'))['sha256']
            self.assertTrue(all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in hashes.items()))
    def test_source_tamper_stops(self):
        p=self.args['kit']/'ranking_features.py';p.write_text(p.read_text()+'\n# changed')
        with self.assertRaisesRegex(ValueError,'Delivered source'):self.ctx()
    def test_raw_tamper_stops(self):
        p=self.args['repo']/'data/kaggle/raw/MMasseyOrdinals.csv';p.write_text(p.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'Raw input'):self.ctx()
    def test_environment_stops(self):
        with patch.object(w,'environment',return_value={'different':True}):
            with self.assertRaisesRegex(ValueError,'Environment'):self.ctx()
    def test_missing_reference_stops(self):
        c=json.loads((self.args['kit']/'constraints.json').read_text());p=self.args['possession']/'private_runs'/c['fingerprints']['possession']/'fits/M_2016_anchor/model.json';p.unlink()
        with self.assertRaises(ValueError):self.ctx()
    def test_report_checksum_stops(self):
        p=self.args['margin']/'reports/milestone_11_return.zip';p.write_bytes(p.read_bytes()+b'tamper')
        with self.assertRaisesRegex(ValueError,'Prior scientific'):self.ctx()
    def test_corrupt_panel_stops(self):
        c=self.ctx();w.prepare(c);p=c['directory']/'panels/M_2013/panel.csv';p.write_text('bad')
        with self.assertRaisesRegex(ValueError,'Corrupt'):w.prepare(c)
    def test_corrupt_matchup_stops(self):
        c=self.ctx();w.prepare(c);p=c['directory']/'snapshots/M_2013/matchups.csv';p.write_text('bad')
        with self.assertRaisesRegex(ValueError,'Corrupt'):w.prepare(c)
    def test_no_reference_refit_or_missing_log_loss_failure(self):
        c=self.ctx();w.prepare(c)
        with patch.object(w.rf,'fitted_model',side_effect=AssertionError('refit')):
            row,_,_,origin=w.obtain(c,2017,'anchor',w.matrices(c),0)
        self.assertEqual(origin,'upstream_replay');self.assertTrue(np.isfinite(row['log_loss']))
    def test_fit_budget_stops(self):
        c=self.ctx();w.prepare(c)
        with patch.object(w.rf,'fitted_model',side_effect=AssertionError('refit')):
            with self.assertRaisesRegex(ValueError,'budget'):w.obtain(c,2017,'anchor_consensus',w.matrices(c),0)
    def test_strict_temporal_splits(self):
        c=self.ctx();w.prepare(c);_,_,x,_,_=w.matrices(c)
        for s in w.SEASONS:
            ti,vi=w.rf.split_indices(x,s);self.assertTrue(x.iloc[ti].Season.lt(s).all());self.assertTrue(x.iloc[vi].Season.eq(s).all())
    def test_gate_both_outcomes(self):
        eff=pd.DataFrame([dict(Season=s,comparison=n,delta_brier=-.002) for s in w.SEASONS for n in [w.CONFIG['primary'],w.CONFIG['secondary']]])
        self.assertTrue(all(d['decision'].startswith('CONSIDER') for d in w.decisions(eff)['decisions']))
        eff['delta_brier']=.002;self.assertTrue(all(d['decision']=='DO_NOT_EXPAND_AUTOMATICALLY' for d in w.decisions(eff)['decisions']))
    def test_incomplete_gate_rejected(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):w.decisions(pd.DataFrame([dict(Season=2016,comparison=w.CONFIG['primary'],delta_brier=-.001)]))
    def test_report_changed_during_stage_stops(self):
        c=self.ctx();c['prior_zip'].write_bytes(c['prior_zip'].read_bytes()+b'tamper')
        with self.assertRaisesRegex(ValueError,'Prior report'):w.preservation(c)
    def test_symlink_output_stops(self):
        (self.args['kit']/'reports').symlink_to(self.args['repo'],target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'Unsafe'):self.ctx()
    def test_verified_archive_scope_rejected(self):
        p=self.args['margin']/'reports/milestone_11_return.zip'
        with zipfile.ZipFile(p,'a') as z:z.writestr('unlisted.txt','extra')
        with self.assertRaisesRegex(ValueError,'scope'):w.read_previous_report(p,w.sha(p))

class RunnerTests(unittest.TestCase):
    def test_invalid_limit(self):
        import run_round12 as r
        with self.assertRaises(ValueError):r.run_stage('evaluate',max_seconds=181)
    def test_invalid_stage(self):
        import run_round12 as r
        with self.assertRaises(ValueError):r.run_stage('train_forever')
    def test_timeout_stops_child(self):
        import run_round12 as r
        with tempfile.TemporaryDirectory() as d:
            kit=Path(d);(kit/'ranking_workflow.py').write_text('import time;time.sleep(30)')
            with patch.object(r,'__file__',str(kit/'run_round12.py')),contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(TimeoutError):r.run_stage('prepare',max_seconds=1)
            self.assertEqual(json.loads((kit/'reports/failure.json').read_text())['status'],'TIME_LIMIT')
    def test_failure_bundle_excludes_private_files(self):
        import run_round12 as r
        with tempfile.TemporaryDirectory() as d:
            kit=Path(d);(kit/'reports').mkdir();(kit/'reports/failure.json').write_text('{}')
            (kit/'private_runs').mkdir();(kit/'private_runs/secret_model.json').write_text('private')
            dest=r.failure_bundle(kit,'prepare',ValueError('test'))
            with zipfile.ZipFile(dest) as z:
                self.assertEqual(set(z.namelist()),{'runtime.json','failure.json'})
    def test_lock_exclusion(self):
        import run_round12 as r
        with tempfile.TemporaryDirectory() as d:
            kit=Path(d);(kit/'reports').mkdir()
            with (kit/'reports/execution.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with patch.object(r,'__file__',str(kit/'run_round12.py')):
                    with self.assertRaisesRegex(RuntimeError,'Another'):r.run_stage('prepare',max_seconds=1)

if __name__=='__main__':unittest.main()
