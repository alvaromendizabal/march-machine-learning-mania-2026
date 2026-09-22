"""Aggregate publication invariants; no competitive model fitting."""
import copy
import unittest
from current_research import load_evidence,validate_data,load_progression,validate_progression

class EvidenceTests(unittest.TestCase):
    def setUp(self): self.data=load_evidence()
    def rejected(self,mutate):
        d=copy.deepcopy(self.data);mutate(d)
        with self.assertRaises(ValueError):validate_data(d)
    def test_valid_evidence(self):self.assertEqual(validate_data(self.data)['schema'],1)
    def test_no_fabricated_score(self):self.rejected(lambda d:d['robustness'].update(new_kaggle_score=.1))
    def test_no_fabricated_submission(self):self.rejected(lambda d:d['robustness'].update(submissions=1))
    def test_pooled_metric(self):self.rejected(lambda d:d['robustness']['pooled'].update(margin=.1))
    def test_finite_metric(self):self.rejected(lambda d:d['robustness']['pooled'].update(core=float('nan')))
    def test_year_completeness(self):self.rejected(lambda d:d['robustness']['rows'].pop())
    def test_no_seed_selection(self):self.rejected(lambda d:d['robustness']['seeds'].pop())
    def test_frozen_weight(self):self.rejected(lambda d:d['method'].update(margin_weight=.5))
    def test_fit_accounting(self):self.rejected(lambda d:d['robustness'].update(new_tree_fits=100))
    def test_source_hash(self):self.rejected(lambda d:d['sources'][0].update(sha256='invalid'))
    def test_negative_findings_retained(self):
        r=self.data['screen']['rows'];self.assertEqual(len(r),5);self.assertTrue(all(x['candidate']>x['core'] for x in r[:4]));self.assertLess(r[-1]['candidate'],r[-1]['core'])
    def test_ablation_not_every_year(self):self.assertEqual(sum(x['margin']<x['binary'] for x in self.data['robustness']['rows']),2)

class ProgressionTests(unittest.TestCase):
    def setUp(self):self.d=load_progression()
    def bad(self,fn):
        d=copy.deepcopy(self.d);fn(d)
        with self.assertRaises(ValueError):validate_progression(d)
    def test_valid(self):self.assertEqual(validate_progression(self.d)['scored']['candidate_score'],.1094899)
    def test_score(self):self.bad(lambda d:d['scored'].update(candidate_score=.1))
    def test_status(self):self.bad(lambda d:d['scored']['raw_submission'].update(status='PENDING'))
    def test_identity(self):self.bad(lambda d:d['scored']['raw_submission'].update(ref='123'))
    def test_hash(self):self.bad(lambda d:d['scored'].update(candidate_sha256='0'*64))
    def test_gain(self):self.bad(lambda d:d['scored'].update(gain_vs_incumbent=.9))
    def test_women_unsubmitted(self):self.bad(lambda d:d['women_screen'].update(submissions=1))
    def test_women_no_score(self):self.bad(lambda d:d['women_screen'].update(new_kaggle_score=.1))
    def test_women_population(self):self.bad(lambda d:d['women_screen']['rows'].pop())
    def test_women_pooled(self):self.bad(lambda d:d['women_screen'].update(screen_margin_brier=.1))
    def test_women_ablation(self):self.bad(lambda d:d['women_screen'].update(objective_gain=.1))
    def test_women_fits(self):self.bad(lambda d:d['women_screen'].update(new_tree_fits=100))
    def test_women_guard(self):self.bad(lambda d:d['women_screen']['checks'].update(historical_gain=False))
    def test_progression_provenance(self):self.bad(lambda d:d['sources'][0].update(sha256='invalid'))

if __name__=='__main__':unittest.main()
