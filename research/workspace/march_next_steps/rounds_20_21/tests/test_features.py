"""Prepared unit tests. Nothing in this file has been executed by the assistant."""
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
import feature_rounds as f
from research_io import sf
import consensus_reference as cf
from fixtures import toy_data

class ContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,cls.d,cls.seeds,_,_,cls.ranks=toy_data()
        cls.g=f.legal_long(cls.c,cls.d,2013,'20')
        games,long=cf.reference_inputs(cls.c,cls.d,2013)
        cls.base=cf.finish_reference(sf.compact_strength(games),sf.standard_control(long),long,cls.seeds,2013)
        panel,_=cf.publication_panel(cls.ranks,2013)
        cls.pairs=cf.build_matchups(cls.base,panel)[0]
    def test_candidates_equal_volume(self):
        self.assertEqual(len(f.FEATURES['20']),4);self.assertEqual(len(f.FEATURES['21']),4)
    def test_six_recipes_each(self):
        for r in ['20','21']:self.assertEqual([len(x) for x in f.recipes(r).values()],[17,21,23,23,25,25])
    def test_unknown_round_rejected(self):
        with self.assertRaises(ValueError):f.recipes('22')
    def test_future_year_rejected(self):
        with self.assertRaises(ValueError):f.legal_long(self.c,self.d,2026,'20')
    def test_two_rows_per_game(self):self.assertEqual(len(self.g),2*len(self.d.loc[self.d.Season.eq(2013)]))
    def test_order_independent(self):
        pd.testing.assert_frame_equal(self.g,f.legal_long(self.c.sample(frac=1,random_state=7),self.d.sample(frac=1,random_state=3),2013,'20'))
    def test_future_regular_rows_ignored(self):
        d=self.d.copy();d.loc[d.Season.gt(2013),'WFGM']=-900
        pd.testing.assert_frame_equal(self.g,f.legal_long(self.c,d,2013,'20'))
    def test_post_cutoff_rows_ignored(self):
        row=self.d.loc[self.d.Season.eq(2013)].iloc[[0]].copy();row.DayNum=150;row.WFGM=-4
        pd.testing.assert_frame_equal(self.g,f.legal_long(self.c,pd.concat([self.d,row]),2013,'20'))
    def test_duplicate_game_rejected(self):
        d=pd.concat([self.d,self.d.iloc[[0]]])
        with self.assertRaises(ValueError):f.legal_long(self.c,d,2013,'20')
    def test_compact_mismatch_rejected(self):
        d=self.d.copy();d.loc[0,'WScore']+=1
        with self.assertRaises(ValueError):f.legal_long(self.c,d,2013,'20')
    def test_missing_box_rejected(self):
        with self.assertRaises(ValueError):f.legal_long(self.c,self.d.drop(columns='WDR'),2013,'20')
    def test_negative_box_rejected(self):
        d=self.d.copy();d.loc[0,'WTO']=-1
        with self.assertRaises(ValueError):f.legal_long(self.c,d,2013,'20')
    def test_makes_exceed_attempts_rejected(self):
        d=self.d.copy();d.loc[0,'WFGM']=999
        with self.assertRaises(ValueError):f.legal_long(self.c,d,2013,'20')
    def test_three_subset_rejected(self):
        d=self.d.copy();d.loc[0,'WFGA3']=999
        with self.assertRaises(ValueError):f.legal_long(self.c,d,2013,'20')
    def test_zero_possessions_rejected(self):
        d=self.d.copy();d.loc[0,'WOR']=1000
        with self.assertRaises(ValueError):f.legal_long(self.c,d,2013,'20')
    def test_bad_overtime_rejected(self):
        d=self.d.copy();d.loc[0,'NumOT']=-1
        with self.assertRaises(ValueError):f.legal_long(self.c,d,2013,'20')
    def test_overtime_pace_conversion(self):
        d=self.d.copy();d.loc[0,'NumOT']=1;g=f.legal_long(self.c,d,2013,'20')
        row=g.loc[g.NumOT.eq(1)].iloc[0]
        self.assertAlmostEqual(row.pace,row.possessions*40/45)
    def test_profiles_finite(self):self.assertTrue(np.isfinite(f.profiles(self.g).to_numpy()).all())
    def test_profiles_variance_positive(self):self.assertTrue(f.profiles(self.g).shot_variance.gt(0).all())
    def test_context20_swap(self):
        p=f.profiles(self.g);a=np.array([1101,1102]);b=np.array([1103,1104]);g=np.array([2.,-3.]);r=np.array([.4,-.3])
        np.testing.assert_allclose(f.context20(p,a,b,g,r),-f.context20(p,b,a,-g,-r),rtol=0,atol=1e-12)
    def test_zero_gap_zero_context(self):
        p=f.profiles(self.g);z=f.context20(p,np.array([1101]),np.array([1102]),np.array([0.]),np.array([0.]));np.testing.assert_array_equal(z,np.zeros_like(z))
    def test_neutral_context_zero(self):
        p=f.profiles(self.g);p.pace_mean=70.;p.shot_variance=2.
        np.testing.assert_allclose(f.context20(p,np.array([1101]),np.array([1102]),np.array([2.]),np.array([1.])),0.)
    def test_registry_counts(self):
        for r in ['20','21']:self.assertEqual(int(f.registry(r).new_candidate.sum()),4)
    def test_baseline_unchanged(self):
        for r in ['20','21']:
            out,*_=f.build_snapshot(self.base,self.pairs,self.g,r)
            pd.testing.assert_frame_equal(out[cf.KEYS+f.BASE],self.pairs[cf.KEYS+f.BASE])
    def test_duplicate_control_contains_no_new_info(self):
        for r in ['20','21']:
            out,*_=f.build_snapshot(self.base,self.pairs,self.g,r)
            np.testing.assert_array_equal(out[f.DUPLICATE].to_numpy(),out[f.CONTROLS[r]].to_numpy())
    def test_builds_finite_both(self):
        for r in ['20','21']:
            out,_,cov,_,diag=f.build_snapshot(self.base,self.pairs,self.g,r)
            self.assertTrue(np.isfinite(out[f.FEATURES[r]].to_numpy()).all());self.assertEqual(diag.rating_fits.sum(),0)
    def test_missing_seeded_profile_stops(self):
        with self.assertRaises(ValueError):f.build_snapshot(self.base,self.pairs,self.g.loc[self.g.TeamID.ne(1101)],'20')
    def test_too_little_seeded_support_stops(self):
        keep=self.g.loc[self.g.TeamID.ne(1101)];few=self.g.loc[self.g.TeamID.eq(1101)].head(4)
        with self.assertRaises(ValueError):f.build_snapshot(self.base,self.pairs,pd.concat([keep,few]),'20')
    def test_invalid_pairs_stops(self):
        pair=pd.concat([self.pairs,self.pairs.iloc[[0]]])
        with self.assertRaises(ValueError):f.build_snapshot(self.base,pair,self.g,'20')

