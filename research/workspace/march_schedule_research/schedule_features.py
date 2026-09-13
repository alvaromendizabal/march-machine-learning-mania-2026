"""Seven pre-tournament resume hypotheses. No tournament labels, network calls or fits.

These are custom proxies, NOT NCAA NET, official WAB, or a winning-solution reproduction.
Seeds are only known after the field announcement; this module is not a pre-game
regular-season backtest. All regular-season rows are restricted to the snapshot cutoff.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.special import expit

QUALITY = ['quality_points_won', 'quality_points_won_nonhome', 'quality_bad_losses']
RECORD = ['reference_surplus', 'reference_surplus_nonhome', 'reference_upset_credit', 'reference_bad_loss_cost']
QUALITY_COLS = ['diff_' + n for n in QUALITY]
RECORD_COLS = ['diff_' + n for n in RECORD]
NEW_COLS = QUALITY_COLS + RECORD_COLS
KEYS = ['Gender', 'Season', 'TeamID']
PARAMETERS = {'cutoff_day':132, 'top_seed_max':4, 'top_seed_points':6., 'other_seed_points':4.,
              'unseeded_points':.25, 'reference_quantile':.75, 'home_points':3.,
              'logistic_scale_points':10., 'support_pseudogames':5.}

def require(ok, message):
    if not bool(ok):
        raise ValueError(message)


def build_schedule_snapshot(compact:pd.DataFrame, base:pd.DataFrame, gender:str, season:int,
                            cutoff:int=132) -> tuple[pd.DataFrame,pd.DataFrame]:
    """Reuse cutoff-aligned ridge strengths/seeds; never fit another rating model.

    Outcome-minus-reference-expectation is a descriptive season resume, not a
    calibrated probability, causal team effect, or leave-one-game-out prediction.
    The reference is the 75th percentile of ALL active teams, not a claimed bubble team.
    """
    require(gender in ('M','W') and season<=2021 and cutoff<=132,'Unsupported prediction context')
    require(not any(c in base for c in ['y','WScore','LScore']), 'Base snapshots must be label-free')
    required={'Season','DayNum','WTeamID','LTeamID','WScore','LScore','WLoc'}
    require(required<=set(compact), 'Missing compact schema')
    g=compact.loc[(compact.Season==season)&(compact.DayNum<=cutoff)].copy()
    require(not g.empty,'No legal games')
    require(g[list(required)].notna().all().all(),'Missing regular-season values')
    nums=[c for c in required if c!='WLoc']
    v=g[nums].to_numpy(dtype=float)
    require(np.isfinite(v).all() and (v>=0).all() and np.equal(v,np.floor(v)).all(),'Invalid integral game values')
    require(g.WLoc.isin(['H','A','N']).all() and (g.WScore>g.LScore).all() and (g.WTeamID!=g.LTeamID).all(),'Invalid game')
    identity=pd.DataFrame({'day':g.DayNum,'a':np.minimum(g.WTeamID,g.LTeamID),'b':np.maximum(g.WTeamID,g.LTeamID)})
    require(not identity.duplicated().any(),'Duplicate physical game')
    g=g.sort_values(['DayNum','WTeamID','LTeamID']).reset_index(drop=True)
    required_base=set(KEYS+['strength','seed','games','snapshot_day'])
    require(required_base<=set(base), 'Missing cached base columns')
    b=base.loc[(base.Gender==gender)&(base.Season==season)].copy()
    require(not b.empty and not b.TeamID.duplicated().any(),'Missing/duplicate team snapshot')
    require((b.snapshot_day==cutoff).all(),'Snapshot cutoff mismatch')
    require(np.isfinite(b.strength).all(),'Nonfinite strength')
    seeds=b.seed.dropna()
    require(len(seeds)>0 and seeds.between(1,16).all() and np.equal(seeds,np.floor(seeds)).all(),'Invalid/missing seeded field')
    all_teams=set(g.WTeamID)|set(g.LTeamID)
    require(all_teams==set(b.TeamID),'Cached snapshot and regular-season team universes differ')
    pieces=[]
    for side,other,sgn in [('W','L',1),('L','W',-1)]:
        pieces.append(pd.DataFrame({'TeamID':g[side+'TeamID'],'OpponentID':g[other+'TeamID'],
                                    'DayNum':g.DayNum,'win':float(side=='W'),
                                    'home':sgn*g.WLoc.map({'H':1,'A':-1,'N':0})}))
    long=pd.concat(pieces,ignore_index=True)
    opp=b[['TeamID','strength','seed']].rename(columns={'TeamID':'OpponentID','strength':'opp_strength','seed':'opp_seed'})
    long=long.merge(opp,on='OpponentID',how='left',validate='many_to_one')
    require(long.opp_strength.notna().all(),'Missing opponent strength')
    counts=long.groupby('TeamID').size()
    require(np.array_equal(counts.reindex(b.TeamID).to_numpy(),b.games.to_numpy()),'Cached game counts do not match legal compact data')
    p=PARAMETERS
    q=np.where(long.opp_seed<=p['top_seed_max'],p['top_seed_points'],
               np.where(long.opp_seed.notna(),p['other_seed_points'],p['unseeded_points']))
    reference=float(b.strength.quantile(p['reference_quantile']))
    expectation=expit((reference-long.opp_strength+p['home_points']*long.home)/p['logistic_scale_points'])
    nonhome=(long.home<=0).astype(float)
    long['quality_points']=q
    long['reference_expectation']=expectation
    long['quality_points_won']=long.win*q
    long['quality_points_won_nonhome']=long.win*q*nonhome
    long['quality_bad_losses']=(1-long.win)*long.opp_seed.isna()
    long['reference_surplus']=long.win-expectation
    long['reference_surplus_nonhome']=(long.win-expectation)*nonhome
    long['reference_upset_credit']=long.win*(1-expectation)**2
    long['reference_bad_loss_cost']=(1-long.win)*expectation**2
    long['nonhome_games']=nonhome
    result=long.groupby('TeamID')[QUALITY+RECORD+['nonhome_games']].sum().reset_index()
    result['games']=result.TeamID.map(counts)
    for name in ['quality_bad_losses','reference_upset_credit','reference_bad_loss_cost']:
        result[name]/=result.games+p['support_pseudogames']
    result.reference_surplus_nonhome/=result.nonhome_games+p['support_pseudogames']
    result['reference_strength']=reference
    result['strength']=result.TeamID.map(b.set_index('TeamID').strength)
    result['seed']=result.TeamID.map(b.set_index('TeamID').seed)
    result['Gender'],result['Season'],result['snapshot_day']=gender,season,cutoff
    require(np.isfinite(result[QUALITY+RECORD]).all().all(),'Nonfinite schedule features')
    long['Gender'],long['Season']=gender,season
    return result.sort_values('TeamID').reset_index(drop=True),long


def matchup_features(teams:pd.DataFrame,pairs:pd.DataFrame) -> pd.DataFrame:
    require(not any(c in pairs for c in ['y','WScore','LScore']), 'Tournament labels cannot enter features')
    keys=['Gender','Season','Team1ID','Team2ID']
    require(set(keys)<=set(pairs), 'Missing pair identifiers')
    require(not pairs.duplicated(keys).any() and (pairs.Team1ID!=pairs.Team2ID).all(),'Duplicate or self matchup')
    require(not teams.duplicated(KEYS).any(),'Duplicate team snapshot')
    out=pairs[keys].reset_index(drop=True).copy()
    parts=[]
    for name in ['Team1ID','Team2ID']:
        part=out.merge(teams[KEYS+QUALITY+RECORD].rename(columns={'TeamID':name}),
                       on=['Gender','Season',name],how='left',validate='many_to_one')
        require(np.isfinite(part[QUALITY+RECORD]).all().all(),'Missing/nonfinite matchup profile')
        parts.append(part[QUALITY+RECORD].to_numpy())
    out[NEW_COLS]=parts[0]-parts[1]
    return out


def registry(anchor:list[str]) -> pd.DataFrame:
    meanings={
      'quality_points_won':'Sum 6/4/0.25 opponent-quality points over regular-season wins; no secondary-tournament tier',
      'quality_points_won_nonhome':'Same point sum for away and neutral-site wins',
      'quality_bad_losses':'Losses to non-NCAA-field opponents divided by games+5',
      'reference_surplus':'Actual wins minus expected wins of the season 75th-percentile strength reference',
      'reference_surplus_nonhome':'Nonhome reference surplus divided by nonhome games+5',
      'reference_upset_credit':'Sum win*(1-reference_expectation)^2 divided by games+5',
      'reference_bad_loss_cost':'Sum loss*reference_expectation^2 divided by games+5'}
    rows=[]
    for c in anchor+NEW_COLS:
        family='anchor' if c in anchor else 'quality' if c in QUALITY_COLS else 'record'
        rows.append({'feature':c,'family':family,'new_candidate':family!='anchor','swap_parity':-1,
                     'description':meanings.get(c.removeprefix('diff_'),'Frozen round-02 control'),
                     'availability':'Regular season <=132; bracket seeds after field announcement',
                     'label_policy':'No same-season NCAA outcomes in features; no 2022-2026 training/evaluation',
                     'status':'unproven; fixed-family ablation required','official_NET_or_WAB':False})
    return pd.DataFrame(rows)
