"""Round 02: pre-tournament shooting representations, independent of tournament labels.

This is an isolated research module, NOT a replacement for the production package.
The compact strength and standard shooting controls follow the published project's
formulas. New signals are leave-opponent-out residuals and weighted additive shot
profiles. All fits here use regular-season observations, not tournament labels.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.linear_model import Ridge

CUTOFF = 132
BOX = ('FGM', 'FGA', 'FGM3', 'FGA3', 'FTM', 'FTA', 'OR', 'DR', 'TO')
STRENGTH = ['seed', 'strength', 'schedule_strength', 'win_rate', 'margin', 'margin_sd']
CONTROL = STRENGTH + ['adj_offense', 'adj_defense'] + [
    side + shot + '_posterior' for side in ('', 'opp_') for shot in ('two', 'three', 'free')
] + ['three_share', 'opp_three_share']
RESIDUAL = ['resid_three_pp100', 'resid_free_pp100',
            'resid_three_recent_pp100', 'resid_free_recent_pp100',
            'schedule_three_accuracy', 'schedule_free_accuracy']
PROFILE = [f'profile_{rate}_{side}' for rate in ('two', 'three', 'share')
           for side in ('offense', 'allowance')]
INTERACTIONS = ['profile_matchup_efg', 'profile_variance_scaled_strength']
ANCHOR_COLS = ['diff_' + c for c in CONTROL]
RESIDUAL_COLS = ['diff_' + c for c in RESIDUAL]
PROFILE_COLS = ['diff_' + c for c in PROFILE] + INTERACTIONS
RECIPES = {'anchor': ANCHOR_COLS,
           'anchor_residual': ANCHOR_COLS + RESIDUAL_COLS,
           'anchor_profile': ANCHOR_COLS + PROFILE_COLS,
           'anchor_both': ANCHOR_COLS + RESIDUAL_COLS + PROFILE_COLS}
ALL_FEATURES = RECIPES['anchor_both']


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def legal_games(frame: pd.DataFrame, season: int, *, detailed: bool, cutoff: int = CUTOFF) -> pd.DataFrame:
    """Filter BEFORE validation: later seasons and post-cutoff rows are not inputs."""
    required = ['Season', 'DayNum', 'WTeamID', 'LTeamID', 'WScore', 'LScore', 'WLoc']
    if detailed:
        required += [s + k for s in ('W', 'L') for k in BOX]
    require(set(required).issubset(frame.columns), 'Missing required regular-season columns')
    out = frame.loc[(frame.Season == season) & (frame.DayNum <= cutoff)].copy()
    require(not out.empty, f'No legal regular-season games in {season}')
    require(not out[required].isna().any().any(), 'Missing required game values')
    numeric = [k for k in required if k != 'WLoc']
    vals = out[numeric].to_numpy(dtype=float)
    require(np.isfinite(vals).all() and (vals >= 0).all(), 'Invalid numeric game values')
    require(np.equal(vals, np.floor(vals)).all(), 'Game identifiers/counts must be integral')
    require(out.WLoc.isin(['H', 'A', 'N']).all(), 'Invalid WLoc')
    require((out.WTeamID != out.LTeamID).all() and (out.WScore > out.LScore).all(), 'Invalid winner or score')
    key = pd.DataFrame({'day': out.DayNum,
                        'low': np.minimum(out.WTeamID, out.LTeamID),
                        'high': np.maximum(out.WTeamID, out.LTeamID)})
    require(not key.duplicated().any(), 'Duplicate physical game')
    if detailed:
        for s in ('W', 'L'):
            for made, att in [('FGM', 'FGA'), ('FGM3', 'FGA3'), ('FTM', 'FTA')]:
                require((out[s + made] <= out[s + att]).all(), 'Makes exceed attempts')
            two_m = out[s + 'FGM'] - out[s + 'FGM3']
            two_a = out[s + 'FGA'] - out[s + 'FGA3']
            require(((two_m >= 0) & (two_a >= 0) & (two_m <= two_a)).all(), 'Invalid two-point counts')
    return out.sort_values(['DayNum', 'WTeamID', 'LTeamID']).reset_index(drop=True)


def long_games(frame: pd.DataFrame, *, detailed: bool = False) -> pd.DataFrame:
    chunks = []
    for s, o, sign in [('W', 'L', 1), ('L', 'W', -1)]:
        d = pd.DataFrame({'TeamID': frame[s+'TeamID'], 'OpponentID': frame[o+'TeamID'],
                          'DayNum': frame.DayNum, 'points': frame[s+'Score'],
                          'allowed': frame[o+'Score'], 'home': sign*frame.WLoc.map({'H':1,'A':-1,'N':0}),
                          'win': int(s == 'W')})
        if detailed:
            for k in BOX:
                d[k], d['opp_'+k] = frame[s+k], frame[o+k]
        chunks.append(d)
    out = pd.concat(chunks, ignore_index=True)
    if detailed:
        p1 = out.FGA-out.OR+out.TO+0.475*out.FTA
        p2 = out.opp_FGA-out.opp_OR+out.opp_TO+0.475*out.opp_FTA
        require(((p1 > 0) & (p2 > 0)).all(), 'Nonpositive possessions')
        out['possessions'] = (p1+p2)/2
        out['clean'] = np.abs(p1-p2)/out.possessions <= 0.10
    return out


def compact_strength(compact: pd.DataFrame) -> pd.DataFrame:
    """Same six compact-control concepts as features.py; no temporal history."""
    teams = np.sort(pd.unique(compact[['WTeamID', 'LTeamID']].to_numpy().ravel()))
    look = {t:i for i,t in enumerate(teams)}
    n, k = len(compact), len(teams)
    x = sparse.csr_matrix((np.r_[np.ones(n),-np.ones(n),compact.WLoc.map({'H':1,'A':-1,'N':0})],
                          (np.tile(np.arange(n),3),np.r_[compact.WTeamID.map(look),compact.LTeamID.map(look),np.full(n,k)])),
                         shape=(n,k+1))
    model = Ridge(alpha=20., fit_intercept=False, solver='lsqr', tol=1e-8)
    model.fit(x,compact.WScore-compact.LScore)
    ratings = pd.DataFrame({'TeamID':teams,'strength':model.coef_[:k]})
    long = long_games(compact)
    long['margin'] = long.points-long.allowed
    out = long.groupby('TeamID').agg(games=('win','size'),win_rate=('win','mean'),
                                       margin=('margin','mean'),margin_sd=('margin','std')).reset_index()
    out = out.merge(ratings,on='TeamID',validate='one_to_one')
    opp = long.merge(ratings.rename(columns={'TeamID':'OpponentID','strength':'opp_strength'}),
                     on='OpponentID',validate='many_to_one')
    out = out.merge(opp.groupby('TeamID').opp_strength.mean().rename('schedule_strength'),on='TeamID',validate='one_to_one')
    return out


def additive_fit(long: pd.DataFrame, target: np.ndarray, weights: np.ndarray,
                 *, alpha: float = 20.) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Weighted additive rate model; off/allowance coefficients have the target's units."""
    keep = np.isfinite(target) & np.isfinite(weights) & (weights > 0)
    g = long.loc[keep].reset_index(drop=True)
    require(len(g) > 0, 'No positive-opportunity rate observations')
    y, w = np.asarray(target)[keep], np.asarray(weights)[keep]
    teams = np.sort(pd.unique(g[['TeamID','OpponentID']].to_numpy().ravel()))
    look = {t:i for i,t in enumerate(teams)}
    n,k = len(g),len(teams)
    x = sparse.csr_matrix((np.r_[np.ones(2*n),g.home],
                          (np.tile(np.arange(n),3),np.r_[g.TeamID.map(look),g.OpponentID.map(look)+k,np.full(n,2*k)])),
                         shape=(n,2*k+1))
    model = Ridge(alpha=alpha,fit_intercept=True,solver='lsqr',tol=1e-8)
    # Average opportunity weight is 1: penalty has comparable scale across rate fits.
    model.fit(x,y,sample_weight=w/w.mean())
    return teams,model.coef_[:k],model.coef_[k:2*k],float(model.intercept_)


