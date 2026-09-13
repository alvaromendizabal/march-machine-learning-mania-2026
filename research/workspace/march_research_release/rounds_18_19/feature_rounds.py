"""Opportunity-weighted opponent adjustment. Prepared code; not executed by ChatGPT.

Builders accept pre-cutoff regular-season box scores only. Tournament outcomes
are attached separately in round_workflow.py. Coefficients are descriptive
season-local rate effects, NOT calibrated probabilities or causal effects.
"""
from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.linalg import cho_factor, cho_solve
from scipy.sparse.csgraph import connected_components
from research_io import require
import consensus_reference as cf

YEARS = list(range(2013, 2020)) + list(range(2021, 2026))
VALIDATION = [2022, 2023, 2024, 2025]
BASE = list(cf.ALL)
FAMILIES = {'18': ['offensive_rebounding', 'assisted_makes'],
            '19': ['three_point_share', 'free_throw_share']}
# Sign is the direction of increasing target share; this need not imply better performance.
TARGETS = {
    'offensive_rebounding': ('OR', 'rebound_opportunities', 1),
    'assisted_makes': ('Ast', 'FGM', 1),
    'three_point_share': ('three_points', 'points', 1),
    'free_throw_share': ('FTM', 'points', 1),
}

FEATURES = {r: [f'adjusted_{t}_{side}' for t in targets for side in ('offense', 'defense')]
            for r, targets in FAMILIES.items()}
CONTROLS = {r: [f'rate_{t}_{side}' for t in targets for side in ('offense', 'defense')]
            for r, targets in FAMILIES.items()}
DUPLICATE = [f'duplicate_control_{i}' for i in range(1, 5)]
PARAMETERS = {r: {'cutoff_day': 132, 'alpha': 20.0, 'prior_exposure': 100.0,
                 'minimum_seeded_exposure': 50.0,
                 'weight_normalization': 'denominator / mean(denominator)',
                 'normal_equation_relative_tolerance': 1e-9,
                 'feature_units': 'events per 100 opportunities',
                 'coefficient_sign': 'offense positive = greater target share; defense positive = lower opponent target share; not intrinsically better',
                 'targets': targets} for r, targets in FAMILIES.items()}


def recipes(round_id: str) -> dict[str, list[str]]:
    require(round_id in FAMILIES, 'Unsupported round')
    a, b = FAMILIES[round_id]
    controls = BASE + CONTROLS[round_id]
    return {'reference': BASE.copy(), 'rates': controls,
            a: controls + FEATURES[round_id][:2],
            b: controls + FEATURES[round_id][2:],
            'both': controls + FEATURES[round_id],
            # Each unadjusted rate is duplicated once; no new information.
            'duplicate_control': controls + DUPLICATE}


