"""User-executed correctness tests. All data in this file are synthetic."""
import io,json,unittest
from itertools import combinations
import numpy as np
import pandas as pd
import feature_rounds as f


def small_games(season=2013):
    rng=np.random.default_rng(9216);compact=[];detail=[];ids=np.arange(1101,1109)
    for day in range(10,130,10):
        teams=rng.permutation(ids)
        for a,b in zip(teams[::2],teams[1::2]):
            box={}
            for side in ['W','L']:
                d={'FGA':60,'FGM':29 if side=='W' else 23,'FGA3':21,'FGM3':8 if side=='W' else 5,
                   'FTA':18,'FTM':12,'OR':8,'TO':int(rng.integers(11,16)),
                   'Stl':int(rng.integers(3,9)),'Blk':int(rng.integers(1,6)), 'DR':28,'Ast':int(rng.integers(10,16))}
                box.update({side+k:v for k,v in d.items()})
            g={'Season':season,'DayNum':day,'WTeamID':int(a),'LTeamID':int(b),
               'WScore':78,'LScore':63,'WLoc':str(rng.choice(['H','A','N']))}
            compact.append(g);detail.append(dict(g,**box))
    return pd.DataFrame(compact),pd.DataFrame(detail)


def pair_fixture(rid):
    c,d=small_games();long=f.legal_long(c,d,2013,rid);ids=sorted(set(c.WTeamID)|set(c.LTeamID))
    tables=[f.fit_target(long,t,ids)[0] for t in f.FAMILIES[rid]]
    p=pd.DataFrame([('M',2013,a,b) for a,b in combinations(ids,2)],columns=f.cf.KEYS)
    for j,name in enumerate(f.BASE):p[name]=(p.Team1ID-p.Team2ID)*(j+1)/10
    base=pd.DataFrame({'Gender':'M','Season':2013,'TeamID':ids,'seed':np.arange(1,9),'strength':np.arange(8)})
    return base,p,tables


