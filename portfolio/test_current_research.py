import copy, unittest
from current_research import load, validate
class Tests(unittest.TestCase):
    def setUp(self): self.d=load()
    def reject(self,path,value):
        d=copy.deepcopy(self.d); target=d
        for key in path[:-1]: target=target[key]
        target[path[-1]]=value
        with self.assertRaises(ValueError): validate(d)
    def test_valid(self): self.assertEqual(validate(self.d)["schema"],1)
    def test_champion_score(self): self.reject(["scored","champion","score"],0.09)
    def test_champion_ref(self): self.reject(["scored","champion","ref"],"x")
    def test_full_market(self): self.reject(["scored","full_market","score"],0.1)
    def test_r1_market(self): self.reject(["scored","r1_market","score"],0.1)
    def test_decision(self): self.reject(["scored","champion","decision"],"OTHER")
    def test_disjoint(self): self.reject(["decomposition","disjoint"],False)
    def test_interval(self): self.reject(["decomposition","inferred_interval"],[0.1,0.2])
    def test_rows(self): self.reject(["integrity","rows"],1)
    def test_changed(self): self.reject(["integrity","changed_rows"],1)
    def test_protected(self): self.reject(["integrity","protected_rows"],1)
    def test_women(self): self.reject(["integrity","women_rows_unchanged"],0)
    def test_hash(self): self.reject(["scored","champion","sha256"],"x")
    def test_zero_fits(self): self.reject(["integrity","tree_fits"],1)
    def test_one_upload(self): self.reject(["integrity","upload_attempts"],2)
    def test_no_followup(self): self.reject(["integrity","automatic_followups"],1)
    def test_arithmetic(self):
        s=self.d["scored"]; expected=s["margin_release"]["score"]+s["full_market"]["score"]-s["r1_market"]["score"]
        self.assertAlmostEqual(expected,self.d["decomposition"]["inferred_score"],12)
if __name__=="__main__": unittest.main()
