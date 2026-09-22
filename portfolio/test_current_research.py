"""Small aggregate-only portfolio invariants; no model fitting."""
import copy
import unittest
from current_research import load, validate

class ReportTests(unittest.TestCase):
    def setUp(self): self.data=load()
    def reject(self,section,key,value):
        data=copy.deepcopy(self.data);data[section][key]=value
        with self.assertRaises(ValueError):validate(data)
    def test_valid(self): self.assertEqual(validate(self.data)['schema'],1)
    def test_no_invented_score(self): self.reject('women','kaggle_score',.1)
    def test_no_invented_submission(self): self.reject('women','new_submissions',1)
    def test_no_invented_incumbent(self): self.reject('scored','incumbent',.09)
    def test_scored_identity(self): self.reject('scored','submission_ref','123')
    def test_scored_hash(self): self.reject('scored','sha256','?')
    def test_pooled_consistency(self): self.reject('women','margin',.1)
    def test_nonfinite(self): self.reject('women','core',float('nan'))
    def test_complete_years(self): self.reject('women','years',self.data['women']['years'][:2])
    def test_all_repeats_retained(self): self.reject('women','repeats',self.data['women']['repeats'][:1])
    def test_decision(self): self.reject('women','decision','SUBMIT_NOW')
    def test_unchanged_tests(self): self.reject('women','regression_tests',100)
    def test_unchanged_fits(self): self.reject('women','new_tree_fits',200)
    def test_checks(self): self.reject('women','checks',{'one':True})
    def test_screen_complete(self): self.reject('screen','gain',[.1])
    def test_screen_finite(self): self.reject('screen','gain',[float('nan')]*8)
    def test_not_always_beating_control(self):
        self.assertEqual(sum(x['margin']<x['binary'] for x in self.data['women']['years']),2)
    def test_all_years_beat_core(self):
        self.assertTrue(all(x['margin']<x['core'] for x in self.data['women']['years']))

if __name__=='__main__': unittest.main()