def legal_long(compact: pd.DataFrame, detailed: pd.DataFrame, season: int,
               round_id: str) -> pd.DataFrame:
    """Validate legal rows before orienting each physical game twice.

    No generic dropna, outcome-based filtering, or negative-count clipping.
    Undefined zero-opportunity rows are handled target-by-target in fit_target.
    """
    require(season in YEARS and round_id in FAMILIES, 'Unsupported season/round')
    keys = ['Season', 'DayNum', 'WTeamID', 'LTeamID']
    for name, df in [('compact', compact), ('detailed', detailed)]:
        require(set(keys + ['WLoc', 'WScore', 'LScore']).issubset(df), 'Missing '+name+' identity fields')
    c = compact.loc[compact.Season.eq(season) & compact.DayNum.le(132)].copy()
    d = detailed.loc[detailed.Season.eq(season) & detailed.DayNum.le(132)].copy()
    require(not c.empty and not d.empty, 'Missing legal regular-season rows')
    require(not c.duplicated(keys).any() and not d.duplicated(keys).any(), 'Duplicate game keys')
    # Canonical physical identities also reject swapped winner/loser duplicates.
    for df in [c, d]:
        physical = pd.DataFrame({'season': df.Season, 'day': df.DayNum,
            'lo': np.minimum(df.WTeamID, df.LTeamID), 'hi': np.maximum(df.WTeamID, df.LTeamID)})
        require(not physical.duplicated().any(), 'Duplicate physical game')
        require(df.WLoc.isin(['H', 'A', 'N']).all(), 'Invalid game location')
        require((df.WScore > df.LScore).all() and (df.WTeamID != df.LTeamID).all(), 'Invalid winner or teams')
    box = ['FGA', 'FGM', 'FGA3', 'FGM3', 'FTA', 'FTM', 'OR', 'TO']
    box += ['DR','Ast'] if round_id == '18' else []
    numeric = keys + ['WScore', 'LScore'] + [side+b for side in ['W', 'L'] for b in box]
    require(set(numeric).issubset(d), 'Missing required detailed box fields: '+str(sorted(set(numeric)-set(d))))
    values = d[numeric].to_numpy(dtype=float)
    require(np.isfinite(values).all() and (values >= 0).all() and (values == np.floor(values)).all(),
            'Nonfinite, negative or noninteger box values')
    for side in ['W', 'L']:
        require((d[side+'FGM'] <= d[side+'FGA']).all() and (d[side+'FGM3'] <= d[side+'FGA3']).all(), 'Makes exceed attempts')
        require((d[side+'FGA3'] <= d[side+'FGA']).all() and (d[side+'FGM3'] <= d[side+'FGM']).all(), 'Invalid three-point subset')
        require((d[side+'FTM'] <= d[side+'FTA']).all(), 'FT makes exceed attempts')
    ident = keys + ['WScore', 'LScore', 'WLoc']
    check = d[ident].merge(c[ident], on=ident, how='left', indicator=True, validate='one_to_one')
    require(check['_merge'].eq('both').all(), 'Detailed games disagree with compact results')
    d = d.sort_values(keys).reset_index(drop=True)
    sides = []
    for own, opp, sign in [('W', 'L', 1), ('L', 'W', -1)]:
        out = pd.DataFrame({'Season': d.Season, 'DayNum': d.DayNum,
            'TeamID': d[own+'TeamID'], 'OpponentID': d[opp+'TeamID'],
            'home': sign*d.WLoc.map({'H': 1., 'A': -1., 'N': 0.}), 'points':d[own+'Score']})
        for b in box:
            out[b] = d[own+b].to_numpy()
            out['opp_'+b] = d[opp+b].to_numpy()
        sides.append(out)
    long = pd.concat(sides, ignore_index=True).sort_values(['DayNum', 'TeamID', 'OpponentID']).reset_index(drop=True)
    own_pos = long.FGA-long.OR+long.TO+.475*long.FTA
    opp_pos = long.opp_FGA-long.opp_OR+long.opp_TO+.475*long.opp_FTA
    require((own_pos > 0).all() and (opp_pos > 0).all(), 'Nonpositive possession estimate')
    long['possessions'] = (own_pos+opp_pos)/2
    long['two_attempts'] = long.FGA-long.FGA3
    if round_id == '18':
        long['rebound_opportunities'] = long.OR + long.opp_DR
        require((long.Ast <= long.FGM).all(), 'Assists exceed made field goals; inspect before excluding or imputing')
    else:
        long['three_points'] = 3*long.FGM3
        require((long.points == 2*long.FGM+long.FGM3+long.FTM).all(),
                'Score does not reconcile to field goals and free throws; inspect source')
        require((long.points > 0).all(), 'Scoring shares require positive points')
    return long


