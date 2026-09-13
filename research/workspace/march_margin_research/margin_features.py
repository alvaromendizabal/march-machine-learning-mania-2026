"""Two pre-tournament margin representations; no tournament labels or model selection.

A large win is NOT automatically an outlier. Huber acts on opponent/home-adjusted
residuals. The separately tested tanh target compresses the observed margin itself.
"""
from __future__ import annotations
from itertools import combinations
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.sparse.csgraph import connected_components
from scipy.special import huber
from research_io import sf, require

YEARS = list(range(2013, 2020))
KEYS = ['Gender', 'Season', 'Team1ID', 'Team2ID']
BASE = list(sf.ANCHOR_COLS)
HUBER = ['diff_huber_margin_strength']
COMPRESSED = ['diff_compressed_margin_strength']
ALL = BASE + HUBER + COMPRESSED
RECIPES = {'anchor': BASE, 'anchor_huber': BASE + HUBER,
           'anchor_compressed': BASE + COMPRESSED, 'anchor_both': ALL}
PARAMETERS = {'cutoff':132, 'ridge_alpha':20., 'huber_delta_points':15.,
              'compression_scale_points':15., 'max_irls_steps':100,
              'gradient_acceptance':1e-5, 'primary':'huber_given_anchor'}
INPUTS = ['Season','DayNum','WTeamID','LTeamID','WScore','LScore','WLoc']


def legal_results(raw: pd.DataFrame, season: int) -> pd.DataFrame:
    require(season in YEARS, 'Only the declared 2013–2019 seasons are supported')
    return sf.legal_games(raw, season, detailed=False, cutoff=132)[INPUTS].copy()


def design(games: pd.DataFrame):
    teams=np.sort(pd.unique(games[['WTeamID','LTeamID']].to_numpy().ravel())).astype(int)
    ix={int(t):i for i,t in enumerate(teams)};n=len(games);k=len(teams)
    a=games.WTeamID.map(ix).to_numpy();b=games.LTeamID.map(ix).to_numpy()
    home=games.WLoc.map({'H':1.,'A':-1.,'N':0.}).to_numpy()
    x=sparse.csr_matrix((np.r_[np.ones(n),-np.ones(n),home],
        (np.tile(np.arange(n),3),np.r_[a,b,np.full(n,k)])),shape=(n,k+1))
    graph=sparse.csr_matrix((np.ones(2*n),(np.r_[a,b],np.r_[b,a])),shape=(k,k))
    components,groups=connected_components(graph,directed=False)
    y=(games.WScore-games.LScore).to_numpy(dtype=float)
    return teams,x,y,int(components),groups


def objective(theta,x,y,delta=15.,alpha=20.):
    residual=y-x@theta
    value=float(np.sum(huber(delta,residual))+alpha/2*np.dot(theta,theta))
    grad=np.asarray(-x.T@np.clip(residual,-delta,delta)).ravel()+alpha*theta
    return value,grad


def solve_huber(x,y,delta=15.,alpha=20.,max_steps=100,tolerance=1e-5):
    """Deterministic IRLS; stationarity checked independently, never loosened on retry."""
    require(alpha>0 and delta>0 and 1<=max_steps<=100 and tolerance>0,'Invalid solver settings')
    theta=np.zeros(x.shape[1]);eye=sparse.eye(x.shape[1],format='csc')
    trace=[]
    for step in range(max_steps+1):
        value,grad=objective(theta,x,y,delta,alpha);gn=float(np.max(np.abs(grad)))
        trace.append({'iteration':step,'objective':value,'gradient_max_abs':gn})
        require(np.isfinite(theta).all() and np.isfinite(value) and np.isfinite(grad).all(),'Nonfinite robust solver')
        if gn<=tolerance:return theta,pd.DataFrame(trace)
        require(step<max_steps,f'Huber stationarity not certified within {max_steps} steps; gradient={gn}')
        residual=y-x@theta
        weights=np.minimum(1.,delta/np.maximum(np.abs(residual),1e-300))
        matrix=(x.T@x.multiply(weights[:,None])+alpha*eye).tocsc()
        rhs=np.asarray(x.T@(weights*y)).ravel()
        candidate=spsolve(matrix,rhs)
        candidate_value=objective(candidate,x,y,delta,alpha)[0]
        require(candidate_value<=value+1e-10*max(1.,abs(value)),'IRLS objective increased')
        theta=candidate
    raise AssertionError('Unreachable')


