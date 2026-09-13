"""Temporary-fixture integration and safety tests, executed only by the user."""
from pathlib import Path
import json,tempfile,unittest,zipfile,hashlib,time,sys
from unittest.mock import patch
import numpy as np
import pandas as pd
import feature_rounds as f
import round_workflow as w
import run_round
from fixtures import build_fixture

class IOTests(unittest.TestCase):
    def test_atomic_checkpoint_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);w.atomic_json(p/'value.json',{'value':1});w.seal(p,['value.json']);self.assertTrue(w.checkpoint(p,['value.json']))
    def test_corrupt_checkpoint_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);w.atomic_json(p/'value.json',{'value':1});w.seal(p,['value.json']);(p/'value.json').write_text('{}')
            with self.assertRaises(ValueError):w.checkpoint(p,['value.json'])
    def test_missing_completion_not_reused(self):
        with tempfile.TemporaryDirectory() as d:self.assertFalse(w.checkpoint(Path(d),['value.json']))
    def test_path_traversal_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):w.safe_file(Path(d),'../escape')
    def test_symbolic_output_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'target').mkdir();(root/'link').symlink_to(root/'target',target_is_directory=True)
            with self.assertRaises(ValueError):w.output_dir(root/'link')
    def test_legacy_metric_without_log_loss(self):
        y=np.array([0,1]);p=np.array([.2,.7]);m=w.normalize_metric({'brier':float(np.mean((p-y)**2))},y,p,'M',2022)
        self.assertGreater(m['log_loss'],0)
    def test_bad_metric_not_silently_recomputed(self):
        with self.assertRaises(ValueError):w.normalize_metric({'brier':0.},np.array([0,1]),np.array([.2,.7]),'M',2022)
    def test_gate_does_not_promote_bad_family(self):
        e=pd.DataFrame([{'Season':s,'comparison':c,'delta_brier':.001} for c in ['adjustment_given_rates','both_given_duplicate'] for s in f.VALIDATION])
        self.assertEqual(w.decision(e,'16')['decision'],'DO_NOT_PROMOTE')
    def test_gate_requires_duplicate_control(self):
        e=pd.DataFrame([{'Season':s,'comparison':c,'delta_brier':-.001 if c=='adjustment_given_rates' else .001} for c in ['adjustment_given_rates','both_given_duplicate'] for s in f.VALIDATION])
        self.assertEqual(w.decision(e,'17')['decision'],'DO_NOT_PROMOTE')
    def test_gate_positive_case(self):
        e=pd.DataFrame([{'Season':s,'comparison':c,'delta_brier':-.001} for c in ['adjustment_given_rates','both_given_duplicate'] for s in f.VALIDATION])
        self.assertEqual(w.decision(e,'17')['decision'],'CONSIDER_PRODUCTION_TRANSFER')
    def test_partial_gate_rejected(self):
        e=pd.DataFrame([{'Season':2022,'comparison':'adjustment_given_rates','delta_brier':-.1}])
        with self.assertRaises(ValueError):w.decision(e,'16')
    def test_hard_timeout_preserves_files(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'round_workflow.py').write_text('import time\ntime.sleep(8)\n');(p/'keep.txt').write_text('checkpoint')
            with patch.object(run_round,'__file__',str(p/'run_round.py')):
                with self.assertRaises(TimeoutError):run_round.run_stage('16','smoke',1)
            self.assertEqual((p/'keep.txt').read_text(),'checkpoint')
            self.assertTrue((p/'reports/round16/milestone_16_failure.zip').is_file())
    def test_invalid_stage_does_not_launch(self):
        with self.assertRaises(ValueError):run_round.run_stage('16','unknown',1)
    def test_invalid_ceiling(self):
        with self.assertRaises(ValueError):run_round.run_stage('16','smoke',900)

class FullFixtureTest(unittest.TestCase):
    def test_both_rounds_export_resume_and_protection(self):
        with tempfile.TemporaryDirectory() as d:
            args,head=build_fixture(d)
            with patch.object(w.rf,'EXPECTED_SHA',head):
                for rid in ['16','17']:
                    ctx=w.preflight(**args,round_id=rid)
                    if rid=='16':w.audit(ctx)
                    with self.assertRaises((ValueError,FileNotFoundError)):w.prepare(ctx)
                    # Interrupt smoke after one target checkpoint, then recover.
                    original=f.fit_target;counter={'n':0}
                    def interrupt(*a,**kw):
                        counter['n']+=1
                        if counter['n']==2:raise RuntimeError('Intentional synthetic interruption')
                        return original(*a,**kw)
                    with patch.object(f,'fit_target',side_effect=interrupt):
                        with self.assertRaises(RuntimeError):w.smoke(ctx)
                    first=ctx['directory']/f'ratings/M_2013_{f.FAMILIES[rid][0]}/model.json'
                    first_hash=w.sha(first)
                    w.smoke(ctx);self.assertEqual(w.sha(first),first_hash)
                    self.assertEqual(w.read_json(ctx['directory']/'smoke.json')['new_rating_fits'],1)
                    w.prepare(ctx);self.assertEqual(w.read_json(ctx['directory']/'prepare.json')['new_rating_fits'],22)
                    w.evaluate(ctx);receipt=w.read_json(ctx['directory']/'evaluation_receipt.json')
                    self.assertEqual(receipt['new_classifier_fits'],20);self.assertEqual(receipt['total_comparisons'],24)
                    with patch.dict(sys.modules,{"jinja2":None}):w.report(ctx)
                    bundle=ctx['reports']/f'milestone_{rid}_return.zip'
                    with zipfile.ZipFile(bundle) as z:
                        integrity=json.loads(z.read('return_integrity.json'))['sha256']
                        for name,h in integrity.items():self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),h)
                        self.assertNotIn('predictions.csv',z.namelist());self.assertNotIn('profiles.csv',z.namelist())
                    from round_plots import figures
                    self.assertEqual(len(figures(ctx['directory'],rid,ctx['kit']/'evidence')),10)
                    with patch.object(f,'fit_target',side_effect=AssertionError('Should reuse ratings')),patch.object(w.rf,'fitted_model',side_effect=AssertionError('Should reuse classifiers')):
                        w.smoke(ctx);w.prepare(ctx);w.evaluate(ctx)
                    self.assertEqual(w.read_json(ctx['directory']/'evaluation_receipt.json')['new_classifier_fits'],0)
                    w.preservation(ctx)
                bad=ctx['directory']/f'ratings/M_2013_{f.FAMILIES[rid][0]}/teams.csv';bad.write_text('corrupt')
                with self.assertRaises(ValueError):w.prepare(ctx)

if __name__=='__main__':unittest.main()