def standard_control(long: pd.DataFrame) -> pd.DataFrame:
    totals = long.groupby('TeamID').sum(numeric_only=True)
    out = pd.DataFrame(index=totals.index)
    for side in ('','opp_'):
        for shot,m,a in [('two',totals[side+'FGM']-totals[side+'FGM3'],totals[side+'FGA']-totals[side+'FGA3']),
                         ('three',totals[side+'FGM3'],totals[side+'FGA3']),
                         ('free',totals[side+'FTM'],totals[side+'FTA'])]:
            league = (m.sum()+0.5)/(a.sum()+1.)
            out[side+shot+'_posterior'] = (m+100.*league)/(a+100.)
        out[side+'three_share'] = totals[side+'FGA3']/totals[side+'FGA'].replace(0,np.nan)
    clean = long.loc[long.clean]
    teams,off,allowed,_ = additive_fit(clean,(100.*clean.points/clean.possessions).to_numpy(),np.ones(len(clean)))
    eff = pd.DataFrame({'TeamID':teams,'adj_offense':off,'adj_defense':-allowed})
    out = out.reset_index().merge(eff,on='TeamID',how='left',validate='one_to_one')
    return out


def opponent_residuals(long: pd.DataFrame, cutoff: int = CUTOFF) -> tuple[pd.DataFrame,pd.DataFrame]:
    """Expected opponent shooting excludes ALL meetings with the evaluated defense.

    The league prior also excludes those meetings on both orientations. Other games
    through the snapshot cutoff may be used: this is a PRE-TOURNAMENT descriptor,
    not a claimed pre-game forecast for the regular-season games themselves.
    Residuals are not identified causal luck; missing player/shot-location context remains.
    """
    totals = long.groupby('TeamID')[['FGM3','FGA3','FTM','FTA']].sum()
    meetings = long.groupby(['TeamID','OpponentID'])[['FGM3','FGA3','FTM','FTA']].sum()
    g = long.reset_index(drop=True).copy()
    keys = pd.MultiIndex.from_frame(g[['TeamID','OpponentID']])
    reverse = pd.MultiIndex.from_frame(g[['OpponentID','TeamID']])
    mt = meetings.reindex(keys).reset_index(drop=True)
    mo = meetings.reindex(reverse).reset_index(drop=True)
    ot = totals.reindex(g.OpponentID).reset_index(drop=True)
    exposure = g.possessions + 0.0
    prior_pos = 5.*float(g.possessions.mean())
    rows = pd.DataFrame({'TeamID':g.TeamID,'OpponentID':g.OpponentID,'DayNum':g.DayNum,'possessions':g.possessions})
    output = pd.DataFrame(index=np.sort(g.TeamID.unique()))
    output.index.name = 'TeamID'
    recency = 0.5**((cutoff-g.DayNum.to_numpy(dtype=float))/30.)
    for shot,m,a,value in [('three','FGM3','FGA3',3.),('free','FTM','FTA',1.)]:
        # Excluding both orientations removes the physical meetings from the league prior.
        lm = totals[m].sum()-mt[m]-mo[m]
        la = totals[a].sum()-mt[a]-mo[a]
        om,oa = ot[m]-mo[m],ot[a]-mo[a]
        require(((om>=0)&(oa>=om)&(la>=lm)&(lm>=0)).all(), 'Invalid leave-opponent-out counts')
        league = (lm+0.5)/(la+1.)
        probability = (om+100.*league)/(oa+100.)
        residual = g['opp_'+m]-g['opp_'+a]*probability
        rows[shot+'_expected_pct'] = probability
        rows[shot+'_outside_attempts'] = oa
        rows[shot+'_residual_makes'] = residual
        base = pd.DataFrame({'TeamID':g.TeamID,'r':residual,'p':exposure,
                             'rr':residual*recency,'rp':exposure*recency,
                             'ea':g['opp_'+a]*probability,'a':g['opp_'+a]})
        sums = base.groupby('TeamID').sum()
        output['resid_'+shot+'_pp100'] = 100.*value*sums.r/(sums.p+prior_pos)
        output['resid_'+shot+'_recent_pp100'] = 100.*value*sums.rr/(sums.rp+prior_pos)
        fallback = (totals[m].sum()+0.5)/(totals[a].sum()+1.)
        output['schedule_'+shot+'_accuracy'] = sums.ea.div(sums.a.replace(0,np.nan)).fillna(fallback)
    return output.reset_index(),rows


