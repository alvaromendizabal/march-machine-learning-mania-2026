"""Pre-announcement outcomes are never inputs: bracket eligibility is not actual venue.

The frozen definition supports women's complete 64-team brackets, 2013--2019.
The top-16-hosting policy feature is active only in 2015--2019. Earlier zeros
mean policy inapplicable, NOT that women's games were all neutral before 2015.
"""
from __future__ import annotations
from itertools import combinations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent / 'frozen'))
import shot_features as sf

KEYS = ['Gender','Season','Team1ID','Team2ID']
BASE = list(sf.ANCHOR_COLS)
STATUS = ['diff_top4_status']
HOST = ['host_eligibility_contrast']
SCALED = ['host_eligibility_volatility_scaled']
ALL = BASE + STATUS + HOST + SCALED
RECIPES = {'anchor':BASE, 'seed_status':BASE+STATUS,
           'host_context':BASE+STATUS+HOST, 'host_context_scaled':ALL}
PODS = {s:pod for pod,ss in enumerate([(1,16,8,9),(4,13,5,12),(3,14,6,11),(2,15,7,10)],1) for s in ss}
PARAMETERS = {'first_policy_season':2015,'last_supported_season':2019,
              'volatility_unit':10.,'variance_floor':1.,'field_size':64,
              'actual_venue_inferred':False,'archived_venue_overrides':False}
require = sf.require


def seed_panel(seeds:pd.DataFrame, season:int) -> pd.DataFrame:
    require(isinstance(season,(int,np.integer)) and 2013<=season<=2019,'Unsupported season: no automatic extrapolation past 2019')
    require({'Season','TeamID','Seed'}.issubset(seeds),'Seed schema missing')
    # Ignore non-selected seasons before interpreting seed text.
    current=seeds.loc[seeds.Season.eq(season),['Season','TeamID','Seed']].copy()
    require(len(current)==64 and not current.isna().any().any(),'Expected complete 64-team women\'s field')
    require(not current.TeamID.duplicated().any() and not current.Seed.duplicated().any(),'Duplicate team or bracket seed')
    token=current.Seed.astype(str).str.extract(r'^([WXYZ])(0[1-9]|1[0-6])$')
    require(not token.isna().any().any(),'Unsupported seed spelling/play-in structure')
    current['region']=token[0];current['seed_number']=token[1].astype(int)
    require(set(current.region)==set('WXYZ'),'Four bracket regions required')
    for _,g in current.groupby('region'):
        require(set(g.seed_number)==set(range(1,17)),'Region must contain every seed 1--16')
    require(np.isfinite(current.TeamID.to_numpy(float)).all() and (current.TeamID>0).all() and
            (current.TeamID%1==0).all(),'Invalid team IDs')
    current['pod']=current.seed_number.map(PODS).astype(int)
    current['top4']=current.seed_number.le(4).astype(int)
    return current.sort_values('TeamID').reset_index(drop=True)


