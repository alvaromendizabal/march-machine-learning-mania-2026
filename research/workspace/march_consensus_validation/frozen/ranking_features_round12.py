"""Publication-safe consensus control and two matched-system matchup hypotheses.

No outcome column is read. No system is selected with tournament labels. Numerical
'votes' are features, not independent observations or calibrated probabilities.
"""
from __future__ import annotations
from itertools import combinations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import logit
from research_io import sf, require, event

KEYS = ['Gender', 'Season', 'Team1ID', 'Team2ID']
BASE = ['diff_' + field for field in sf.CONTROL]
CONSENSUS = ['diff_rank_consensus_logit']
MEDIAN = ['pair_rank_median_residual']
VOTES = ['pair_rank_vote_logit']
NEW = MEDIAN + VOTES
ALL = BASE + CONSENSUS + NEW
RECIPES = {
    'anchor': BASE,
    'anchor_consensus': BASE + CONSENSUS,
    'anchor_consensus_median': BASE + CONSENSUS + MEDIAN,
    'anchor_consensus_votes': BASE + CONSENSUS + VOTES,
    'anchor_consensus_both': ALL,
}
PARAMETERS = {'cutoff_day': 132, 'max_edition_age': 14, 'percentile_clip': .01,
              'vote_pseudocount_per_side': 1., 'minimum_common_systems': 3,
              'system_selection': 'every contemporaneous legal system; no outcome-based selection',
              'chunk_rows': 250_000}
RAW_COLUMNS = ['Season', 'RankingDayNum', 'SystemName', 'TeamID', 'OrdinalRank']
YEARS = list(range(2013, 2020))


def read_legal_rankings(path: Path, seasons: list[int], chunksize: int | None = None) -> pd.DataFrame:
    """Stream the large CSV once. Keep only requested seasons and legal day range."""
    require(set(seasons).issubset(YEARS) and len(seasons) == len(set(seasons)) and bool(seasons),
            'Unsupported/duplicate requested seasons')
    chunksize = PARAMETERS['chunk_rows'] if chunksize is None else chunksize
    require(isinstance(chunksize, int) and chunksize > 0, 'Invalid CSV chunk size')
    parts = []; seen = 0
    for i, chunk in enumerate(pd.read_csv(path, usecols=RAW_COLUMNS, chunksize=chunksize,
                                         float_precision='round_trip')):
        seen += len(chunk)
        keep = chunk.Season.isin(seasons) & chunk.RankingDayNum.between(118, 132)
        if keep.any(): parts.append(chunk.loc[keep, RAW_COLUMNS].copy())
        event('ranking_csv_chunk', chunk=i+1, rows_scanned=seen, legal_rows_kept=sum(map(len,parts)))
    require(bool(parts), 'No legal pre-cutoff ranking rows; do not substitute final-season rankings')
    return pd.concat(parts, ignore_index=True)


def publication_panel(raw: pd.DataFrame, season: int) -> tuple[pd.DataFrame, dict]:
    """Match the pinned repository normalization; choose edition before team filtering.

    Missing teams in a latest edition are not backfilled from an earlier edition.
    A system's normalization denominator is its own published maximum ordinal.
    """
    require(season in YEARS, 'Season outside the declared experiment')
    require(set(RAW_COLUMNS).issubset(raw.columns), 'Ranking columns missing')
    legal = raw.loc[raw.Season.eq(season) & raw.RankingDayNum.between(118, 132), RAW_COLUMNS].copy()
    require(not legal.empty and not legal.isna().any().any(), 'Missing legal ranking observations')
    cols = ['Season','RankingDayNum','TeamID','OrdinalRank']
    values = legal[cols].to_numpy(dtype=float)
    require(np.isfinite(values).all() and np.equal(values, np.floor(values)).all(),
            'Ranking fields require finite integer values')
    require((legal.OrdinalRank > 0).all() and (legal.TeamID > 0).all(), 'Nonpositive ranking/team identifier')
    require(legal.SystemName.map(lambda v: isinstance(v,str) and bool(v.strip())).all(), 'Invalid system name')
    require(not legal.duplicated(RAW_COLUMNS[:-1]).any(), 'Duplicate ranking observation')
    legal[cols] = legal[cols].astype('int64')
    last = legal.groupby('SystemName', sort=True).RankingDayNum.transform('max')
    selected = legal.loc[legal.RankingDayNum.eq(last)].sort_values(['SystemName','TeamID']).reset_index(drop=True)
    cohort = selected.groupby('SystemName',sort=True).OrdinalRank.transform('max')
    selected['percentile'] = 1 - (selected.OrdinalRank-1) / (cohort-1).clip(lower=1)
    selected['system_logit'] = logit(selected.percentile.clip(.01,.99))
    selected['age'] = 132-selected.RankingDayNum
    require(np.isfinite(selected[['percentile','system_logit']].to_numpy()).all(), 'Invalid normalized ranking')
    support = {'Season':season, 'systems':int(selected.SystemName.nunique()),
        'teams':int(selected.TeamID.nunique()), 'observations':len(selected),
        'max_publication_day':int(selected.RankingDayNum.max()), 'min_publication_day':int(selected.RankingDayNum.min()),
        'oldest_edition_age':int(selected.age.max()), 'tournament_labels_used':False}
    return selected, support


