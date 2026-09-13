"""Two independent, preregistered basketball representation experiments.

Only pre-tournament information enters these functions. Labels never enter them.
Round 14 explores ordinal-tail resolution and cardinal quantile mappings.
Round 15 compares games against identical opponents in identical venue categories.
"""
from __future__ import annotations
from itertools import combinations
import numpy as np
import pandas as pd
from scipy.special import expit, logit, ndtri
from research_io import sf, require
import consensus_reference as cf

KEYS = cf.KEYS
BASE = cf.ALL.copy()  # fixed 17-input reference including established consensus
VALIDATION = cf.VALIDATION.copy()
YEARS = cf.YEARS.copy()
FEATURES = {
 '14': ['rank_midpoint_logit_correction','rank_normal_quantile_correction',
        'rank_mapped_margin_gap','rank_mapped_efficiency_gap'],
 '15': ['common_venue_margin_gap','common_venue_win_gap',
        'common_venue_offense_gap','common_venue_defense_gap']}
FAMILIES = {'14': ('tail_resolution','cardinal_mapping'),
            '15': ('score_and_result','offense_and_defense')}
PARAMETERS = {'14': {'plotting_position':'1-(rank-0.5)/maximum_rank_in_edition',
                      'normal_scale':float(np.pi/np.sqrt(3)),
                      'quantile_method':'linear', 'minimum_mapping_teams':50},
              '15': {'cutoff_day':132,'shrinkage_opponents':4.,
                      'venue_matching':'exact H/A/N category',
                      'aggregation':'equal venue weights within opponent, equal opponent weights',
                      'efficiency_quality_filter':'relative possession-estimate discrepancy <= 0.10'}}
DUPLICATE = [f'diagnostic_duplicate_{i}' for i in range(4)]

def recipes(round_id: str) -> dict[str,list[str]]:
    require(round_id in FEATURES, 'Unsupported round')
    a,b = FAMILIES[round_id]; f=FEATURES[round_id]
    return {'reference':BASE, a:BASE+f[:2], b:BASE+f[2:],
            'both':BASE+f,'duplicate_control':BASE+DUPLICATE}


def validate_pairs(pairs: pd.DataFrame) -> None:
    require(set(KEYS+BASE)<=set(pairs), 'Missing reference/pair columns')
    require(not pairs.empty and pairs.Gender.eq('M').all(), 'Men only')
    require(pairs.Season.nunique()==1 and int(pairs.Season.iloc[0]) in YEARS, 'Wrong snapshot year')
    v=pairs[KEYS[1:]].to_numpy(dtype=float)
    require(np.isfinite(v).all() and np.equal(v,np.floor(v)).all(), 'Nonintegral identities')
    require((pairs.Team1ID != pairs.Team2ID).all() and not pairs.duplicated(KEYS).any(), 'Duplicate or self pairing')
    require(np.isfinite(pairs[BASE].to_numpy(dtype=float)).all(), 'Nonfinite reference')


