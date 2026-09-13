"""Opponent/site-adjusted late-season form relative to day-100 frozen ratings.

No tournament results are accepted by this module. The residuals are descriptive
surprises relative to an earlier model, not causal effects, identified momentum,
player availability measurements, or calibrated probabilities.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits
sys.path.insert(0, str(Path(__file__).resolve().parent/'frozen'))
import shot_features as sf

PARAMETERS = {'early_cutoff':100,'midpoint':116,'snapshot_cutoff':132,
              'half_life_days':14.0,'prior_games':5.0,'ridge_alpha':20.0,
              'max_possession_gap':0.10}
LEVEL = ['late_offense_surprise','late_defense_surprise']
CHANGE = ['late_offense_change','late_defense_change']
FEATURES = LEVEL + CHANGE
LEVEL_COLS = ['diff_'+c for c in LEVEL]
CHANGE_COLS = ['diff_'+c for c in CHANGE]
ALL_COLS = LEVEL_COLS + CHANGE_COLS
require = sf.require


def long_legal(detailed: pd.DataFrame, season: int, cutoff: int) -> pd.DataFrame:
    g = sf.legal_games(detailed, season, detailed=True, cutoff=cutoff)
    long = sf.long_games(g,detailed=True)
    # Clean is computed symmetrically from both teams' possession estimates.
    return long.loc[long.clean].sort_values(['DayNum','TeamID','OpponentID']).reset_index(drop=True)


def fit_early(detailed: pd.DataFrame, season: int) -> dict:
    """One regular-season ridge fit. Nothing after day 100 enters the design/target."""
    require(2013 <= season <= 2019, 'This stage is limited to 2013-2019')
    g=long_legal(detailed,season,PARAMETERS['early_cutoff'])
    require(len(g)>0,'No clean early regular-season games')
    teams=np.sort(pd.unique(g[['TeamID','OpponentID']].to_numpy().ravel()))
    lookup={int(t):i for i,t in enumerate(teams)}; n,k=len(g),len(teams)
    x=sparse.csr_matrix((np.r_[np.ones(2*n),g.home.to_numpy(float)],
       (np.tile(np.arange(n),3),np.r_[g.TeamID.map(lookup),g.OpponentID.map(lookup)+k,np.full(n,2*k)])),shape=(n,2*k+1))
    model=Ridge(alpha=PARAMETERS['ridge_alpha'],fit_intercept=True,solver='lsqr',tol=1e-8)
    with threadpool_limits(limits=2):model.fit(x,100*g.points/g.possessions)
    require(np.isfinite(model.coef_).all() and np.isfinite(model.intercept_), 'Invalid early ratings')
    return {'Season':int(season),'trained_through_day':100,'max_training_day':int(g.DayNum.max()),
      'team_ids':[int(t) for t in teams],'offense':model.coef_[:k].tolist(),
      'allowance':model.coef_[k:2*k].tolist(),'home_effect':float(model.coef_[-1]),
      'intercept':float(model.intercept_),'alpha':PARAMETERS['ridge_alpha'],
      'early_physical_games':len(g)//2,'rating_fits':1,
      'early_team_games':{str(int(t)):int(n) for t,n in g.groupby('TeamID').size().items()}}


def late_residuals(detailed: pd.DataFrame, season: int, early: dict) -> pd.DataFrame:
    require(early['Season']==season and early['trained_through_day']==100, 'Wrong early model')
    allg=long_legal(detailed,season,132)
    g=allg.loc[allg.DayNum.gt(100)].copy()
    require(not g.empty, 'No clean late games; cannot investigate temporal form')
    off=dict(zip(early['team_ids'],early['offense']));allow=dict(zip(early['team_ids'],early['allowance']))
    g['known_early'] = g.TeamID.isin(off)&g.OpponentID.isin(off)
    g['expected_for']=early['intercept']+g.TeamID.map(off)+g.OpponentID.map(allow)+early['home_effect']*g.home
    g['expected_against']=early['intercept']+g.OpponentID.map(off)+g.TeamID.map(allow)-early['home_effect']*g.home
    g['offense_surprise']=100*g.points/g.possessions-g.expected_for
    # Positive defense surprise denotes allowing less than the earlier expectation.
    g['defense_surprise']=g.expected_against-100*g.allowed/g.possessions
    g['weight']=0.5**((132-g.DayNum.to_numpy(float))/PARAMETERS['half_life_days'])
    return g[['TeamID','OpponentID','DayNum','known_early','weight','offense_surprise','defense_surprise']].reset_index(drop=True)


def build_snapshot(detailed: pd.DataFrame, base: pd.DataFrame, gender: str, season: int, early: dict):
    require(gender in ('M','W'),'Invalid population')
    require(set(base.Gender)=={gender} and set(base.Season)=={season},'Base snapshot season/population mismatch')
    require(base.TeamID.is_unique, 'Duplicate base team')
    g=late_residuals(detailed,season,early)
    require(set(g.TeamID)<=set(base.TeamID),'Late games have teams absent from base snapshot')
    rows=[]
    for team in sorted(base.TeamID):
        observed=g.loc[g.TeamID==team]
        valid=observed.loc[observed.known_early]
        first=valid.loc[valid.DayNum<=116];second=valid.loc[valid.DayNum>116]
        row={'Gender':gender,'Season':season,'TeamID':int(team),
             'early_games':early['early_team_games'].get(str(int(team)),0),
             'late_games':len(valid),'first_window_games':len(first),'second_window_games':len(second),
             'late_weight':float(valid.weight.sum()),'excluded_unknown_opponent_games':len(observed)-len(valid)}
        for side in ('offense','defense'):
            c=side+'_surprise'; prior=PARAMETERS['prior_games']
            # No observations -> explicit zero-centered prior, never an observed zero.
            row['late_'+side+'_surprise']=float((valid[c]*valid.weight).sum()/(valid.weight.sum()+prior))
            row['late_'+side+'_change']=float(second[c].sum()/(len(second)+prior)-first[c].sum()/(len(first)+prior))
        rows.append(row)
    out=pd.DataFrame(rows)
    require(np.isfinite(out[FEATURES].to_numpy(float)).all(),'Nonfinite form feature')
    return out,g


def pair_features(teams: pd.DataFrame,pairs: pd.DataFrame) -> pd.DataFrame:
    keys=['Gender','Season','Team1ID','Team2ID']
    require(set(keys)<=set(pairs), 'Invalid pair keys')
    require((pairs.Team1ID!=pairs.Team2ID).all() and not pairs.duplicated(keys).any(),'Invalid/duplicate matchups')
    require(not teams.duplicated(['Gender','Season','TeamID']).any(),'Duplicate snapshots')
    out=pairs[keys].reset_index(drop=True).copy()
    for side,key in [('a','Team1ID'),('b','Team2ID')]:
        t=teams[['Gender','Season','TeamID']+FEATURES].rename(columns={'TeamID':key,**{c:side+'_'+c for c in FEATURES}})
        out=out.merge(t,on=['Gender','Season',key],how='left',validate='many_to_one')
    for c in FEATURES:out['diff_'+c]=out['a_'+c]-out['b_'+c]
    require(np.isfinite(out[ALL_COLS].to_numpy(float)).all(),'Missing form snapshot for matchup')
    return out[keys+ALL_COLS]


def registry(anchor) -> pd.DataFrame:
    rows=[]
    meanings={LEVEL_COLS[0]:'Shrunken recency-weighted offensive surprise versus day-100 expectation',
       LEVEL_COLS[1]:'Shrunken recency-weighted defensive surprise; higher = better defense',
       CHANGE_COLS[0]:'Offensive surprise in days 117-132 minus days 101-116; both shrunk',
       CHANGE_COLS[1]:'Defensive surprise in days 117-132 minus days 101-116; both shrunk'}
    for c in list(anchor)+ALL_COLS:
        rows.append({'feature':c,'family':'anchor' if c in anchor else 'late_level' if c in LEVEL_COLS else 'late_change',
          'new_candidate':c not in anchor,'description':meanings.get(c,'Frozen existing reference input'),
          'availability':'Regular season through day 132; reference ratings through day 100; anchor seeds at bracket release',
          'swap_parity':-1,'uses_tournament_outcomes':False,
          'missing_policy':'Unknown early matchups excluded; zero-centered five-game prior; support audited',
          'evidence':'Hypothesis; not promoted'})
    return pd.DataFrame(rows)