def adjusted_profiles(long: pd.DataFrame) -> pd.DataFrame:
    """Separate 2P accuracy, 3P accuracy and 3PA share, adjusted jointly for opponent and venue.

    Rate regressions are linear approximations, not KenPom ratings or shot-location models.
    Feature effects remain unclipped; only composed matchup rate hypotheses are bounded.
    """
    out = pd.DataFrame({'TeamID':np.sort(long.TeamID.unique())})
    for name,m,a in [('two',long.FGM-long.FGM3,long.FGA-long.FGA3),
                     ('three',long.FGM3,long.FGA3),('share',long.FGA3,long.FGA)]:
        target = m.div(a.replace(0,np.nan)).to_numpy()
        teams,off,allow,intercept = additive_fit(long,target,a.to_numpy(dtype=float))
        block = pd.DataFrame({'TeamID':teams,'profile_'+name+'_offense':off,
                              'profile_'+name+'_allowance':allow})
        out=out.merge(block,on='TeamID',how='left',validate='one_to_one')
        # An unseen/zero-opportunity team's rating is prior/zero, with diagnostics retained.
        out['profile_'+name+'_offense']=out['profile_'+name+'_offense'].fillna(0.)
        out['profile_'+name+'_allowance']=out['profile_'+name+'_allowance'].fillna(0.)
        out['profile_'+name+'_league']=intercept
    return out


