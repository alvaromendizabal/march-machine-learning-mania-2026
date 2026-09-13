"""Round 08: basketball possession-accounting hypotheses, never tournament labels.

Six ordinary rate controls are NOT novel to the project. Four nonlinear matchup
candidates combine shooting, lost possessions, second chances and free throws.
The accounting model is approximate; its contrasts are not causal effects.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit, logit

sys.path.insert(0, str(Path(__file__).resolve().parent / 'frozen'))
import shot_features as sf

PARAMETERS = {'cutoff_day':132, 'prior_opportunities':100., 'ft_possession_weight':0.475,
              'probability_epsilon':1e-6, 'matchup_rule':'logit_offense + logit_allowance - logit_league',
              'ftr_rule':'offense * allowance / league', 'ft_accuracy_rule':'offense_only',
              'rebound_approximation':'field_goal_miss_fraction * offensive_rebound_share'}
BASE = list(sf.ANCHOR_COLS)
RATE_NAMES = [p+n for p in ('','opp_') for n in ('tov_rate','orb_rate','fta_rate')]
RATES = ['diff_'+n for n in RATE_NAMES]
MECHANISM = ['possession_net_pp100','possession_rebound_edge_pp100',
             'possession_turnover_edge_pp100','possession_free_throw_edge_pp100']
RECIPES = {'anchor':BASE, 'anchor_rates':BASE+RATES,
           'anchor_mechanism':BASE+MECHANISM, 'anchor_both':BASE+RATES+MECHANISM}
ALL = RECIPES['anchor_both']
require = sf.require


def accounting(two, three, share, free, turnover, rebound, fta):
    """Approximate neutral points/possession derived from P=FGA-OR+TO+.475FTA.

    TO=t*P; OR approximately r*(1-FG%)*FGA. Hence
    PPP=(1-t)*(2*eFG%+FT%*FTA/FGA)/(1-r*(1-FG%)+.475*FTA/FGA).
    Omits FT rebounds, team/dead-ball rebounds, and changing state after a rebound.
    """
    vals = np.broadcast_arrays(*[np.asarray(a,dtype=float) for a in (two,three,share,free,turnover,rebound,fta)])
    require(all(np.isfinite(a).all() for a in vals),'Nonfinite accounting input')
    require(all(((a>=0)&(a<=1)).all() for a in vals[:6]),'Probability outside [0,1]')
    require((vals[6]>=0).all(),'Negative free-throw attempt ratio')
    two,three,share,free,turnover,rebound,fta = vals
    fg=(1-share)*two+share*three
    efg=(1-share)*two+1.5*share*three
    denominator=1-rebound*(1-fg)+PARAMETERS['ft_possession_weight']*fta
    require((denominator>1e-8).all(),'Unsupported accounting denominator')
    value=(1-turnover)*(2*efg+free*fta)/denominator
    require(np.isfinite(value).all(),'Nonfinite accounting result')
    return value


def blend_probability(offense, allowance, league):
    """Fixed neutral odds-combination hypothesis, not learned opponent adjustment."""
    e=PARAMETERS['probability_epsilon']
    vals=[np.asarray(a,dtype=float) for a in (offense,allowance,league)]
    require(all(np.isfinite(a).all() and ((a>=0)&(a<=1)).all() for a in vals),'Invalid rate blend')
    o,d,l=[np.clip(a,e,1-e) for a in vals]
    return expit(logit(o)+logit(d)-logit(l))


def build_snapshot(detailed:pd.DataFrame, base:pd.DataFrame, gender:str, season:int):
    """Season-local totals and priors. Snapshot has no tournament-label argument."""
    require(gender in ('M','W'),'Unknown gender')
    require(set(['Gender','Season','TeamID','seed']).issubset(base),'Missing base keys')
    require(base.Gender.eq(gender).all() and base.Season.eq(season).all(),'Base snapshot mismatch')
    require(not base.TeamID.duplicated().any(),'Duplicate base team')
    g=sf.legal_games(detailed,season,detailed=True,cutoff=PARAMETERS['cutoff_day'])
    long=sf.long_games(g,detailed=True)
    totals=long.groupby('TeamID',sort=True).sum(numeric_only=True)
    out=pd.DataFrame(index=totals.index)
    league={}; prior=PARAMETERS['prior_opportunities']
    for side in ('','opp_'):
        v=lambda n:totals[side+n]
        own_pos=v('FGA')-v('OR')+v('TO')+PARAMETERS['ft_possession_weight']*v('FTA')
        require((own_pos>v('TO')).all(),'Turnovers exhaust estimated possessions')
        opportunities={
          'two':(v('FGM')-v('FGM3'),v('FGA')-v('FGA3')),
          'three':(v('FGM3'),v('FGA3')), 'share':(v('FGA3'),v('FGA')),
          'free':(v('FTM'),v('FTA')), 'tov_rate':(v('TO'),own_pos),
          'orb_rate':(v('OR'),v('OR')+totals[('opp_' if not side else '')+'DR'])}
        for name,(made,attempts) in opportunities.items():
            require(((made>=0)&(attempts>=made)).all(),'Invalid rate opportunity counts: '+side+name)
            center=float((made.sum()+.5)/(attempts.sum()+1.))
            out[side+name]=(made+prior*center)/(attempts+prior)
            if not side:league[name]=center
        fta,fga=v('FTA'),v('FGA')
        require((fga>0).all(),'No field-goal attempts')
        center=float((fta.sum()+.5)/(fga.sum()+1.))
        out[side+'fta_rate']=(fta+prior*center)/(fga+prior)
        if not side:league['fta_rate']=center
    for n,v in league.items():out['league_'+n]=v
    out['detail_games']=long.groupby('TeamID').size()
    out['rebound_opportunities']=totals.OR+totals.opp_DR
    out['turnover_opportunities']=totals.FGA-totals.OR+totals.TO+.475*totals.FTA
    out['Gender']=gender;out['Season']=season
    out=base[['Gender','Season','TeamID','seed']].merge(out.reset_index(),on=['Gender','Season','TeamID'],how='left',validate='one_to_one')
    seeded=out.loc[out.seed.notna()]
    require(len(seeded)>0 and not seeded.drop(columns='seed').isna().any().any(),'Incomplete seeded-team rate support')
    require((seeded.detail_games>=10).all(),'Fewer than ten detailed games for a seeded team')
    cover={'Gender':gender,'Season':season,'teams':len(out),'seeded_teams':len(seeded),
           'min_seeded_detail_games':int(seeded.detail_games.min()),
           'min_seeded_rebound_opportunities':float(seeded.rebound_opportunities.min()),
           'min_seeded_turnover_opportunities':float(seeded.turnover_opportunities.min()),
           'max_regular_day':int(g.DayNum.max()),'tournament_labels_read':False,'new_rating_fits':0}
    return out.drop(columns='seed'),cover


def pair_features(base:pd.DataFrame,rates:pd.DataFrame,pairs:pd.DataFrame):
    """Feature-only arbitrary orientations, with explicit 1:1 and many:1 checks."""
    keys=['Gender','Season','TeamID'];pkeys=['Gender','Season','Team1ID','Team2ID']
    require(set(pkeys).issubset(pairs),'Missing pair keys')
    require(not pairs.duplicated(pkeys).any(),'Duplicate pair')
    require(pairs.Team1ID.ne(pairs.Team2ID).all(),'Self matchup')
    require(not base.duplicated(keys).any() and not rates.duplicated(keys).any(),'Duplicate snapshot key')
    merged=base[keys+sf.CONTROL].merge(rates,on=keys,how='left',validate='one_to_one')
    table=pairs[pkeys].reset_index(drop=True).copy()
    for prefix,key in [('a','Team1ID'),('b','Team2ID')]:
        renamed=merged.rename(columns={'TeamID':key,**{c:prefix+'_'+c for c in merged if c not in keys}})
        table=table.merge(renamed,on=['Gender','Season',key],how='left',validate='many_to_one')
    cols=sf.CONTROL+RATE_NAMES+['two','three','share','free','opp_two','opp_three','opp_share']+['league_'+n for n in ['two','three','share','tov_rate','orb_rate','fta_rate']]
    require(np.isfinite(table[[p+'_'+c for p in ('a','b') for c in cols]].to_numpy(dtype=float)).all(),'Missing or nonfinite matchup input')
    out=pairs[pkeys].reset_index(drop=True).copy()
    for name in sf.CONTROL+RATE_NAMES:out['diff_'+name]=table['a_'+name]-table['b_'+name]
    values=[];diagnostics=[]
    for side,other in [('a','b'),('b','a')]:
        mix={}
        for n in ['two','three','share','tov_rate','orb_rate']:
            require(np.allclose(table['a_league_'+n],table['b_league_'+n],atol=0,rtol=0),'League-prior mismatch')
            mix[n]=blend_probability(table[side+'_'+n],table[other+'_opp_'+n],table[side+'_league_'+n])
        mix['free']=table[side+'_free'].to_numpy()
        mix['fta_rate']=(table[side+'_fta_rate']*table[other+'_opp_fta_rate']/table[side+'_league_fta_rate']).to_numpy()
        args=[mix[n] for n in ['two','three','share','free','tov_rate','orb_rate','fta_rate']]
        total=accounting(*args)
        noreb=list(args);noreb[5]=np.zeros(len(table))
        noto=list(args);noto[4]=np.zeros(len(table))
        noft=list(args);noft[6]=np.zeros(len(table))
        # Positive turnover value means less value lost when A minus B is formed.
        values.append(np.column_stack([total,total-accounting(*noreb),total-accounting(*noto),total-accounting(*noft)])*100)
        d=pd.DataFrame({side+'_'+n:v for n,v in mix.items()});d[side+'_proxy_pp100']=100*total
        diagnostics.append(d)
    out[MECHANISM]=values[0]-values[1]
    require(np.isfinite(out[ALL].to_numpy()).all(),'Nonfinite constructed feature')
    diagnostic=pd.concat([out[pkeys],*diagnostics],axis=1)
    return out,diagnostic


def registry():
    records=[]
    for n in BASE:
        records.append({'feature':n,'family':'unchanged_reference','new_definition':False,'description':'Exact cached 16-input reference control'})
    for n in RATES:
        records.append({'feature':n,'family':'basic_rate_controls','new_definition':False,
                        'description':'Team difference in shrunk offense/allowed turnover, rebound, or FTA/FGA rate; concept already in project'})
    descriptions=['Neutral scoring proxy difference from possession accounting',
                  'Difference in scoring proxy gain when rebounds are enabled instead of zero',
                  'Difference in negative scoring proxy loss from turnovers instead of zero turnovers',
                  'Difference in scoring proxy change when FTA/FGA is enabled instead of zero']
    for n,description in zip(MECHANISM,descriptions):
        records.append({'feature':n,'family':'possession_accounting','new_definition':True,'description':description})
    frame=pd.DataFrame(records)
    frame['availability']='regular-season games through day 132; seeds in reference after field announcement'
    frame['leakage_policy']='No tournament labels in snapshots or matchup construction; priors are same-season regular-only'
    frame['swap_parity']=-1;frame['hypothesis_status']='Unproven; fixed-formula exploratory ablation required'
    return frame