def fit_target(long: pd.DataFrame, target: str, seeded: list[int],
               alpha: float = 20., prior_exposure: float = 100.,
               minimum_exposure: float = 50.) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    """One deterministic opportunity-weighted ridge solve; no iterative optimizer.

    Minimize sum_i w_i (rate_i - b0 - attack_i - defense_j - h*home_i)^2
    + alpha*||[attack, defense, h]||^2. Intercept is unpenalized.
    Both coefficient sets have the declared sign convention after fitting. We fit season-local
    box outcomes, not NCAA tournament targets. Rates are not binomial models.
    """
    require(target in TARGETS and alpha > 0 and prior_exposure > 0, 'Invalid target/penalty')
    num, den, off_sign = TARGETS[target]
    require(set(['TeamID', 'OpponentID', 'home', num, den]).issubset(long), 'Missing rate fields')
    require(np.isfinite(long[[num, den, 'home']].to_numpy(dtype=float)).all(), 'Nonfinite input rate fields')
    require((long[den] >= 0).all() and (long[num] >= 0).all(), 'Negative events/opportunities')
    require(long.home.isin([-1.,0.,1.]).all(), 'Invalid venue encoding')
    keep = long[den] > 0
    require(not ((~keep) & long[num].ne(0)).any(), 'Events without opportunities; inspect source data')
    g = long.loc[keep].copy()
    require(len(g) > 0, 'No positive opportunity rows')
    require(np.isfinite(g[[num, den, 'home']].to_numpy()).all() and (g[num] >= 0).all(), 'Invalid rate observations')
    teams = np.sort(pd.unique(g[['TeamID', 'OpponentID']].to_numpy().ravel()).astype(int))
    require(set(seeded).issubset(set(teams)), 'Seeded team lacks rate observations')
    require(len(teams) <= 500, 'Unexpected team universe; bounded dense solve refused')
    k, n = len(teams), len(g)
    lookup = {int(t): i for i, t in enumerate(teams)}
    ai = g.TeamID.map(lookup).to_numpy(dtype=int)
    di = g.OpponentID.map(lookup).to_numpy(dtype=int)
    adjacency = sparse.csr_matrix((np.ones(2*n), (np.r_[ai,di], np.r_[di,ai])), shape=(k,k))
    nc, components = connected_components(adjacency, directed=False)
    require(len({int(components[lookup[int(t)]]) for t in seeded}) == 1, 'Seeded teams span disconnected opponent graph')
    a_support = g.groupby('TeamID')[den].sum().reindex(teams, fill_value=0.)
    d_support = g.groupby('OpponentID')[den].sum().reindex(teams, fill_value=0.)
    require((a_support.loc[seeded] >= minimum_exposure).all() and (d_support.loc[seeded] >= minimum_exposure).all(),
            'Seeded rate exposure below declared support threshold')
    weight = g[den].to_numpy(dtype=float)/float(g[den].mean())
    y = g[num].to_numpy(dtype=float)/g[den].to_numpy(dtype=float)
    row = np.tile(np.arange(n), 4)
    col = np.r_[ai, di+k, np.full(n,2*k), np.full(n,2*k+1)]
    data = np.r_[np.ones(2*n), g.home.to_numpy(dtype=float), np.ones(n)]
    X = sparse.csr_matrix((data,(row,col)),shape=(n,2*k+2))
    penalty = np.r_[np.full(2*k+1,alpha),0.]
    H = (X.T @ X.multiply(weight[:,None])).toarray()
    H[np.diag_indices_from(H)] += penalty
    rhs = np.asarray(X.T@(weight*y)).ravel()
    theta = cho_solve(cho_factor(H, lower=True, check_finite=True), rhs, check_finite=True)
    error = H@theta-rhs
    relative = float(np.max(np.abs(error))/max(1.,float(np.max(np.abs(rhs)))))
    require(np.isfinite(theta).all() and relative <= 1e-9, 'Normal-equation numerical certificate failed')
    pred = np.asarray(X@theta).ravel()
    league = float(g[num].sum()/g[den].sum())
    a_num = g.groupby('TeamID')[num].sum().reindex(teams,fill_value=0.)
    d_num = g.groupby('OpponentID')[num].sum().reindex(teams,fill_value=0.)
    rate_a = (a_num+prior_exposure*league)/(a_support+prior_exposure)
    rate_d = (d_num+prior_exposure*league)/(d_support+prior_exposure)
    table = pd.DataFrame({'TeamID':teams,
        f'adjusted_{target}_offense':100*off_sign*theta[:k],
        f'adjusted_{target}_defense':-100*off_sign*theta[k:2*k],
        f'rate_{target}_offense':100*off_sign*rate_a.to_numpy(),
        f'rate_{target}_defense':-100*off_sign*rate_d.to_numpy(),
        f'exposure_{target}_offense':a_support.to_numpy(),
        f'exposure_{target}_defense':d_support.to_numpy()})
    model = {'target':target,'teams':teams.tolist(),'coefficients':theta.tolist(),
        'alpha':float(alpha),'prior_exposure':float(prior_exposure),
        'weight_mean_denominator':float(g[den].mean()),'league_rate':league,
        'coefficient_order':'offense, defense, home, intercept',
        'solver':'positive-definite Cholesky weighted ridge','tournament_labels_read':False}
    diagnostic = {'target':target,'Season':int(long.Season.iloc[0]),'team_rows':n,
        'teams':k,'physical_games':int(len(long)//2),'zero_opportunity_rows':int((~keep).sum()),
        'graph_components':int(nc),'weighted_rmse':float(np.sqrt(np.average((pred-y)**2,weights=weight))),
        'normal_equation_relative_error':relative,'league_rate':league,
        'home_effect_per100':float(theta[-2]*100),
        'minimum_seeded_exposure':float(min(a_support.loc[seeded].min(),d_support.loc[seeded].min())),
        'in_sample_predictions_outside_0_1':int(((pred<0)|(pred>1)).sum()),
        'diagnostic_scope':'descriptive regular-season rate fit; not held-out metric'}
    return table, model, diagnostic


def pair_tables(base: pd.DataFrame, pairs: pd.DataFrame, tables: list[pd.DataFrame],
                round_id: str) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    require(len(tables)==2 and round_id in FAMILIES, 'Two target tables required')
    require(set(cf.KEYS+BASE).issubset(pairs) and not pairs.duplicated(cf.KEYS).any(), 'Invalid reference pair table')
    require((pairs.Team1ID < pairs.Team2ID).all() and pairs.Season.nunique()==1, 'Expected one-season ordered pairs')
    all_cols = FEATURES[round_id]+CONTROLS[round_id]
    merged = tables[0].merge(tables[1], on='TeamID', how='outer', validate='one_to_one')
    ids = set(pairs.Team1ID)|set(pairs.Team2ID)
    require(ids.issubset(set(merged.TeamID)), 'Missing seeded adjustment table')
    indexed = merged.set_index('TeamID')
    require(np.isfinite(indexed.loc[sorted(ids),all_cols].to_numpy()).all(), 'Missing candidate or control value')
    out = pairs[cf.KEYS+BASE].copy()
    for c in all_cols:
        out[c] = pairs.Team1ID.map(indexed[c])-pairs.Team2ID.map(indexed[c])
    for duplicate, control in zip(DUPLICATE,CONTROLS[round_id],strict=True):out[duplicate]=out[control]
    require(np.isfinite(out[BASE+all_cols+DUPLICATE].to_numpy()).all(), 'Nonfinite matchup feature')
    profile_columns=[c for c in ['Gender','Season','TeamID','strength','seed','games'] if c in base]
    profiles=base[profile_columns].merge(merged,on='TeamID',how='left',validate='one_to_one')
    support=pairs[cf.KEYS].copy()
    for target in FAMILIES[round_id]:
        minimum=np.minimum(indexed[f'exposure_{target}_offense'],indexed[f'exposure_{target}_defense'])
        support[f'min_exposure_{target}']=np.minimum(pairs.Team1ID.map(minimum),pairs.Team2ID.map(minimum))
    support['minimum_exposure']=support[[c for c in support if c.startswith('min_exposure_')]].min(axis=1)
    coverage=pd.DataFrame([{'Season':int(pairs.Season.iloc[0]),'round':round_id,
        'teams':len(ids),'potential_matchups':len(pairs),'candidate_count':4,'rate_controls':4,
        'minimum_exposure':float(support.minimum_exposure.min()),'tournament_labels_read':False}])
    return out,profiles,coverage,support


def registry(round_id: str) -> pd.DataFrame:
    rows=[]
    for f in BASE:rows.append({'feature':f,'family':'frozen_consensus_reference','role':'reference','new_candidate':False})
    for t in FAMILIES[round_id]:
        for side in ['offense','defense']:
            for prefix,role in [('rate','unadjusted_rate_control'),('adjusted','candidate')]:
                rows.append({'feature':f'{prefix}_{t}_{side}','family':t,'role':role,'new_candidate':role=='candidate'})
    for f in DUPLICATE:rows.append({'feature':f,'family':'duplication_sensitivity','role':'diagnostic_only','new_candidate':False})
    out=pd.DataFrame(rows)
    out['cutoff_day']=132;out['swap_parity']=-1
    out['availability']='same-season regular-season detailed box scores through day 132; seeds only select forecast pairs'
    out['units']='signed events per 100 opportunities, except frozen reference'
    out['evidence']='prepared hypothesis; greater assist or point share is not intrinsically better; decide from controlled Brier'
    out['interpretation']='positive offense = higher target rate; positive defense = lower opponent target rate'
    return out
