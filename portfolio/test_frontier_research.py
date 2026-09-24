import copy, math, unittest
from frontier_research import load, validate

class Tests(unittest.TestCase):
    def setUp(self): self.d=load()
    def reject(self,path,value):
        d=copy.deepcopy(self.d); target=d
        for key in path[:-1]: target=target[key]
        target[path[-1]]=value
        with self.assertRaises(ValueError): validate(d)
    def test_valid(self): self.assertEqual(validate(self.d)["schema"],1)
    def test_champion(self): self.reject(["scores","retained_private_champion"],0.09)
    def test_champion_ref(self): self.reject(["scores","retained_submission_ref"],"x")
    def test_target(self): self.reject(["scores","stretch_target"],0.08)
    def test_candidate_status(self): self.reject(["latest_candidate","decision"],"SCORED")
    def test_candidate_unscored(self): self.reject(["latest_candidate","candidate_score"],0.1)
    def test_selected_family(self): self.reject(["latest_candidate","selected_family"],"all_residual")
    def test_selection_gain(self): self.reject(["latest_candidate","selection_gain"],0.0)
    def test_selection_wins(self): self.reject(["latest_candidate","selection_wins"],6)
    def test_stability(self): self.reject(["latest_candidate","worst_season_gain"],-0.01)
    def test_rejected_panel(self): self.reject(["latest_candidate","all_residual_worst_season_gain"],-0.001)
    def test_scope(self): self.reject(["latest_candidate","protected_rows"],1)
    def test_women(self): self.reject(["latest_candidate","women_rows_byte_identical"],0)
    def test_outcomes_boundary(self): self.reject(["latest_candidate","known_2026_outcomes_used"],True)
    def test_market_selection_boundary(self): self.reject(["latest_candidate","market_inputs_used_for_selection"],True)
    def test_market_training_boundary(self): self.reject(["latest_candidate","market_inputs_used_for_training"],True)
    def test_provenance(self): self.reject(["provenance","independently_rebuilt_raw_2026_market_observations"],True)
    def test_matrix(self):
        d=copy.deepcopy(self.d); d["reproduction_matrix"]=d["reproduction_matrix"][:2]
        with self.assertRaises(ValueError): validate(d)
    def test_hash(self): self.reject(["latest_candidate","candidate_sha256"],"x")
    def test_gap_arithmetic(self): self.assertAlmostEqual(self.d["scores"]["retained_private_champion"]-self.d["scores"]["stretch_target"],self.d["scores"]["remaining_absolute_reduction"],12)

if __name__=="__main__": unittest.main()