class FeatureTests(unittest.TestCase):
    def test_exactly_four_candidates_each(self):
        for r in f.FAMILIES:self.assertEqual(len(f.FEATURES[r]),4)
    def test_exactly_four_rate_controls_each(self):
        for r in f.FAMILIES:self.assertEqual(len(f.CONTROLS[r]),4)
    def test_disjoint_candidates_controls(self):
        for r in f.FAMILIES:self.assertFalse(set(f.FEATURES[r])&set(f.CONTROLS[r]))
    def test_separate_round_features(self):self.assertFalse(set(f.FEATURES['18'])&set(f.FEATURES['19']))
    def test_consensus_reference_dimensions(self):self.assertEqual(len(f.BASE),17)
    def test_six_recipes_each(self):
        for r in f.FAMILIES:self.assertEqual(len(f.recipes(r)),6)
    def test_recipe_dimensions(self):
        for r in f.FAMILIES:self.assertEqual([len(c) for c in f.recipes(r).values()],[17,21,23,23,25,25])
    def test_primary_controls_identical(self):
        for r in f.FAMILIES:self.assertEqual(f.recipes(r)['both'][:21],f.recipes(r)['rates'])
    def test_family_removal_does_not_replace_inputs(self):
        for r,(a,b) in f.FAMILIES.items():
            self.assertEqual(set(f.recipes(r)['both'])-set(f.recipes(r)[a]),set(f.FEATURES[r][2:]))
            self.assertEqual(set(f.recipes(r)['both'])-set(f.recipes(r)[b]),set(f.FEATURES[r][:2]))
    def test_year_boundary(self):self.assertNotIn(2026,f.YEARS);self.assertNotIn(2020,f.YEARS)
    def test_bad_round_rejected(self):
        with self.assertRaises(ValueError):f.recipes('99')
    def test_long_game_count(self):
        c,d=small_games();self.assertEqual(len(f.legal_long(c,d,2013,'18')),2*len(c))
    def test_orientation_home_sum(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'18');self.assertEqual(l.home.sum(),0)
    def test_future_day_excluded_before_validation(self):
        c,d=small_games();future=d.iloc[[0]].copy();future.DayNum=133;future.WAst=-100
        a=f.legal_long(c,d,2013,'18');b=f.legal_long(c,pd.concat([d,future]),2013,'18');pd.testing.assert_frame_equal(a,b)
    def test_future_season_excluded(self):
        c,d=small_games();future=d.copy();future.Season=2026;future.WFTM=-2
        pd.testing.assert_frame_equal(f.legal_long(c,d,2013,'19'),f.legal_long(c,pd.concat([d,future]),2013,'19'))
    def test_shuffle_invariance(self):
        c,d=small_games();pd.testing.assert_frame_equal(f.legal_long(c,d,2013,'18'),f.legal_long(c.sample(frac=1,random_state=1),d.sample(frac=1,random_state=2),2013,'18'))
    def test_duplicate_physical_game_rejected(self):
        c,d=small_games()
        with self.assertRaises(ValueError):f.legal_long(c,pd.concat([d,d.iloc[[0]]]),2013,'18')
    def test_compact_score_mismatch_rejected(self):
        c,d=small_games();d.loc[0,'WScore']+=1
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'18')
    def test_fractional_counts_rejected(self):
        c,d=small_games();d['WAst']=d.WAst.astype(float);d.loc[0,'WAst']=.5
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'18')
    def test_nan_rejected(self):
        c,d=small_games();d.loc[0,'WFTA']=np.nan
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'19')
    def test_two_point_attempts(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'19');np.testing.assert_array_equal(l.two_attempts,l.FGA-l.FGA3)
    def test_bad_three_point_subset(self):
        c,d=small_games();d.loc[0,'WFGA3']=70
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'19')
    def test_illegal_location(self):
        c,d=small_games();d.loc[0,'WLoc']='X'
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'19')
    def test_solve_certificate_and_serialization(self):
        c,d=small_games()
        for r in f.FAMILIES:
            l=f.legal_long(c,d,2013,r)
            for t in f.FAMILIES[r]:
                table,m,diag=f.fit_target(l,t,sorted(l.TeamID.unique()))
                self.assertLessEqual(diag['normal_equation_relative_error'],1e-9)
                json.dumps(m,allow_nan=False);json.dumps(diag,allow_nan=False)
                self.assertTrue(np.isfinite(table.to_numpy()).all())
    def test_input_immutable(self):
        c,d=small_games();cc=c.copy(deep=True);dd=d.copy(deep=True);l=f.legal_long(c,d,2013,'18');f.fit_target(l,'offensive_rebounding',sorted(l.TeamID.unique()))
        pd.testing.assert_frame_equal(c,cc);pd.testing.assert_frame_equal(d,dd)
    def test_unobserved_seeded_team_rejected(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'18')
        with self.assertRaises(ValueError):f.fit_target(l,'offensive_rebounding',[9999])
    def test_support_gate(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'18')
        with self.assertRaises(ValueError):f.fit_target(l,'offensive_rebounding',sorted(l.TeamID.unique()),minimum_exposure=1e9)
    def test_invalid_penalty(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'18')
        with self.assertRaises(ValueError):f.fit_target(l,'offensive_rebounding',sorted(l.TeamID.unique()),alpha=0)
    def test_pair_construction(self):
        for r in f.FAMILIES:
            base,p,t=pair_fixture(r);out,prof,cov,s=f.pair_tables(base,p,t,r)
            self.assertEqual(len(out),28);self.assertEqual(cov.candidate_count.iloc[0],4);self.assertEqual(len(prof),8)
            self.assertGreater(s.minimum_exposure.min(),50)
    def test_duplicate_control_is_exact(self):
        for r in f.FAMILIES:
            base,p,t=pair_fixture(r);out,_,_,_=f.pair_tables(base,p,t,r)
            np.testing.assert_array_equal(out[f.DUPLICATE].to_numpy(),out[f.CONTROLS[r]].to_numpy())
    def test_team_difference_antisymmetry(self):
        for r in f.FAMILIES:
            base,p,t=pair_fixture(r);out,_,_,_=f.pair_tables(base,p,t,r)
            lookup=t[0].merge(t[1],on='TeamID').set_index('TeamID')
            for name in f.FEATURES[r]:
                reversed_values=p.Team2ID.map(lookup[name])-p.Team1ID.map(lookup[name])
                np.testing.assert_allclose(out[name]+reversed_values,0,atol=1e-12)
    def test_csv_dtype_roundtrip_is_numeric(self):
        base,p,t=pair_fixture('18');out,_,_,_=f.pair_tables(base,p,t,'18')
        copied=pd.read_csv(io.StringIO(out.to_csv(index=False,float_format='%.17g')),float_precision='round_trip')
        np.testing.assert_array_equal(copied[f.BASE+f.FEATURES['18']].to_numpy(),out[f.BASE+f.FEATURES['18']].to_numpy())
    def test_bad_pair_order_rejected(self):
        base,p,t=pair_fixture('18');p.loc[0,['Team1ID','Team2ID']]=p.loc[0,['Team2ID','Team1ID']].to_numpy()
        with self.assertRaises(ValueError):f.pair_tables(base,p,t,'18')
    def test_registry_does_not_count_controls(self):
        for r in f.FAMILIES:self.assertEqual(int(f.registry(r).new_candidate.sum()),4)


class MechanismTests(unittest.TestCase):
    def test_rebound_opportunities(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'18')
        np.testing.assert_array_equal(l.rebound_opportunities,l.OR+l.opp_DR)
    def test_assists_above_makes_stop(self):
        c,d=small_games();d.loc[0,'WAst']=100
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'18')
    def test_missing_assists_stop(self):
        c,d=small_games()
        with self.assertRaises(ValueError):f.legal_long(c,d.drop(columns='WAst'),2013,'18')
    def test_missing_rebounds_stop(self):
        c,d=small_games()
        with self.assertRaises(ValueError):f.legal_long(c,d.drop(columns='LDR'),2013,'18')
    def test_scoring_share_identity(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'19')
        np.testing.assert_array_equal(l.points,2*l.FGM+l.FGM3+l.FTM)
        np.testing.assert_array_equal(l.three_points,3*l.FGM3)
    def test_scoring_mismatch_stops(self):
        c,d=small_games();c.loc[0,'WScore']+=1;d.loc[0,'WScore']+=1
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'19')
    def test_direction_is_declared(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'18')
        tab,m,_=f.fit_target(l,'offensive_rebounding',sorted(l.TeamID.unique()));k=len(tab)
        np.testing.assert_allclose(tab.adjusted_offensive_rebounding_offense,100*np.array(m['coefficients'][:k]))
        np.testing.assert_allclose(tab.adjusted_offensive_rebounding_defense,-100*np.array(m['coefficients'][k:2*k]))

if __name__=='__main__':unittest.main()
