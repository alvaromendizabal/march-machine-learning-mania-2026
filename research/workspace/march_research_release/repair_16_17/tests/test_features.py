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
                   'Stl':int(rng.integers(3,9)),'Blk':int(rng.integers(1,6))}
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
    def test_separate_round_features(self):self.assertFalse(set(f.FEATURES['16'])&set(f.FEATURES['17']))
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
        with self.assertRaises(ValueError):f.recipes('18')
    def test_long_game_count(self):
        c,d=small_games();self.assertEqual(len(f.legal_long(c,d,2013,'16')),2*len(c))
    def test_orientation_home_sum(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'16');self.assertEqual(l.home.sum(),0)
    def test_nonsteal_identity(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'16');np.testing.assert_array_equal(l.nonsteal_TO+l.opp_Stl,l.TO)
    def test_negative_nonsteal_rejected(self):
        c,d=small_games();d.loc[0,'LStl']=100
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'16')
    def test_missing_steals_rejected(self):
        c,d=small_games()
        with self.assertRaises(ValueError):f.legal_long(c,d.drop(columns='WStl'),2013,'16')
    def test_missing_blocks_rejected(self):
        c,d=small_games()
        with self.assertRaises(ValueError):f.legal_long(c,d.drop(columns='WBlk'),2013,'17')
    def test_future_day_excluded_before_validation(self):
        c,d=small_games();future=d.iloc[[0]].copy();future.DayNum=133;future.WStl=-100
        a=f.legal_long(c,d,2013,'16');b=f.legal_long(c,pd.concat([d,future]),2013,'16');pd.testing.assert_frame_equal(a,b)
    def test_future_season_excluded(self):
        c,d=small_games();future=d.copy();future.Season=2026;future.WBlk=-2
        pd.testing.assert_frame_equal(f.legal_long(c,d,2013,'17'),f.legal_long(c,pd.concat([d,future]),2013,'17'))
    def test_shuffle_invariance(self):
        c,d=small_games();pd.testing.assert_frame_equal(f.legal_long(c,d,2013,'16'),f.legal_long(c.sample(frac=1,random_state=1),d.sample(frac=1,random_state=2),2013,'16'))
    def test_duplicate_physical_game_rejected(self):
        c,d=small_games()
        with self.assertRaises(ValueError):f.legal_long(c,pd.concat([d,d.iloc[[0]]]),2013,'16')
    def test_compact_score_mismatch_rejected(self):
        c,d=small_games();d.loc[0,'WScore']+=1
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'16')
    def test_fractional_counts_rejected(self):
        c,d=small_games();d['WStl']=d.WStl.astype(float);d.loc[0,'WStl']=.5
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'16')
    def test_nan_rejected(self):
        c,d=small_games();d.loc[0,'WFTA']=np.nan
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'17')
    def test_two_point_attempts(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'17');np.testing.assert_array_equal(l.two_attempts,l.FGA-l.FGA3)
    def test_bad_three_point_subset(self):
        c,d=small_games();d.loc[0,'WFGA3']=70
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'17')
    def test_illegal_location(self):
        c,d=small_games();d.loc[0,'WLoc']='X'
        with self.assertRaises(ValueError):f.legal_long(c,d,2013,'17')
    def test_solve_certificate_and_serialization(self):
        c,d=small_games()
        for r in f.FAMILIES:
            l=f.legal_long(c,d,2013,r)
            for t in f.FAMILIES[r]:
                table,m,diag=f.fit_target(l,t,sorted(l.TeamID.unique()))
                self.assertLessEqual(diag['normal_equation_relative_error'],1e-9)
                json.dumps(m,allow_nan=False);json.dumps(diag,allow_nan=False)
                self.assertTrue(np.isfinite(table.to_numpy()).all())
    def test_sign_convention(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'16');t,m,_=f.fit_target(l,'steal_turnovers',sorted(l.TeamID.unique()));k=len(t)
        np.testing.assert_allclose(t.adjusted_steal_turnovers_offense,-100*np.array(m['coefficients'][:k]))
        np.testing.assert_allclose(t.adjusted_steal_turnovers_defense,100*np.array(m['coefficients'][k:2*k]))
    def test_input_immutable(self):
        c,d=small_games();cc=c.copy(deep=True);dd=d.copy(deep=True);l=f.legal_long(c,d,2013,'16');f.fit_target(l,'steal_turnovers',sorted(l.TeamID.unique()))
        pd.testing.assert_frame_equal(c,cc);pd.testing.assert_frame_equal(d,dd)
    def test_unobserved_seeded_team_rejected(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'16')
        with self.assertRaises(ValueError):f.fit_target(l,'steal_turnovers',[9999])
    def test_support_gate(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'16')
        with self.assertRaises(ValueError):f.fit_target(l,'steal_turnovers',sorted(l.TeamID.unique()),minimum_exposure=1e9)
    def test_invalid_penalty(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'16')
        with self.assertRaises(ValueError):f.fit_target(l,'steal_turnovers',sorted(l.TeamID.unique()),alpha=0)
    def test_control_shrinkage_formula(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'16');tab,m,_=f.fit_target(l,'steal_turnovers',sorted(l.TeamID.unique()))
        sums=l.groupby('TeamID')[['opp_Stl','possessions']].sum()
        expected=-100*(sums.opp_Stl+100*m['league_rate'])/(sums.possessions+100)
        np.testing.assert_allclose(tab.rate_steal_turnovers_offense,expected.to_numpy())
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
        base,p,t=pair_fixture('16');out,_,_,_=f.pair_tables(base,p,t,'16')
        copied=pd.read_csv(io.StringIO(out.to_csv(index=False,float_format='%.17g')),float_precision='round_trip')
        np.testing.assert_array_equal(copied[f.BASE+f.FEATURES['16']].to_numpy(),out[f.BASE+f.FEATURES['16']].to_numpy())
    def test_bad_pair_order_rejected(self):
        base,p,t=pair_fixture('16');p.loc[0,['Team1ID','Team2ID']]=p.loc[0,['Team2ID','Team1ID']].to_numpy()
        with self.assertRaises(ValueError):f.pair_tables(base,p,t,'16')
    def test_registry_does_not_count_controls(self):
        for r in f.FAMILIES:self.assertEqual(int(f.registry(r).new_candidate.sum()),4)


