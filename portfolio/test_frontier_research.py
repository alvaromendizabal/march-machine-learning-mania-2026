import copy, json, unittest
import pandas as pd
from frontier_research import DATA, EXP, OWN, load, validate

class Tests(unittest.TestCase):
    def setUp(self):
        self.d=json.loads(DATA.read_text())
        self.exp=pd.read_csv(EXP)
        self.own=pd.read_csv(OWN)
    def reject_d(self,path,value):
        d=copy.deepcopy(self.d); target=d
        for key in path[:-1]: target=target[key]
        target[path[-1]]=value
        with self.assertRaises(ValueError): validate(d,self.exp,self.own)
    def test_valid(self): self.assertEqual(validate(self.d,self.exp,self.own)[0]["schema"],2)
    def test_canonical(self): self.reject_d(["scores","canonical_aws_reproduced"],0.09)
    def test_pending(self): self.reject_d(["scores","pending_local_candidate"],0.09)
    def test_target(self): self.reject_d(["scores","stretch_target"],0.08)
    def test_scope_men(self): self.reject_d(["scope","men_first_season"],1985)
    def test_scope_women(self): self.reject_d(["scope","women_first_season"],1998)
    def test_post_competition(self): self.reject_d(["scope","post_competition_research"],False)
    def test_pending_not_promoted(self): self.reject_d(["scope","pending_candidate_promoted"],True)
    def test_no_models(self): self.reject_d(["publication","model_fits"],1)
    def test_no_submission(self): self.reject_d(["publication","submissions"],1)
    def test_no_predictions(self): self.reject_d(["publication","private_predictions_published"],True)
    def test_no_weights(self): self.reject_d(["publication","private_weights_published"],True)
    def test_canonical_experiment(self):
        x=self.exp.copy()
        x.loc[x["canonical"].astype("string").str.lower().eq("true"),"audit_brier"]=0.2
        with self.assertRaises(ValueError): validate(self.d,x,self.own)
    def test_pending_experiment(self):
        x=self.exp.copy(); x.loc[x["status"].eq("PENDING_AWS"),"audit_brier"]=0.2
        with self.assertRaises(ValueError): validate(self.d,x,self.own)
    def test_ownership(self):
        x=self.own[self.own["source"]!="WNCAA NET"].copy()
        with self.assertRaises(ValueError): validate(self.d,self.exp,x)
    def test_gap_arithmetic(self):
        self.assertAlmostEqual(self.d["scores"]["canonical_aws_reproduced"]-self.d["scores"]["stretch_target"],self.d["scores"]["remaining_absolute_reduction"],12)

if __name__=="__main__": unittest.main()
