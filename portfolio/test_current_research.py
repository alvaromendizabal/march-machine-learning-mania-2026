import copy, unittest
from current_research import load,validate
class Tests(unittest.TestCase):
 def setUp(self):self.d=load()
 def reject(self,section,key,value):
  d=copy.deepcopy(self.d);d[section][key]=value
  with self.assertRaises(ValueError):validate(d)
 def test_valid(self):self.assertEqual(validate(self.d)['schema'],1)
 def test_incumbent(self):self.reject('scored','champion',.09)
 def test_candidate(self):self.reject('scored','women_candidate',.09)
 def test_promotion(self):self.reject('scored','decision','PROMOTE')
 def test_champion_ref(self):self.reject('scored','champion_ref','1')
 def test_women_ref(self):self.reject('scored','women_ref','1')
 def test_champion_hash(self):self.reject('scored','champion_sha256','x')
 def test_women_hash(self):self.reject('scored','women_sha256','z'*64)
 def test_source_hash(self):self.reject('source','sha256','0')
 def test_no_new_fits(self):self.reject('replay','new_tree_fits',1)
 def test_no_new_upload(self):self.reject('replay','new_submissions',1)
 def test_reused(self):self.reject('replay','reused_tree_fits',0)
 def test_years(self):self.reject('women_historical','years',self.d['women_historical']['years'][:2])
 def test_pooled(self):self.reject('women_historical','margin',.09)
 def test_protected_rows(self):self.reject('preservation','men_rows',0)
 def test_row_count(self):self.reject('preservation','total_rows',1)
 def test_not_always_better(self):self.assertEqual(sum(x['margin']<x['binary'] for x in self.d['women_historical']['years']),2)
 def test_historical_not_score(self):self.assertNotEqual(self.d['women_historical']['margin'],self.d['scored']['women_candidate'])
 def test_nan(self):
  d=copy.deepcopy(self.d);d['women_historical']['years'][0]['margin']=float('nan')
  with self.assertRaises(ValueError):validate(d)
 def test_positive_champion_gap(self):self.assertGreater(self.d['scored']['benchmark']-self.d['scored']['champion'],0)
if __name__=='__main__':unittest.main()
