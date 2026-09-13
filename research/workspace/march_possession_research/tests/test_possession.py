from __future__ import annotations
import ast, copy, json, os, shutil, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import possession_features as f
import possession_workflow as w
import possession_plots as plots
import run_round08 as runner
from fixtures import data,build_fixture


class FeatureContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compact,cls.detail,cls.seeds,cls.labels=data(seasons=(2013,),gender='W')
        cls.base,_=w.sf.build_snapshot(cls.compact,cls.detail,cls.seeds,'W',2013)
        cls.rates,cls.cover=f.build_snapshot(cls.detail,cls.base,'W',2013)
        cls.pairs,_=w.sf.tournament_pairs(cls.labels,'W',[2013])
    def test_counts(self):self.assertEqual([len(c) for c in f.RECIPES.values()],[16,22,20,26])
    def test_no_target_in_feature_lists(self):self.assertFalse(set(f.ALL)&{'y','DayNum','Season','Team1ID','Team2ID','Gender'})
    def test_novel_count(self):self.assertEqual(int(f.registry().new_definition.sum()),4)
    def test_accounting_no_turnovers_rebounds_ft(self):self.assertAlmostEqual(float(f.accounting(.5,.35,.4,.7,0,0,0)),1.02)
    def test_accounting_turnovers_reduce(self):self.assertLess(f.accounting(.5,.35,.4,.7,.2,.3,.3),f.accounting(.5,.35,.4,.7,.1,.3,.3))
    def test_accounting_rebounds_increase(self):self.assertGreater(f.accounting(.5,.35,.4,.7,.2,.4,.3),f.accounting(.5,.35,.4,.7,.2,.2,.3))
    def test_invalid_probability_stops(self):
        with self.assertRaises(ValueError):f.accounting(.5,.35,.4,.7,2,.3,.3)
    def test_invalid_denominator_stops(self):
        with self.assertRaises(ValueError):f.accounting(0,0,.4,.7,.2,1,0)
    def test_blend_neutral_league(self):self.assertAlmostEqual(float(f.blend_probability(.4,.3,.3)),.4)
    def test_blend_finite_at_endpoints(self):self.assertTrue(np.isfinite(f.blend_probability(0,1,.3)))
    def test_label_argument_absent(self):
        import inspect
        self.assertNotIn('labels',inspect.signature(f.build_snapshot).parameters)
    def test_future_regular_rows_ignored(self):
        extra=self.detail.iloc[:1].copy();extra.Season=2026;extra.WFGA=-100
        r,_=f.build_snapshot(pd.concat([self.detail,extra]),self.base,'W',2013);pd.testing.assert_frame_equal(r,self.rates)
    def test_post_cutoff_rows_ignored(self):
        extra=self.detail.iloc[:1].copy();extra.DayNum=133;extra.WFGA=-100
        r,_=f.build_snapshot(pd.concat([self.detail,extra]),self.base,'W',2013);pd.testing.assert_frame_equal(r,self.rates)
    def test_input_row_order_invariant(self):
        r,_=f.build_snapshot(self.detail.sample(frac=1,random_state=7),self.base,'W',2013);pd.testing.assert_frame_equal(r,self.rates)
    def test_swap_parity(self):
        x,_=f.pair_features(self.base,self.rates,self.pairs)
        q,_=f.pair_features(self.base,self.rates,self.pairs.rename(columns={'Team1ID':'Team2ID','Team2ID':'Team1ID'}))
        np.testing.assert_allclose(x[f.ALL],-q[f.ALL],atol=1e-12)
    def test_baseline_byte_equivalent_values(self):
        x,_=f.pair_features(self.base,self.rates,self.pairs);old=w.sf.pair_features(self.base,self.pairs)
        np.testing.assert_array_equal(x[f.BASE].to_numpy(),old[f.BASE].to_numpy())
    def test_missing_team_stops(self):
        with self.assertRaises(ValueError):f.pair_features(self.base,self.rates.iloc[:1],self.pairs)
    def test_duplicate_team_stops(self):
        with self.assertRaises(ValueError):f.pair_features(self.base,pd.concat([self.rates,self.rates.iloc[:1]]),self.pairs)
    def test_zero_shot_opportunities_smoothed(self):
        d=self.detail.copy()
        for s in ['W','L']:d[s+'FGA3']=0;d[s+'FGM3']=0;d[s+'FTA']=0;d[s+'FTM']=0
        r,_=f.build_snapshot(d,self.base,'W',2013);self.assertTrue(np.isfinite(r.select_dtypes('number')).all().all())
    def test_duplicate_game_stops(self):
        with self.assertRaises(ValueError):f.build_snapshot(pd.concat([self.detail,self.detail.iloc[:1]]),self.base,'W',2013)
    def test_stage_budget(self):
        for stage,n in [('prepare',301),('evaluate',301),('report',121)]:
            with self.assertRaises(ValueError):runner.run_stage(stage,max_seconds=n)
    def test_invalid_stage(self):
        with self.assertRaises(ValueError):runner.run_stage('full_training')
    def test_notebook_no_styler(self):
        nb=json.loads((ROOT/'08_possession_matchup_features.ipynb').read_text())
        self.assertEqual(sum(c['cell_type']=='code' for c in nb['cells']),9)
        for c in nb['cells']:
            if c['cell_type']=='code':self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr=='style' for n in ast.walk(ast.parse(''.join(c['source'])))))
    def test_decision_requires_four_seasons(self):
        with self.assertRaises(ValueError):w.decisions(pd.DataFrame([{'Gender':'M','Season':2016,'comparison':'mechanism_given_rates','delta_brier':-.1}]))
    def test_decision_cannot_use_anchor_gain_as_mechanistic_gain(self):
        a=pd.DataFrame([{'Gender':g,'Season':s,'comparison':c,'delta_brier':d} for g in ['M','W'] for s in w.SEASONS for c,d in [('mechanism_given_rates',.001),('both_vs_anchor',-.1)]])
        self.assertTrue(all(x['decision']=='DO_NOT_EXPAND_AUTOMATICALLY' for x in w.decisions(a)))
    def test_decision_stability_required(self):
        a=pd.DataFrame([{'Gender':g,'Season':s,'comparison':'mechanism_given_rates','delta_brier':d} for g in ['M','W'] for s,d in zip(w.SEASONS,[-.004,-.003,.001,.001])])
        self.assertTrue(all(x['decision']=='DO_NOT_EXPAND_AUTOMATICALLY' for x in w.decisions(a)))
    def test_decision_pass(self):
        a=pd.DataFrame([{'Gender':g,'Season':s,'comparison':'mechanism_given_rates','delta_brier':-.001} for g in ['M','W'] for s in w.SEASONS])
        self.assertTrue(all(x['decision']=='CONSIDER_LATER_ERA_REPLICATION' for x in w.decisions(a)))
    def test_supervisor_timeout(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);shutil.copy2(ROOT/'run_round08.py',r/'run_round08.py');(r/'possession_workflow.py').write_text('import time\ntime.sleep(10)\n')
            result=subprocess.run([sys.executable,str(r/'run_round08.py'),'prepare','--max-seconds','1'],capture_output=True,timeout=9)
            self.assertNotEqual(result.returncode,0);self.assertEqual(json.loads((r/'reports/failure.json').read_text())['status'],'TIME_LIMIT')
    def test_concurrent_stage_rejected(self):
        import fcntl
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);shutil.copy2(ROOT/'run_round08.py',r/'run_round08.py');(r/'reports').mkdir()
            with (r/'reports/execution.lock').open('a') as h:
                fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
                p=subprocess.run([sys.executable,str(r/'run_round08.py'),'prepare'],capture_output=True,timeout=5)
                self.assertNotEqual(p.returncode,0);self.assertIn(b'Another stage',p.stderr)