def pair_ranking_signals(panel: pd.DataFrame, team1: np.ndarray, team2: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Accept either orientation; the three features must negate on team swap."""
    a = np.asarray(team1); b = np.asarray(team2)
    require(a.ndim == b.ndim == 1 and len(a)==len(b) and len(a)>0 and (a!=b).all(), 'Invalid pair arrays')
    require(set(['SystemName','TeamID','OrdinalRank','percentile','system_logit']).issubset(panel), 'Panel schema missing')
    require(not panel.duplicated(['SystemName','TeamID']).any(), 'Duplicate panel entries')
    pivot = panel.pivot(index='TeamID',columns='SystemName',values='system_logit').sort_index().sort_index(axis=1)
    require(set(np.r_[a,b]).issubset(pivot.index), 'A seeded team has no legal ranking coverage')
    x = pivot.loc[a].to_numpy(dtype=float); y = pivot.loc[b].to_numpy(dtype=float)
    common = np.isfinite(x) & np.isfinite(y); count = common.sum(axis=1)
    require((count >= PARAMETERS['minimum_common_systems']).all(),
            'Insufficient shared ranking systems for at least one seeded pair')
    delta = np.where(common,x-y,np.nan)
    # Logit of team median percentile is the pre-existing consensus control definition.
    consensus = panel.groupby('TeamID',sort=True).percentile.median().clip(.01,.99).map(logit)
    control = consensus.loc[a].to_numpy()-consensus.loc[b].to_numpy()
    median = np.nanmedian(delta,axis=1)
    # Compare original ordinal ranks for ties/order: clipping logits must NOT create fake ties.
    ordinal = panel.pivot(index='TeamID',columns='SystemName',values='OrdinalRank').reindex(index=pivot.index,columns=pivot.columns)
    ra = ordinal.loc[a].to_numpy(dtype=float); rb = ordinal.loc[b].to_numpy(dtype=float)
    awins = (common & (ra < rb)).sum(axis=1); bwins = (common & (ra > rb)).sum(axis=1)
    ties = (common & (ra == rb)).sum(axis=1)
    require(np.array_equal(awins+bwins+ties,count), 'Rank direction counts inconsistent')
    alpha = PARAMETERS['vote_pseudocount_per_side']
    vote = np.log((awins+.5*ties+alpha)/(bwins+.5*ties+alpha))
    features = pd.DataFrame({CONSENSUS[0]:control, MEDIAN[0]:median-control, VOTES[0]:vote})
    require(np.isfinite(features.to_numpy()).all(), 'Nonfinite ranking feature')
    detail = pd.DataFrame({'common_systems':count,'fraction_favor_team1':(awins+.5*ties)/count,
        'fraction_ties':ties/count,'common_fraction_of_union':count/(np.isfinite(x)|np.isfinite(y)).sum(axis=1),
        'pair_logit_iqr':np.nanquantile(delta,.75,axis=1)-np.nanquantile(delta,.25,axis=1)})
    return features,detail


def build_matchups(base: pd.DataFrame, panel: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame,dict,pd.DataFrame]:
    require(not base.empty and base.Gender.eq('M').all() and base.Season.nunique()==1, 'Men and one snapshot season required')
    require(not base.duplicated(['Gender','Season','TeamID']).any(), 'Duplicate base snapshot')
    season = int(base.Season.iloc[0]); require(season in YEARS and panel.Season.eq(season).all(), 'Panel/snapshot season mismatch')
    selected = base.loc[base.seed.notna()].sort_values('TeamID').copy()
    require(len(selected)>=2 and np.isfinite(selected[sf.CONTROL].to_numpy(dtype=float)).all(), 'Missing seeded-team controls')
    ids = selected.TeamID.to_numpy(dtype=float)
    require(np.isfinite(ids).all() and np.equal(ids,np.floor(ids)).all(), 'Invalid team identifier')
    ids = ids.astype('int64'); look = selected.set_index('TeamID')
    pairs = pd.DataFrame(combinations(ids,2),columns=['Team1ID','Team2ID'])
    pairs.insert(0,'Season',season); pairs.insert(0,'Gender','M')
    for field in sf.CONTROL:
        pairs['diff_'+field] = look.loc[pairs.Team1ID,field].to_numpy()-look.loc[pairs.Team2ID,field].to_numpy()
    feats,detail = pair_ranking_signals(panel,pairs.Team1ID.to_numpy(),pairs.Team2ID.to_numpy())
    reverse,_ = pair_ranking_signals(panel,pairs.Team2ID.to_numpy(),pairs.Team1ID.to_numpy())
    err = float(np.max(np.abs(feats.to_numpy()+reverse.to_numpy())))
    require(err < 1e-12,'Ranking feature swap failure')
    pairs = pd.concat([pairs,feats],axis=1)
    detail = pd.concat([pairs[KEYS].reset_index(drop=True),detail],axis=1)
    profile = selected[['Gender','Season','TeamID','seed','strength']].copy()
    summary = panel.groupby('TeamID').agg(consensus_percentile=('percentile','median'),system_count=('SystemName','nunique'),rank_iqr=('percentile',lambda s:s.quantile(.75)-s.quantile(.25)))
    profile = profile.merge(summary,left_on='TeamID',right_index=True,how='left',validate='one_to_one')
    require(not profile[['consensus_percentile','system_count','rank_iqr']].isna().any().any(), 'Missing ranking profile')
    support = {'Season':season,'seeded_teams':len(ids),'potential_pairs':len(pairs),
        'minimum_common_systems':int(detail.common_systems.min()),'median_common_systems':float(detail.common_systems.median()),
        'min_common_fraction':float(detail.common_fraction_of_union.min()),'feature_swap_error':err,'tournament_labels_used':False}
    require(np.isfinite(pairs[ALL].to_numpy(dtype=float)).all() and not pairs.duplicated(KEYS).any(), 'Invalid final features')
    return pairs,profile,support,detail


def registry() -> pd.DataFrame:
    rows = [{'feature':n,'family':'reference','new_candidate':False,'description':'Unchanged frozen reference'} for n in BASE]
    rows += [{'feature':CONSENSUS[0],'family':'established_consensus_control','new_candidate':False,
              'description':'Difference in logit of each team median normalized legal rank, clip .01/.99'},
        {'feature':MEDIAN[0],'family':'shared_system_margin','new_candidate':True,
         'description':'Median shared-system logit rank difference minus marginal-consensus difference'},
        {'feature':VOTES[0],'family':'shared_system_agreement','new_candidate':True,
         'description':'Log ratio of shared ordinal preferences; tied ranks half each, one pseudocount each'}]
    result=pd.DataFrame(rows);result['swap_parity']=-1;result['cutoff_day']=132
    result['availability']='Latest edition per system in days 118–132; no backfill of absent teams'
    result['interpretation']='Ordinal-derived feature; not calibrated probability; systems not independent'
    return result