def pair_features(base:pd.DataFrame,seeds:pd.DataFrame,pairs:pd.DataFrame):
    """Feature function accepts keys only, never target, game dates, cities or WLoc."""
    require(set(pairs.columns)==set(KEYS),'Pass matchup keys only: outcomes/dates/venues forbidden')
    require(len(pairs)>0 and pairs.Gender.eq('W').all(),'Women-only feature definition')
    require(not pairs.duplicated(KEYS).any() and (pairs.Team1ID!=pairs.Team2ID).all(),'Duplicate/self pair')
    season_values=sorted(pairs.Season.unique().tolist())
    panels=pd.concat([seed_panel(seeds,int(s)) for s in season_values],ignore_index=True)
    # Use the same frozen base construction, including its support checks.
    x=sf.pair_features(base,pairs)[KEYS+BASE].copy()
    j=pairs[KEYS].reset_index(drop=True).copy()
    for side,team in [('a','Team1ID'),('b','Team2ID')]:
        p=panels.rename(columns={'TeamID':team,**{c:side+'_'+c for c in ['Seed','region','seed_number','pod','top4']}})
        j=j.merge(p,on=['Season',team],how='left',validate='many_to_one')
        b=base[['Gender','Season','TeamID','seed','margin_sd']].rename(columns={'TeamID':team,'seed':side+'_base_seed','margin_sd':side+'_margin_sd'})
        j=j.merge(b,on=['Gender','Season',team],how='left',validate='many_to_one')
        require(j[side+'_seed_number'].notna().all(),'Unseeded team in bracket pair')
        require(np.array_equal(j[side+'_seed_number'],j[side+'_base_seed']),'Raw bracket seed disagrees with cached snapshot')
        sd=j[side+'_margin_sd'].to_numpy(float)
        require(np.isfinite(sd).all() and (sd>=0).all(),'Invalid margin variability')
    same=(j.a_region==j.b_region)&(j.a_pod==j.b_pod)
    active=j.Season.ge(PARAMETERS['first_policy_season'])
    signed=(j.a_top4-j.b_top4).astype(float)
    h=signed*same.astype(float)*active.astype(float)
    scale=PARAMETERS['volatility_unit']/np.sqrt(j.a_margin_sd**2+j.b_margin_sd**2+PARAMETERS['variance_floor'])
    x[STATUS[0]]=signed;x[HOST[0]]=h;x[SCALED[0]]=h*scale
    require(np.isfinite(x[ALL].to_numpy()).all(),'Nonfinite features')
    diag=j[KEYS].copy();diag['seed_A']=j.a_seed_number;diag['seed_B']=j.b_seed_number
    diag['same_region']=j.a_region.eq(j.b_region);diag['same_pod']=same
    diag['policy_active']=active;diag['eligibility_contrast']=h
    diag['one_top4']=signed.ne(0);diag['volatility_scale']=scale
    diag['cohort']=np.where(~active,'pre_policy_not_encoded',np.where(h.ne(0),'early_pod_top4_eligibility','other_pair'))
    return x,diag


def build_season(base,seeds,season):
    p=seed_panel(seeds,season)
    pairs=pd.DataFrame(combinations(p.TeamID.to_list(),2),columns=['Team1ID','Team2ID'])
    pairs.insert(0,'Season',season);pairs.insert(0,'Gender','W')
    x,d=pair_features(base,seeds,pairs)
    reverse,_=pair_features(base,seeds,pairs.rename(columns={'Team1ID':'Team2ID','Team2ID':'Team1ID'}))
    require(np.max(np.abs(x[ALL].to_numpy()+reverse[ALL].to_numpy()))<1e-10,'Broken team-swap antisymmetry')
    coverage={'Gender':'W','Season':season,'field_teams':len(p),'all_pairs':len(x),
              'same_pod_pairs':int(d.same_pod.sum()),'eligible_pairs':int(d.eligibility_contrast.ne(0).sum()),
              'policy_active':season>=2015,'actual_venue_measured':False,
              'feature_swap_error':float(np.max(np.abs(x[ALL].to_numpy()+reverse[ALL].to_numpy())))}
    require(len(x)==2016 and coverage['same_pod_pairs']==96,'Unexpected bracket pair counts')
    require(coverage['eligible_pairs']==(48 if season>=2015 else 0),'Unexpected hosting-eligibility support')
    return x,d,coverage


def registry():
    rows=[{'feature':f,'family':'anchor','novel':False,'definition':'Unchanged frozen reference difference'} for f in BASE]
    rows += [
      {'feature':STATUS[0],'family':'seed_status_control','novel':False,'definition':'I(seed_A<=4)-I(seed_B<=4); all supported years'},
      {'feature':HOST[0],'family':'bracket_eligibility','novel':True,'definition':'Status difference times same announced region/pod times I(2015<=season<=2019)'},
      {'feature':SCALED[0],'family':'eligibility_volatility','novel':True,'definition':'Eligibility contrast * 10 / sqrt(margin_sd_A^2+margin_sd_B^2+1)'}]
    frame=pd.DataFrame(rows)
    frame['available_asof']='After field announcement, before first NCAA game; regular-season snapshots through day132'
    frame['actual_venue_claim']=False;frame['outcomes_used_for_features']=False
    frame['swap_parity']=-1
    return frame