class QuarantineTests(unittest.TestCase):
    def test_invalid_physical_games_excluded_in_both_orientations(self):
        c,d=small_games();cc=[];dd=[]
        # Distinct artificial days increase the denominator without duplicate game identities.
        for shift in range(5):
            x=c.copy();z=d.copy();x.DayNum+=shift;z.DayNum+=shift;cc.append(x);dd.append(z)
        c=pd.concat(cc,ignore_index=True);d=pd.concat(dd,ignore_index=True)
        d.loc[0,'LStl']=d.loc[0,'WTO']+1
        l=f.legal_long(c,d,2013,'16')
        self.assertEqual(len(l),2*(len(d)-1));self.assertEqual(l.attrs['turnover_quality']['excluded_physical_games'],1)
        self.assertTrue((l.nonsteal_TO>=0).all())
    def test_quality_does_not_mutate_source(self):
        c,d=small_games();before=d.copy(deep=True);f.turnover_quality(d);pd.testing.assert_frame_equal(before,d)
    def test_negative_counts_still_rejected(self):
        c,d=small_games();d.loc[0,'LStl']=-1
        with self.assertRaises(ValueError):f.turnover_quality(d)
    def test_seeded_quarantine_limit_is_separate(self):
        c,d=small_games();l=f.legal_long(c,d,2013,'16');ids=list(l.TeamID.unique())
        l.attrs['turnover_team_quality']=[{'TeamID':t,'excluded_fraction':.06} for t in ids]
        with self.assertRaises(ValueError):f.seeded_quality_gate(l,ids)

if __name__=='__main__':unittest.main()