def paired_values(profile: pd.DataFrame, pairs: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Preserve pair row order. Arbitrary orientation supports explicit swap testing."""
    require(not profile.TeamID.duplicated().any(), 'Duplicate profile team')
    lookup=profile.set_index('TeamID'); ids=set(pairs.Team1ID)|set(pairs.Team2ID)
    require(ids<=set(lookup.index), 'Missing profile for pairing')
    return pd.DataFrame({c:lookup.loc[pairs.Team1ID,c].to_numpy()-lookup.loc[pairs.Team2ID,c].to_numpy()
                         for c in columns},index=pairs.index)


def ranking_features(base: pd.DataFrame, panel: pd.DataFrame, pairs: pd.DataFrame):
    """Four hypotheses, computed from cached legal editions and same-season ratings.

    Logit and normal maps use open-interval plotting positions, not a 1% clip.
    Empirical quantile maps assume rank ordering can share the marginal distribution
    of existing rating estimates; they are not reconstructed vendor ratings.
    """
    validate_pairs(pairs); season=int(pairs.Season.iloc[0])
    require(base.Season.eq(season).all() and base.Gender.eq('M').all(), 'Wrong base year')
    require(not base.TeamID.duplicated().any(), 'Duplicate base teams')
    required=['Season','RankingDayNum','SystemName','TeamID','OrdinalRank']
    require(set(required)<=set(panel) and not panel[required].isna().any().any(), 'Bad publication schema')
    require(panel.Season.eq(season).all() and panel.RankingDayNum.between(118,132).all(), 'Illegal publication date')
    require(panel.groupby('SystemName').RankingDayNum.nunique().eq(1).all(), 'Mixed editions')
    require(not panel.duplicated(['SystemName','TeamID']).any(), 'Duplicate published ranks')
    vals=panel[['TeamID','OrdinalRank']].to_numpy(dtype=float)
    require(np.isfinite(vals).all() and (vals>0).all() and np.equal(vals,np.floor(vals)).all(), 'Invalid ordinal ranks')
    clean=base[['strength','adj_offense','adj_defense']].dropna()
    require(len(clean)>=PARAMETERS['14']['minimum_mapping_teams'], 'Insufficient league-level cardinal mapping support')
    require(np.isfinite(clean.to_numpy()).all(), 'Invalid cardinal ratings')
    panel=panel.sort_values(['SystemName','TeamID']).copy()
    n=panel.groupby('SystemName').OrdinalRank.transform('max').to_numpy(dtype=float)
    rank=panel.OrdinalRank.to_numpy(dtype=float)
    midpoint=1-(rank-.5)/n
    require(((midpoint>0)&(midpoint<1)).all(), 'Plotting positions outside open interval')
    old=1-(rank-1)/np.maximum(n-1,1)
    panel['midpoint_percentile']=midpoint
    panel['old_percentile']=old
    stats=panel.groupby('TeamID',sort=True).agg(midpoint=('midpoint_percentile','median'),
                    old=('old_percentile','median'),systems=('SystemName','nunique'))
    oldlog=logit(stats.old.clip(.01,.99).to_numpy())
    mid=stats.midpoint.to_numpy()
    stats[FEATURES['14'][0]]=logit(mid)-oldlog
    stats[FEATURES['14'][1]]=PARAMETERS['14']['normal_scale']*ndtri(mid)-oldlog
    stats[FEATURES['14'][2]]=np.quantile(clean.strength.to_numpy(),mid,method='linear')
    net=clean.adj_offense.to_numpy()+clean.adj_defense.to_numpy()
    stats[FEATURES['14'][3]]=np.quantile(net,mid,method='linear')
    stats['old_logit']=oldlog;stats['unclipped_logit']=logit(mid)
    stats['at_old_clip']=(stats.old<=.01)|(stats.old>=.99)
    stats=stats.reset_index(); mapped=paired_values(stats,pairs,FEATURES['14'])
    old_gap=paired_values(stats,pairs,['old_logit']).old_logit.to_numpy()
    require(np.max(np.abs(old_gap-pairs[cf.CONSENSUS].to_numpy()))<1e-12, 'Consensus control drift')
    out=pairs[KEYS+BASE].copy()
    for c in FEATURES['14']:out[c]=mapped[c]
    prof=base[['TeamID','seed','strength','adj_offense','adj_defense']].merge(stats,on='TeamID',validate='one_to_one')
    prof.insert(0,'Season',season)
    coverage=pd.DataFrame([{'Season':season,'pairs':len(out),'mapping_teams':len(clean),
        'ranked_teams':len(stats),'seeded_clipped_teams':int(prof.loc[prof.seed.notna(),'at_old_clip'].sum()),
        'minimum_systems':int(stats.systems.min()),'new_feature_definitions':4,'rating_fits':0}])
    support=pairs[KEYS].copy();support['minimum_systems']=np.minimum(
        stats.set_index('TeamID').loc[pairs.Team1ID,'systems'].to_numpy(),
        stats.set_index('TeamID').loc[pairs.Team2ID,'systems'].to_numpy())
    return out,prof,coverage,support


def common_context_table(compact: pd.DataFrame, detailed: pd.DataFrame, season: int) -> pd.DataFrame:
    """Aggregate legal results by team, opponent, and exact venue category.

    Direct A/B games cannot be shared-opponent comparisons: self opponents are
    never present. All meetings with a third team are averaged within venue first.
    """
    require(season in YEARS,'Unsupported season')
    games=sf.legal_games(compact,season,detailed=False).sort_values(['DayNum','WTeamID','LTeamID'])
    detail=sf.legal_games(detailed,season,detailed=True).sort_values(['DayNum','WTeamID','LTeamID'])
    keys=['Season','DayNum','WTeamID','LTeamID','WScore','LScore','WLoc']
    aligned=detail.merge(games[keys],on=keys,how='left',indicator=True,validate='one_to_one')
    require(aligned['_merge'].eq('both').all(),'Compact/detailed disagreement')
    long=sf.long_games(games);long['margin']=long.points-long.allowed
    group=['TeamID','OpponentID','home']
    out=long.groupby(group,sort=True).agg(margin=('margin','mean'),win=('win','mean'),
                                      games=('win','size'),last_day=('DayNum','max')).reset_index()
    dl=sf.long_games(detail,detailed=True);dl=dl.loc[dl.clean].copy()
    require(not dl.empty,'No clean detailed games')
    dl['offense']=100*dl.points/dl.possessions;dl['defense']=-100*dl.allowed/dl.possessions
    eff=dl.groupby(group,sort=True).agg(offense=('offense','mean'),defense=('defense','mean'),
                                       detail_games=('clean','size')).reset_index()
    out=out.merge(eff,on=group,how='left',validate='one_to_one');out.insert(0,'Season',season)
    return out


def context_contrast(a: pd.DataFrame, b: pd.DataFrame, fields: list[str]):
    """No common evidence -> zero *increment*, with support separately reported.

    A location category must match exactly. Average the matched locations within
    each common opponent before pooling opponents, so rematches do not dominate.
    """
    match=a.merge(b,on=['OpponentID','home'],suffixes=('_a','_b'),validate='one_to_one')
    if match.empty:return np.zeros(len(fields)),0
    good=np.isfinite(match[[f'{f}_{s}' for f in fields for s in ['a','b']]].to_numpy()).all(axis=1)
    match=match.loc[good]
    if match.empty:return np.zeros(len(fields)),0
    delta=pd.DataFrame({f:match[f+'_a'].to_numpy()-match[f+'_b'].to_numpy() for f in fields})
    delta['OpponentID']=match.OpponentID.to_numpy()
    byopp=delta.groupby('OpponentID',sort=True)[fields].mean();n=len(byopp)
    return byopp.sum().to_numpy()/(n+PARAMETERS['15']['shrinkage_opponents']),n


def opponent_features(context: pd.DataFrame, pairs: pd.DataFrame):
    validate_pairs(pairs);season=int(pairs.Season.iloc[0])
    required=['Season','TeamID','OpponentID','home','margin','win','offense','defense','games','last_day']
    require(set(required)<=set(context),'Missing context fields')
    require(context.Season.eq(season).all() and context.last_day.le(132).all(),'Context year/date mismatch')
    require(context.home.isin([-1,0,1]).all(),'Bad venue code')
    require((context.TeamID!=context.OpponentID).all(),'Self opponent')
    require(not context.duplicated(['TeamID','OpponentID','home']).any(),'Duplicate context')
    require(np.isfinite(context[['margin','win']].to_numpy()).all(),'Nonfinite compact context')
    require(context.win.between(0,1).all(),'Invalid win fraction')
    ids=set(pairs.Team1ID)|set(pairs.Team2ID)
    require(ids<=set(context.TeamID),'Missing context team')
    selected=context.loc[context.TeamID.isin(ids)].drop(columns='Season')
    # One matched-context join per season, not thousands of Python pairwise joins.
    shared=selected.merge(selected,on=['OpponentID','home'],suffixes=('_a','_b'))
    shared=shared.loc[shared.TeamID_a<shared.TeamID_b].copy()
    keys=['TeamID_a','TeamID_b']
    low=np.minimum(pairs.Team1ID,pairs.Team2ID);high=np.maximum(pairs.Team1ID,pairs.Team2ID)
    index=pd.MultiIndex.from_arrays([low,high],names=keys)
    sign=np.where(pairs.Team1ID<pairs.Team2ID,1.,-1.)
    out=pairs[KEYS+BASE].copy();support=pairs[KEYS].copy()
    for fields,names,support_name in [(['margin','win'],FEATURES['15'][:2],'matched_compact_opponents'),
                                     (['offense','defense'],FEATURES['15'][2:],'matched_detailed_opponents')]:
        valid=np.isfinite(shared[[f+'_'+side for f in fields for side in ['a','b']]].to_numpy()).all(axis=1)
        t=shared.loc[valid,keys+['OpponentID']].copy()
        for f in fields:t[f]=shared.loc[valid,f+'_a'].to_numpy()-shared.loc[valid,f+'_b'].to_numpy()
        byopp=t.groupby(keys+['OpponentID'],sort=True)[fields].mean()
        sums=byopp.groupby(level=keys).sum();counts=byopp.groupby(level=keys).size()
        counts=counts.reindex(index,fill_value=0).to_numpy()
        value=sums.reindex(index,fill_value=0).to_numpy()/(counts[:,None]+PARAMETERS['15']['shrinkage_opponents'])
        for j,n in enumerate(names):out[n]=sign*value[:,j]
        support[support_name]=counts
    detail=support[['matched_compact_opponents','matched_detailed_opponents']]
    info=pd.DataFrame([{'Season':season,'pairs':len(out),'pairs_with_compact_evidence':int((detail.iloc[:,0]>0).sum()),
        'pairs_with_detail_evidence':int((detail.iloc[:,1]>0).sum()),'median_compact_opponents':float(detail.iloc[:,0].median()),
        'median_detailed_opponents':float(detail.iloc[:,1].median()),'new_feature_definitions':4,'rating_fits':0}])
    profile=context.groupby('TeamID').agg(contexts=('OpponentID','size'),opponents=('OpponentID','nunique'),
                regular_games=('games','sum'),last_day=('last_day','max')).reset_index();profile.insert(0,'Season',season)
    return out,profile,info,support


def finish_features(frame: pd.DataFrame, round_id: str) -> pd.DataFrame:
    out=frame.copy();source=cf.CONSENSUS if round_id=='14' else 'diff_strength'
    for c in DUPLICATE:out[c]=out[source]
    columns=BASE+FEATURES[round_id]+DUPLICATE
    require(np.isfinite(out[columns].to_numpy(dtype=float)).all(), 'Nonfinite candidate feature')
    return out


def registry(round_id: str):
    names=FEATURES[round_id];a,b=FAMILIES[round_id]
    descriptions={
      '14':['Midpoint-logit team gap minus the clipped-consensus gap',
            'Logistic-variance-scaled normal-quantile gap minus clipped-consensus gap',
            'Consensus plotting-position mapped to contemporaneous league margin-strength quantiles',
            'Consensus plotting-position mapped to contemporaneous league adjusted-net-efficiency quantiles'],
      '15':['Shrunk margin gap against common opponents at matching venue categories',
            'Shrunk win-fraction gap against common opponents at matching venue categories',
            'Shrunk points-per-100-possession gap against common opponents at matching venues',
            'Shrunk negative-allowed-efficiency gap against common opponents at matching venues']}
    rows=[{'feature':n,'family':a if i<2 else b,'description':descriptions[round_id][i],
           'new_candidate':True,'cutoff_day':132,'swap_parity':-1,'uses_tournament_labels':False}
          for i,n in enumerate(names)]
    rows += [{'feature':c,'family':'reference','description':'Unchanged round-13 consensus reference','new_candidate':False,
        'cutoff_day':132,'swap_parity':-1,'uses_tournament_labels':False} for c in BASE]
    rows += [{'feature':c,'family':'diagnostic_duplicate','description':'Exact copied input; tests representation/regularization sensitivity, not new information',
        'new_candidate':False,'cutoff_day':132,'swap_parity':-1,'uses_tournament_labels':False} for c in DUPLICATE]
    return pd.DataFrame(rows)