def fit_rating(raw,season,kind):
    require(kind in ('huber','compressed'),'Unknown rating kind')
    games=legal_results(raw,season);teams,x,y,components,groups=design(games)
    if kind=='huber':
        theta,trace=solve_huber(x,y,delta=PARAMETERS['huber_delta_points'],
            alpha=PARAMETERS['ridge_alpha'],max_steps=PARAMETERS['max_irls_steps'],
            tolerance=PARAMETERS['gradient_acceptance'])
        residual=y-x@theta;weight=np.minimum(1.,15./np.maximum(np.abs(residual),1e-300))
        certificate=float(trace.gradient_max_abs.iloc[-1])
    else:
        target=15.*np.tanh(y/15.)
        matrix=(x.T@x+20.*sparse.eye(x.shape[1])).tocsc()
        theta=spsolve(matrix,np.asarray(x.T@target).ravel())
        gradient=np.asarray(x.T@(x@theta-target)).ravel()+20.*theta
        certificate=float(np.max(abs(gradient)));residual=target-x@theta
        weight=np.ones(len(y));trace=pd.DataFrame([{'iteration':1,'objective':float(.5*np.sum(residual**2)+10.*np.dot(theta,theta)),'gradient_max_abs':certificate}])
    require(certificate<=PARAMETERS['gradient_acceptance'] and np.isfinite(theta).all(),'Rating certificate failed')
    require(abs(theta[:-1].sum())<1e-7,'Team effects failed centering check')
    d={'Season':season,'kind':kind,'teams':len(teams),'regular_games':len(games),
       'graph_components':components,'iterations':int(trace.iteration.iloc[-1]),
       'gradient_max_abs':certificate,'home_effect':float(theta[-1]),
       'fraction_residuals_downweighted':float(np.mean(weight<1.)) if kind=='huber' else 0.,
       'max_absolute_input_margin':float(max(abs(y))), 'max_source_day':int(games.DayNum.max())}
    model={'Season':season,'kind':kind,'teams':teams.tolist(),'theta':theta.tolist(),
           'graph_groups':groups.tolist(),'parameters':PARAMETERS,'diagnostics':d}
    return model,trace


def build_matchups(base,models):
    require(set(models)=={'huber','compressed'},'Both rating models required')
    require(not base.duplicated(['Gender','Season','TeamID']).any(),'Duplicate team snapshot')
    require(base.Gender.eq('M').all() and base.Season.nunique()==1,'Men and one season required')
    season=int(base.Season.iloc[0]);selected=base.loc[base.seed.notna()].sort_values('TeamID')
    require(len(selected)>=2 and np.isfinite(selected[sf.CONTROL].to_numpy(dtype=float)).all(),'Missing seeded-team controls')
    teams=selected.TeamID.astype(int).to_list();look=selected.set_index('TeamID')
    pairs=pd.DataFrame(combinations(teams,2),columns=['Team1ID','Team2ID'])
    pairs.insert(0,'Season',season);pairs.insert(0,'Gender','M')
    for f in sf.CONTROL:pairs['diff_'+f]=look.loc[pairs.Team1ID,f].to_numpy()-look.loc[pairs.Team2ID,f].to_numpy()
    profiles=selected[['Gender','Season','TeamID','seed','strength']].copy()
    for kind,m in models.items():
        require(m['Season']==season and m['kind']==kind and m['parameters']==PARAMETERS,'Rating model contract mismatch')
        ix={int(t):i for i,t in enumerate(m['teams'])}
        require(set(teams).issubset(ix),'Missing rating for a seeded team')
        idx=np.array([ix[t] for t in teams]);groups=np.array(m['graph_groups'])
        require(len(np.unique(groups[idx]))==1,'Seeded teams span disconnected schedule components')
        rating=pd.Series(np.array(m['theta'])[:-1],index=m['teams'])
        pairs['diff_'+kind+'_margin_strength']=rating.loc[pairs.Team1ID].to_numpy()-rating.loc[pairs.Team2ID].to_numpy()
        profiles[kind+'_margin_strength']=profiles.TeamID.map(rating)
    require(np.isfinite(pairs[ALL]).all().all() and not pairs.duplicated(KEYS).any(),'Invalid pair features')
    return pairs,profiles,{'Season':season,'seeded_teams':len(teams),'potential_pairs':len(pairs),'label_inputs':False}


def registry():
    rows=[{'feature':f,'family':'reference','new_candidate':False,'description':'Unchanged frozen reference input'} for f in BASE]
    rows += [{'feature':HUBER[0],'family':'residual_robustness','new_candidate':True,
              'description':'Opponent/home-adjusted margin rating using Huber residual loss, delta 15, alpha 20'},
             {'feature':COMPRESSED[0],'family':'target_compression','new_candidate':True,
              'description':'Opponent/home-adjusted ridge rating of 15*tanh(observed margin/15), alpha 20'}]
    result=pd.DataFrame(rows);result['cutoff_day']=132;result['availability']='Pre-tournament regular season only'
    result['swap_parity']=-1;result['evidence']='Hypothesis; no promotion from feature count'
    return result