def build_snapshot(compact: pd.DataFrame, detailed: pd.DataFrame, seeds: pd.DataFrame,
                   gender: str, season: int, cutoff: int = CUTOFF) -> tuple[pd.DataFrame,pd.DataFrame]:
    require(gender in ('M','W'), 'Invalid gender')
    games=legal_games(compact,season,detailed=False,cutoff=cutoff)
    detail=legal_games(detailed,season,detailed=True,cutoff=cutoff)
    key=['Season','DayNum','WTeamID','LTeamID','WScore','LScore','WLoc']
    aligned=detail.merge(games[key],on=key,how='left',indicator=True,validate='one_to_one')
    require(aligned['_merge'].eq('both').all(), 'Detailed and compact games disagree')
    long=long_games(detail,detailed=True)
    base=compact_strength(games)
    for extra in (standard_control(long),adjusted_profiles(long)):
        base=base.merge(extra,on='TeamID',how='left',validate='one_to_one')
    resid,audit=opponent_residuals(long,cutoff)
    base=base.merge(resid,on='TeamID',how='left',validate='one_to_one')
    require({'Season','TeamID','Seed'}.issubset(seeds), 'Missing seed columns')
    current=seeds.loc[seeds.Season==season,['TeamID','Seed']].copy()
    require(not current.duplicated('TeamID').any(), 'Duplicate seed')
    parsed=current.Seed.astype(str).str.extract(r'^[WXYZ](0[1-9]|1[0-6])[ab]?$')[0]
    require(parsed.notna().all(), 'Invalid seed code')
    current['seed']=parsed.astype(float)
    base=base.merge(current[['TeamID','seed']],on='TeamID',how='left',validate='one_to_one')
    base['detailed_games']=base.TeamID.map(long.groupby('TeamID').size()).fillna(0)
    base['detailed_coverage']=base.detailed_games/base.games
    base['clean_games']=base.TeamID.map(long.loc[long.clean].groupby('TeamID').size()).fillna(0)
    base['snapshot_day']=cutoff
    base['Gender'],base['Season']=gender,int(season)
    audit['Gender'],audit['Season']=gender,int(season)
    return base.sort_values('TeamID').reset_index(drop=True),audit