class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)/'fixture';cls.args,cls.head=build_fixture(cls.root)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)/'fixture';shutil.copytree(self.root,root)
        self.args={k:root/v.relative_to(self.root) for k,v in self.__class__.args.items()}
        self.patch=patch.object(w.rf,'EXPECTED_SHA',self.head);self.patch.start();self.ctx=w.preflight(**self.args)
    def tearDown(self):self.patch.stop();self.tmp.cleanup()
    def test_preflight_preserves(self):w.preservation(self.ctx)
    def test_prepare_no_model_fit(self):
        with patch.object(w.rf,'fitted_model',side_effect=AssertionError('No classifier fit')),patch.object(w.sf,'additive_fit',side_effect=AssertionError('No rating fit')):w.prepare(self.ctx)
        self.assertEqual(w.read_json(self.ctx['directory']/'prepare.json')['baseline_replays'],7)
    def test_full_evaluate_and_resume(self):
        w.prepare(self.ctx);w.evaluate(self.ctx)
        rec=w.read_json(self.ctx['directory']/'evaluation_receipt.json');self.assertEqual(rec['new_classifier_fits'],25);self.assertEqual(rec['upstream_classifier_replays'],7)
        with patch.object(w.rf,'fitted_model',side_effect=AssertionError('No repeated fits')),patch.object(f,'build_snapshot',side_effect=AssertionError('No repeated snapshots')):
            w.prepare(self.ctx);w.evaluate(self.ctx)
        rec=w.read_json(self.ctx['directory']/'evaluation_receipt.json');self.assertEqual(rec['new_classifier_fits'],0);self.assertEqual(rec['local_checkpoint_reuses'],25)
        w.report(self.ctx);self.assertEqual(len(plots.figures(self.ctx['directory'],self.ctx['kit']/'evidence/round07')),10)
        with zipfile.ZipFile(self.ctx['kit']/'reports/milestone_08_return.zip') as z:
            self.assertNotIn('predictions.csv',z.namelist());self.assertFalse(any('model.json' in n or 'rates.csv' in n for n in z.namelist()))
    def test_missing_upstream_stops(self):
        (self.ctx['shooting']/'snapshots/M_2013/teams.csv').unlink()
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_corrupt_upstream_stops(self):
        p=self.ctx['shooting']/'snapshots/M_2013/teams.csv';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_data_change_stops(self):
        p=self.ctx['raw']/'WRegularSeasonDetailedResults.csv';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_frozen_source_change_stops(self):
        p=self.ctx['kit']/'frozen/shot_features.py';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_new_source_change_stops(self):
        p=self.ctx['kit']/'possession_features.py';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_missing_manifest_stops(self):
        (self.ctx['kit']/'MANIFEST.json').unlink()
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_environment_change_stops(self):
        with patch.object(w,'environment',return_value={}):
            with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_known_notebook_edits_preserved(self):
        before={p:w.sha(self.ctx['repo']/p) for p in w.rf.ALLOWED_DIRTY};w.prepare(self.ctx);w.preservation(self.ctx)
        self.assertEqual(before,{p:w.sha(self.ctx['repo']/p) for p in w.rf.ALLOWED_DIRTY})
    def test_further_notebook_change_stops(self):
        p=self.ctx['repo']/next(iter(w.rf.ALLOWED_DIRTY));p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.preflight(**self.args)
    def test_path_traversal_and_symlink(self):
        with self.assertRaises(ValueError):w.safe_file(self.ctx['kit'],'../repo/.gitignore')
        p=self.ctx['kit']/'symlink';p.symlink_to(self.ctx['repo']/'.gitignore')
        with self.assertRaises(ValueError):w.safe_file(self.ctx['kit'],'symlink')
    def test_new_fit_budget_enforced(self):
        w.prepare(self.ctx);bundle=w.matrices(self.ctx,'M')
        with patch.object(w.rf,'fitted_model',side_effect=AssertionError('Must stop before fitting')):
            with self.assertRaises(ValueError):w.obtain(self.ctx,'M',2016,'anchor',bundle,0)
    def test_future_tournament_rows_ignored(self):
        w.prepare(self.ctx);b=w.matrices(self.ctx,'W');p=self.ctx['raw']/'WNCAATourneyCompactResults.csv';d=w.read_csv(p);e=d.iloc[:1].copy();e.Season=2026
        w.atomic_csv(p,pd.concat([d,e]));b2=w.matrices(self.ctx,'W');pd.testing.assert_frame_equal(b[2],b2[2]);np.testing.assert_array_equal(b[1],b2[1])
    def test_temporal_split(self):
        w.prepare(self.ctx);_,_,x,_,_=w.matrices(self.ctx,'W')
        for s in w.SEASONS:
            a,b=w.rf.split_indices(x,s);self.assertTrue((x.iloc[a].Season<s).all());self.assertTrue((x.iloc[b].Season==s).all())
    def test_stage_tamper_stops(self):
        w.prepare(self.ctx);(self.ctx['directory']/'prepare.json').write_text('{}')
        with self.assertRaises(ValueError):w.evaluate(self.ctx)
    def test_corrupt_new_checkpoint_stops(self):
        w.prepare(self.ctx);bundle=w.matrices(self.ctx,'M');w.obtain(self.ctx,'M',2016,'anchor',bundle,1)
        p=self.ctx['directory']/'fits/M_2016_anchor/model.json';p.write_text(p.read_text()+'\n')
        with self.assertRaises(ValueError):w.obtain(self.ctx,'M',2016,'anchor',bundle,1)
    def test_preprocessing_uses_training_only(self):
        w.prepare(self.ctx);_,y,x,_,_=w.matrices(self.ctx,'W');ti,vi=w.rf.split_indices(x,2016)
        model=w.rf.fitted_model(x.iloc[ti],y[ti],f.BASE);x.loc[x.index[vi],f.BASE]=1e9
        m2=w.rf.fitted_model(x.iloc[ti],y[ti],f.BASE);self.assertEqual(model,m2)

if __name__=='__main__':unittest.main()
