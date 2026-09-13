"""Unchanged ranking consensus; explicit later-era calendar and label boundaries.

The two failed round-12 pairwise features are NOT computed or fitted here.
All statistical components of the compact reference call the pinned round-02
functions. Tournament results are accepted only by the separate label loader.
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import logit
from research_io import sf, require, event

OLD_YEARS = list(range(2013, 2020))
NEW_YEARS = list(range(2021, 2026))
YEARS = OLD_YEARS + NEW_YEARS
VALIDATION = [2022, 2023, 2024, 2025]
KEYS = ['Gender', 'Season', 'Team1ID', 'Team2ID']
BASE = list(sf.ANCHOR_COLS)
CONSENSUS = 'diff_rank_consensus_logit'
ALL = BASE + [CONSENSUS]
RECIPES = {'anchor': BASE, 'anchor_consensus': ALL}
RANK_COLS = ['Season', 'RankingDayNum', 'SystemName', 'TeamID', 'OrdinalRank']
EXPECTED_SEEDED = 68
EXPECTED_MAIN_DRAW = {s: 62 if s == 2021 else 63 for s in YEARS}
EXPECTED_FIRST_FOUR = 4
SUPPORT = {'minimum_detailed_games': 10, 'minimum_clean_games': 5,
           'minimum_detailed_fraction': .8, 'minimum_common_systems': 3}
PARAMETERS = {'cutoff_day':132, 'max_edition_age':14, 'percentile_clip':.01,
              'selection':'all contemporaneous legal systems; no outcome selection',
              'new_feature_definitions':0, 'build_reference_only':True}


def seed_table(seeds: pd.DataFrame, season: int) -> pd.DataFrame:
    require(season in YEARS, 'Season outside declared range; 2020/2026 are excluded')
    require({'Season','TeamID','Seed'}.issubset(seeds), 'Seed columns missing')
    cur = seeds.loc[seeds.Season.eq(season), ['TeamID','Seed']].copy()
    require(not cur.empty and not cur.isna().any().any() and not cur.TeamID.duplicated().any(), 'Missing/duplicate seeds')
    require(cur.Seed.astype(str).str.fullmatch(r'[WXYZ](0[1-9]|1[0-6])[ab]?').all(), 'Malformed seed codes')
    require(not cur.Seed.duplicated().any(), 'Duplicate seed code')
    ids = cur.TeamID.to_numpy(dtype=float)
    require(np.isfinite(ids).all() and (ids > 0).all() and np.equal(ids,np.floor(ids)).all(), 'Invalid seed team identifiers')
    require(len(cur) == EXPECTED_SEEDED, f'Expected {EXPECTED_SEEDED} seeded teams in {season}; got {len(cur)}')
    cur['TeamID'] = cur.TeamID.astype('int64')
    cur['seed'] = cur.Seed.str[1:3].astype(float)
    cur['seed_stem'] = cur.Seed.str[:3]
    return cur.sort_values('TeamID').reset_index(drop=True)


def reference_inputs(compact: pd.DataFrame, detailed: pd.DataFrame, season: int):
    require(season in YEARS, 'Unsupported season')
    games=sf.legal_games(compact,season,detailed=False)
    detail=sf.legal_games(detailed,season,detailed=True)
    keys=['Season','DayNum','WTeamID','LTeamID','WScore','LScore','WLoc']
    aligned=detail.merge(games[keys],on=keys,how='left',indicator=True,validate='one_to_one')
    require(aligned['_merge'].eq('both').all(),'Detailed/compact games disagree')
    return games, sf.long_games(detail,detailed=True)


def finish_reference(strength: pd.DataFrame, shooting: pd.DataFrame, long: pd.DataFrame,
                     seeds: pd.DataFrame, season: int) -> pd.DataFrame:
    cur=seed_table(seeds,season)
    base=strength.merge(shooting,on='TeamID',how='left',validate='one_to_one')
    base=base.merge(cur[['TeamID','seed']],on='TeamID',how='left',validate='one_to_one')
    base['detailed_games']=base.TeamID.map(long.groupby('TeamID').size()).fillna(0)
    base['detailed_coverage']=base.detailed_games/base.games
    base['clean_games']=base.TeamID.map(long.loc[long.clean].groupby('TeamID').size()).fillna(0)
    base['snapshot_day']=132; base['Gender']='M'; base['Season']=int(season)
    validate_reference(base,cur)
    return base.sort_values('TeamID').reset_index(drop=True)


def validate_reference(base: pd.DataFrame, seeds: pd.DataFrame | None = None):
    require(not base.empty and base.Gender.eq('M').all() and base.Season.nunique()==1, 'Expected one men\'s snapshot')
    require(not base.TeamID.duplicated().any(), 'Duplicate snapshot TeamID')
    selected=base.loc[base.seed.notna()].sort_values('TeamID')
    require(len(selected)==EXPECTED_SEEDED,'Incomplete seeded-team snapshot')
    require(np.isfinite(selected[sf.CONTROL].to_numpy(dtype=float)).all(),'Nonfinite seeded reference inputs')
    if seeds is not None:
        require(np.array_equal(selected.TeamID.to_numpy(),seeds.sort_values('TeamID').TeamID.to_numpy()),'Missing seeded team')
    for col,limit in [('detailed_games',SUPPORT['minimum_detailed_games']),('clean_games',SUPPORT['minimum_clean_games']),
                      ('detailed_coverage',SUPPORT['minimum_detailed_fraction'])]:
        require((selected[col]>=limit).all(),f'Seeded team {col} below declared support')
    return selected


def read_rankings(path: Path, seasons: list[int], chunksize: int = 250_000):
    require(seasons and len(set(seasons))==len(seasons) and set(seasons)<=set(YEARS),'Invalid requested ranking seasons')
    require(isinstance(chunksize,int) and chunksize>0,'Invalid chunksize')
    parts=[];rows=0
    for i,c in enumerate(pd.read_csv(path,usecols=RANK_COLS,chunksize=chunksize,float_precision='round_trip')):
        rows+=len(c);mask=c.Season.isin(seasons)&c.RankingDayNum.between(118,132)
        if mask.any():parts.append(c.loc[mask,RANK_COLS].copy())
        event('ranking_chunk',chunk=i+1,rows_scanned=rows,legal_rows_retained=sum(map(len,parts)))
    require(parts,'No legal ranking observations')
    return pd.concat(parts,ignore_index=True)


def publication_panel(raw: pd.DataFrame, season: int):
    """Round-12 normalization unchanged; only the explicit allowed years expand."""
    require(season in YEARS and set(RANK_COLS)<=set(raw),'Unsupported year or missing ranking schema')
    legal=raw.loc[raw.Season.eq(season)&raw.RankingDayNum.between(118,132),RANK_COLS].copy()
    require(not legal.empty and not legal.isna().any().any(),'Missing legal rankings')
    cols=['Season','RankingDayNum','TeamID','OrdinalRank'];v=legal[cols].to_numpy(dtype=float)
    require(np.isfinite(v).all() and np.equal(v,np.floor(v)).all(),'Ranks and identities must be finite integral values')
    require((legal.OrdinalRank>0).all() and (legal.TeamID>0).all(),'Nonpositive rank or team identifier')
    require(legal.SystemName.map(lambda x:isinstance(x,str) and bool(x.strip())).all(),'Invalid system name')
    require(not legal.duplicated(RANK_COLS[:-1]).any(),'Duplicate ranking observation')
    legal[cols]=legal[cols].astype('int64')
    last=legal.groupby('SystemName',sort=True).RankingDayNum.transform('max')
    panel=legal.loc[legal.RankingDayNum.eq(last)].sort_values(['SystemName','TeamID']).reset_index(drop=True)
    cohort=panel.groupby('SystemName',sort=True).OrdinalRank.transform('max')
    panel['percentile']=1-(panel.OrdinalRank-1)/(cohort-1).clip(lower=1)
    panel['system_logit']=logit(panel.percentile.clip(.01,.99));panel['age']=132-panel.RankingDayNum
    info={'Season':season,'systems':int(panel.SystemName.nunique()),'teams':int(panel.TeamID.nunique()),
          'observations':len(panel),'min_publication_day':int(panel.RankingDayNum.min()),
          'max_publication_day':int(panel.RankingDayNum.max()),'oldest_edition_age':int(panel.age.max()),'tournament_labels_used':False}
    return panel,info


def build_matchups(base: pd.DataFrame, panel: pd.DataFrame):
    selected=validate_reference(base);season=int(base.Season.iloc[0]);require(season in YEARS and panel.Season.eq(season).all(),'Wrong panel season')
    require(not panel.duplicated(['SystemName','TeamID']).any(),'Duplicate panel entries')
    lookup=selected.set_index('TeamID');ids=selected.TeamID.to_numpy(dtype='int64')
    stats=panel.groupby('TeamID',sort=True).agg(consensus_percentile=('percentile','median'),
        system_count=('SystemName','nunique'),mean_age=('age','mean'))
    require(set(ids)<=set(stats.index),'Seeded team missing from latest ranking editions; no backfill')
    stats['consensus_logit']=logit(stats.consensus_percentile.clip(.01,.99))
    pairs=pd.DataFrame(combinations(ids,2),columns=['Team1ID','Team2ID']);pairs.insert(0,'Season',season);pairs.insert(0,'Gender','M')
    for c in sf.CONTROL:pairs['diff_'+c]=lookup.loc[pairs.Team1ID,c].to_numpy()-lookup.loc[pairs.Team2ID,c].to_numpy()
    pairs[CONSENSUS]=stats.loc[pairs.Team1ID,'consensus_logit'].to_numpy()-stats.loc[pairs.Team2ID,'consensus_logit'].to_numpy()
    # Retain the earlier coverage requirement, without computing the rejected candidates.
    available=panel.assign(present=1).pivot(index='TeamID',columns='SystemName',values='present').reindex(ids).fillna(0).to_numpy(dtype=np.int64)
    common=available@available.T;upper=common[np.triu_indices(len(ids),1)]
    require((upper>=SUPPORT['minimum_common_systems']).all(),'Insufficient shared ranking coverage')
    require(np.isfinite(pairs[ALL].to_numpy(dtype=float)).all() and not pairs.duplicated(KEYS).any(),'Invalid matchup matrix')
    profile=selected[['Gender','Season','TeamID','seed','strength','detailed_games','clean_games','detailed_coverage']].merge(stats,on='TeamID',validate='one_to_one')
    info={'Season':season,'seeded_teams':len(ids),'potential_pairs':len(pairs),'minimum_common_systems':int(upper.min()),
          'minimum_systems':int(profile.system_count.min()),'minimum_detailed_games':int(profile.detailed_games.min()),
          'minimum_clean_games':int(profile.clean_games.min()),'minimum_detailed_coverage':float(profile.detailed_coverage.min()),
          'tournament_labels_used':False,'new_feature_definitions':0}
    return pairs,profile,info


def tournament_labels(results: pd.DataFrame, seeds: pd.DataFrame, team_names: pd.DataFrame,
                      years: list[int] | None = None):
    """Main draw via seed stems; 2021 non-game excluded, never fabricated as a win.

    Seed suffix matching is label selection only. No realized opponent/round/location
    is given to a feature constructor. All potential seeded pairs already exist.
    """
    years=YEARS if years is None else years
    require(years and len(set(years))==len(years) and set(years)<=set(YEARS),'Only declared years, never 2020 or 2026')
    required=['Season','DayNum','WTeamID','LTeamID','WScore','LScore']
    require(set(required)<=set(results),'Missing target schema')
    pieces=[];audit=[]
    for year in years:
        cur=seed_table(seeds,year).set_index('TeamID')
        g=results.loc[results.Season.eq(year),required].copy()
        require(not g.empty and not g.isna().any().any(),'Missing tournament rows')
        v=g[required].to_numpy(dtype=float)
        require(np.isfinite(v).all() and np.equal(v,np.floor(v)).all(),'Invalid tournament count/identifier')
        require((g.WTeamID!=g.LTeamID).all(),'Tournament self-matchup')
        lo=np.minimum(g.WTeamID,g.LTeamID);hi=np.maximum(g.WTeamID,g.LTeamID)
        require(not pd.DataFrame({'low':lo,'high':hi}).duplicated().any(),'Duplicate tournament matchup')
        require(set(g.WTeamID)|set(g.LTeamID)<=set(cur.index),'Unseeded target team')
        wa=g.WTeamID.map(cur.Seed);la=g.LTeamID.map(cur.Seed)
        playin=wa.str[:3].eq(la.str[:3])
        require((~playin | (wa.str.len().eq(4)&la.str.len().eq(4)&wa.str[-1].ne(la.str[-1]))).all(),'Ambiguous First Four identity')
        require(int(playin.sum())==EXPECTED_FIRST_FOUR,f'Expected four First Four games in {year}')
        excluded_non_game=np.zeros(len(g),dtype=bool)
        if year==2021:
            require({'TeamID','TeamName'}<=set(team_names),'Team names required for documented 2021 no-contest')
            o=team_names.loc[team_names.TeamName.eq('Oregon'),'TeamID'];vcu=team_names.loc[team_names.TeamName.eq('VCU'),'TeamID']
            require(len(o)==len(vcu)==1,'Cannot resolve documented Oregon/VCU no-contest identity')
            a,b=int(o.iloc[0]),int(vcu.iloc[0])
            excluded_non_game=((g.WTeamID.eq(a)&g.LTeamID.eq(b))|(g.WTeamID.eq(b)&g.LTeamID.eq(a))).to_numpy()
        main=g.loc[~playin.to_numpy() & ~excluded_non_game].copy()
        require(len(main)==EXPECTED_MAIN_DRAW[year],f'Unexpected played main-draw count in {year}: {len(main)}')
        require((main.WScore>main.LScore).all() and (main.LScore>0).all(),'Invalid played-game score; inspect rather than invent targets')
        if year in OLD_YEARS:require(main.DayNum.ge(136).all(),'Old reference/main-draw definition differs')
        p=pd.DataFrame({'Gender':'M','Season':year,'Team1ID':np.minimum(main.WTeamID,main.LTeamID).astype('int64'),
            'Team2ID':np.maximum(main.WTeamID,main.LTeamID).astype('int64'),'y':main.WTeamID.lt(main.LTeamID).astype(int)})
        pieces.append(p)
        audit.append({'Season':year,'raw_tournament_rows':len(g),'first_four_excluded':int(playin.sum()),
            'no_contest_rows_excluded':int(excluded_non_game.sum()),'played_main_draw_games':len(main),
            'first_four_max_day':int(g.loc[playin,'DayNum'].max()),'main_draw_min_day':int(main.DayNum.min()),
            'scope':'played main draw only; administrative advancement is not a played result'})
    out=pd.concat(pieces,ignore_index=True).sort_values(['Season','Team1ID','Team2ID']).reset_index(drop=True)
    return out.drop(columns='y'),out.y.to_numpy(dtype=int),pd.DataFrame(audit)


def registry():
    r=[{'feature':c,'role':'unchanged reference','new_candidate':False} for c in BASE]
    r.append({'feature':CONSENSUS,'role':'established consensus, unchanged later-era replication','new_candidate':False})
    out=pd.DataFrame(r);out['cutoff_day']=132;out['swap_parity']=-1
    return out