class StyleResponseTests(unittest.TestCase):
    def setUp(self):
        self.p=pd.DataFrame({'pace':[0.,.2,1.,2.],'three':[0.,.1,.2,.5]},index=[1,2,3,4])
        self.g=pd.DataFrame({'OpponentID':[1,2,3],'offense':[90.,100.,120.],'defense':[-110.,-100.,-80.]})
    def test_direct_response_excluded(self):
        a=f.weighted_response(self.g,2,self.p,['pace','three'],np.ones(2))[0]
        g=self.g.copy();g.loc[g.OpponentID.eq(2),['offense','defense']]=999
        np.testing.assert_allclose(a,f.weighted_response(g,2,self.p,['pace','three'],np.ones(2))[0])
    def test_zero_neighbors_returns_neutral_with_zero_support(self):
        p=self.p.copy();p.loc[4]=100
        value,support,count=f.weighted_response(self.g,4,p,['pace','three'],np.ones(2))
        np.testing.assert_array_equal(value,0.);self.assertEqual(support,0);self.assertEqual(count,0)
    def test_no_other_opponents_returns_zero(self):
        v,s,n=f.weighted_response(self.g.iloc[[0]],1,self.p,['pace','three'],np.ones(2));np.testing.assert_array_equal(v,0.);self.assertEqual(s,0)
    def test_translation_invariance_of_response(self):
        a=f.weighted_response(self.g,4,self.p,['pace','three'],np.ones(2))[0]
        g=self.g.copy();g[['offense','defense']]+=15
        np.testing.assert_allclose(a,f.weighted_response(g,4,self.p,['pace','three'],np.ones(2))[0])
    def test_vectorized_matches_scalar(self):
        v,s,n=f.response_matrix(self.g,[1,2,3,4],self.p,['pace','three'],np.ones(2))
        for i,t in enumerate([1,2,3,4]):
            vv,ss,nn=f.weighted_response(self.g,t,self.p,['pace','three'],np.ones(2))
            np.testing.assert_allclose(v[i],vv,atol=1e-12);self.assertAlmostEqual(s[i],ss);self.assertEqual(n[i],nn)
    def test_more_shrinkage_smaller_response(self):
        a=f.weighted_response(self.g,4,self.p,['pace','three'],np.ones(2),prior=5)[0]
        b=f.weighted_response(self.g,4,self.p,['pace','three'],np.ones(2),prior=50)[0]
        self.assertTrue((abs(b)<=abs(a)).all())
    def test_empty_vectorized_shape(self):
        v,s,n=f.response_matrix(self.g.iloc[:0],[1,2],self.p,['pace','three'],np.ones(2));self.assertEqual(v.shape,(2,2));self.assertEqual(s.sum(),0)

if __name__=='__main__':unittest.main()