def pair_features(teams: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    """Arbitrary orientation supported for swap tests; tournament labels are not accepted."""
    require(not any(c in pairs for c in ['y','WScore','LScore']), 'Labels must be passed separately')
    keys=['Gender','Season','Team1ID','Team2ID']
    require(set(keys).issubset(pairs), 'Missing matchup keys')
    require(not pairs.duplicated(keys).any(), 'Duplicate matchups')
    require((pairs.Team1ID!=pairs.Team2ID).all(), 'Self matchup')
    require(not teams.duplicated(['Gender','Season','TeamID']).any(), 'Duplicate team snapshot')
    out=pairs[keys].reset_index(drop=True).copy()
    joined=out.copy()
    for p,k in [('a','Team1ID'),('b','Team2ID')]:
        renamed=teams.rename(columns={'TeamID':k,**{c:p+'_'+c for c in teams if c not in ['Gender','Season','TeamID']}})
        joined=joined.merge(renamed,on=['Gender','Season',k],how='left',validate='many_to_one')
    require(not joined[['a_seed','b_seed','a_games','b_games']].isna().any().any(), 'Missing team snapshot or seed')
    require((joined[['a_detailed_coverage','b_detailed_coverage']]>=0.80).all().all(), 'Detailed coverage below 80%')
    require((joined[['a_detailed_games','b_detailed_games']]>=10).all().all(), 'Fewer than 10 detailed games')
    require((joined[['a_clean_games','b_clean_games']]>=5).all().all(), 'Fewer than 5 clean games')
    for c in CONTROL+RESIDUAL+PROFILE:
        out['diff_'+c]=joined['a_'+c]-joined['b_'+c]
    means,variances=[],[]
    for p,q in [('a','b'),('b','a')]:
        rates={}
        for r in ('two','three','share'):
            require(np.allclose(joined['a_profile_'+r+'_league'],joined['b_profile_'+r+'_league']), 'Inconsistent league intercepts')
            rates[r]=np.clip(joined[p+'_profile_'+r+'_league']+joined[p+'_profile_'+r+'_offense']+
                             joined[q+'_profile_'+r+'_allowance'],0.01,0.99)
        s,p2,p3=rates['share'],rates['two'],rates['three']
        mean=2*(1-s)*p2+3*s*p3
        var=4*(1-s)*p2+9*s*p3-mean**2
        means.append(mean)
        variances.append(np.maximum(var,0.01))
    out['profile_matchup_efg']=(means[0]-means[1])/2
    out['profile_variance_scaled_strength']=out.diff_strength/np.sqrt(variances[0]+variances[1])
    require(np.isfinite(out[ALL_FEATURES].to_numpy()).all(), 'Nonfinite engineered matchup features')
    return out


def tournament_pairs(results: pd.DataFrame, gender: str, seasons: list[int]) -> tuple[pd.DataFrame,np.ndarray]:
    require(max(seasons)<=2021, 'This exploratory kit cannot evaluate 2022–2026')
    # Main-draw games only; no First Four. Never build features from tournament scores.
    g=results.loc[results.Season.isin(seasons)&(results.DayNum>=136)].copy()
    require(not g.empty, 'No main-draw tournament targets in requested seasons')
    require((g.WScore>g.LScore).all(), 'Invalid tournament labels')
    pairs=pd.DataFrame({'Gender':gender,'Season':g.Season,'Team1ID':np.minimum(g.WTeamID,g.LTeamID),
                        'Team2ID':np.maximum(g.WTeamID,g.LTeamID),'y':(g.WTeamID<g.LTeamID).astype(int)})
    pairs=pairs.sort_values(['Season','Team1ID','Team2ID']).reset_index(drop=True)
    require(not pairs.duplicated(['Gender','Season','Team1ID','Team2ID']).any(), 'Duplicate physical tournament matchup')
    return pairs.drop(columns='y'),pairs.y.to_numpy()


def feature_registry() -> pd.DataFrame:
    rows=[]
    for name in ALL_FEATURES:
        family='anchor' if name in ANCHOR_COLS else 'residual' if name in RESIDUAL_COLS else 'profile'
        rows.append({'feature':name,'family':family,'new_candidate':family!='anchor',
                     'availability':'regular-season <= day 132; seeds known at bracket release',
                     'swap_parity':-1,'tournament_labels_used':False,
                     'status':'hypothesis, not proven gain','selection':'constant/support check on training rows only',
                     'meaning': ('Residual is not identified causal luck' if family=='residual' else
                                 'Opponent/site-adjusted shot-rate hypothesis; not shot tracking' if family=='profile' else
                                 'Existing concept held in fixed control')})
    return pd.DataFrame(rows)
