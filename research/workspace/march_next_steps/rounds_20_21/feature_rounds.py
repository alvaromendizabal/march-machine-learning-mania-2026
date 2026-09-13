"""Two fixed matchup-context experiments. Prepared, not executed by the assistant.

No tournament labels enter this module. All outputs are antisymmetric matchup
features. Round 20 tests symmetric risk context interacting with strength gaps;
round 21 tests performance against similar opponent styles, excluding direct
meetings from the response aggregation. These are descriptive hypotheses.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from research_io import require
import consensus_reference as cf

YEARS=list(range(2013,2020))+list(range(2021,2026))
VALIDATION=[2022,2023,2024,2025]
BASE=list(cf.ALL)
FAMILIES={'20':['pace_context','shot_variance_context'],
          '21':['pace_spacing_response','pressure_rebounding_response']}
FEATURES={'20':['pace_x_strength','pace_x_consensus','variance_x_strength','variance_x_consensus'],
          '21':['spacing_offense_response','spacing_defense_response','pressure_offense_response','pressure_defense_response']}
CONTROLS={'20':['diff_pace_mean','diff_pace_sd','diff_three_share','diff_shot_variance'],
          '21':['diff_neutral_offense','diff_neutral_defense','diff_nonhome_offense','diff_nonhome_defense']}
DUPLICATE=[f'duplicate_control_{i}' for i in range(1,5)]
PARAMETERS={r:{'cutoff_day':132,'new_candidates':4,'direct_controls':4,'rating_fits':0,
    'minimum_detailed_games':10,'shot_prior_attempts':50.,'shrinkage_opponents':5.,
    'style_radius_standard_deviations':2.,'style_scale':'all legal teams, within-season population SD',
    'home_efficiency_adjustment':3.,'risk_multiplier':'square root of ratio to contemporary league context',
    'no_tournament_outcomes':True} for r in FAMILIES}


def recipes(rid):
    require(rid in FAMILIES,'Unknown round')
    a,b=FAMILIES[rid];controls=BASE+CONTROLS[rid]
    return {'reference':BASE.copy(),'rates':controls,a:controls+FEATURES[rid][:2],
        b:controls+FEATURES[rid][2:],'both':controls+FEATURES[rid],
        'duplicate_control':controls+DUPLICATE}


def legal_long(compact,detailed,season,rid):
    require(season in YEARS and rid in FAMILIES,'Unsupported season/round')
    keys=['Season','DayNum','WTeamID','LTeamID']
    core=keys+['WScore','LScore','WLoc']
    box=['FGM','FGA','FGM3','FGA3','FTM','FTA','OR','DR','TO']
    require(set(core).issubset(compact) and set(core+['NumOT']+[s+c for s in ['W','L'] for c in box]).issubset(detailed),'Missing game columns')
    c=compact.loc[compact.Season.eq(season)&compact.DayNum.le(132)].copy()
    d=detailed.loc[detailed.Season.eq(season)&detailed.DayNum.le(132)].copy()
    require(not c.empty and not d.empty,'Missing legal regular-season games')
    for frame in (c,d):
        v=frame[keys+['WScore','LScore']].to_numpy(dtype=float)
        require(np.isfinite(v).all() and (v>=0).all() and (v==np.floor(v)).all(),'Invalid integral identifiers/scores')
        require(frame.WLoc.isin(['H','A','N']).all() and (frame.WScore>frame.LScore).all(),'Invalid winner/location')
        require((frame.WTeamID!=frame.LTeamID).all(),'Self-match')
        physical=pd.DataFrame({'s':frame.Season,'d':frame.DayNum,'lo':np.minimum(frame.WTeamID,frame.LTeamID),'hi':np.maximum(frame.WTeamID,frame.LTeamID)})
        require(not physical.duplicated().any(),'Duplicate physical game')
    merge=d.merge(c[core],on=core,how='left',indicator=True,validate='one_to_one')
    require(merge['_merge'].eq('both').all(),'Detailed and compact game disagreement')
    values=d[['NumOT']+[s+b for s in ['W','L'] for b in box]].to_numpy(dtype=float)
    require(np.isfinite(values).all() and (values>=0).all() and (values==np.floor(values)).all(),'Invalid box counts')
    for s in ['W','L']:
        for m,a in [('FGM','FGA'),('FGM3','FGA3'),('FTM','FTA')]:require((d[s+m]<=d[s+a]).all(),'Makes exceed attempts')
        require((d[s+'FGM3']<=d[s+'FGM']).all() and (d[s+'FGA3']<=d[s+'FGA']).all(),'Impossible three-point subset')
        require((d[s+'FGM']-d[s+'FGM3']<=d[s+'FGA']-d[s+'FGA3']).all(),'Impossible two-point subset')
    out=[]
    for own,opp,sign in [('W','L',1),('L','W',-1)]:
        row=pd.DataFrame({'Season':d.Season,'DayNum':d.DayNum,'TeamID':d[own+'TeamID'],
            'OpponentID':d[opp+'TeamID'],'home':sign*d.WLoc.map({'H':1.,'A':-1.,'N':0.}),
            'points':d[own+'Score'],'allowed':d[opp+'Score'],'NumOT':d.NumOT})
        for b in box:row[b]=d[own+b].to_numpy();row['opp_'+b]=d[opp+b].to_numpy()
        out.append(row)
    g=pd.concat(out,ignore_index=True).sort_values(['DayNum','TeamID','OpponentID']).reset_index(drop=True)
    po=g.FGA-g.OR+g.TO+.475*g.FTA;pd_=g.opp_FGA-g.opp_OR+g.opp_TO+.475*g.opp_FTA
    require((po>0).all() and (pd_>0).all(),'Nonpositive possessions; no clipping')
    g['possessions']=(po+pd_)/2;g['pace']=g.possessions*40/(40+5*g.NumOT)
    g['eff']=100*g.points/g.possessions;g['allowed_eff']=100*g.allowed/g.possessions
    return g


def profiles(long):
    """Known-at-cutoff aggregates; no learned tournament preprocessing."""
    grouped=long.groupby('TeamID',sort=True)
    t=grouped.sum(numeric_only=True)
    p=grouped.agg(pace_mean=('pace','mean'),pace_sd=('pace','std'),detailed_games=('pace','size'))
    two=t.FGA-t.FGA3;made2=t.FGM-t.FGM3
    # Jeffreys half-event safeguards define finite priors, even in tiny fixtures.
    l2=(made2.sum()+.5)/(two.sum()+1);l3=(t.FGM3.sum()+.5)/(t.FGA3.sum()+1)
    q=(t.FGA3+50*(t.FGA3.sum()+.5)/(t.FGA.sum()+1))/(t.FGA+50)
    p2=(made2+50*l2)/(two+50);p3=(t.FGM3+50*l3)/(t.FGA3+50)
    e=2*(1-q)*p2+3*q*p3;e2=4*(1-q)*p2+9*q*p3
    p['three_share']=q;p['shot_variance']=e2-e**2
    p['forced_turnovers']=(t.opp_TO+20*(t.opp_TO.sum()/t.possessions.sum()))/(t.possessions+20)
    den=t.OR+t.opp_DR
    p['offensive_rebounds']=(t.OR+20*((t.OR.sum()+.5)/(den.sum()+1)))/(den+20)
    require(np.isfinite(p.to_numpy(dtype=float)).all() and (p.shot_variance>0).all(),'Invalid profile values')
    return p


def context20(p, a, b, gap, rankgap):
    league_pace=float(p.pace_mean.mean());league_var=float(p.shot_variance.mean())
    pair_pace=(p.loc[a,'pace_mean'].to_numpy()+p.loc[b,'pace_mean'].to_numpy())/2
    pair_var=(p.loc[a,'shot_variance'].to_numpy()+p.loc[b,'shot_variance'].to_numpy())/2
    speed=np.sqrt(pair_pace/league_pace)-1
    variance=np.sqrt(league_var/pair_var)-1
    # Context proxies, not calibrated probabilities or score forecasts.
    return np.column_stack([gap*speed,rankgap*speed,gap*variance,rankgap*variance])


def weighted_response(group, target, style, columns, scales, radius=2., prior=5.):
    """Exclude direct meetings and weight each other distinct opponent once.

    Opponent style itself is described using its full legal season. Thus the
    response exclusion is NOT a claim that every input statistic is leave-pair-out.
    """
    group=group.loc[group.OpponentID.ne(target)].copy()
    if group.empty:return np.zeros(2),0.,0
    ids=group.OpponentID.to_numpy(dtype=int)
    distance=((style.loc[ids,columns].to_numpy()-style.loc[target,columns].to_numpy())/scales)**2
    distance=distance.sum(axis=1);w=np.exp(-.5*distance)*(distance<=radius**2)
    support=float(w.sum());count=int((w>0).sum())
    if support==0:return np.zeros(2),0.,0
    residual=group[['offense','defense']].to_numpy()
    centered=residual-residual.mean(axis=0)
    response=(w[:,None]*centered).sum(axis=0)/(support+prior)
    return response,support,count


def response_matrix(group, targets, style, columns, scales, radius=2., prior=5.):
    """Vectorized target-style responses with target-specific direct-game exclusions."""
    targets=np.asarray(targets,dtype=int)
    if group.empty:return np.zeros((len(targets),2)),np.zeros(len(targets)),np.zeros(len(targets),dtype=int)
    opponent=group.OpponentID.to_numpy(dtype=int)
    observed=style.loc[opponent,columns].to_numpy(dtype=float)
    targetstyle=style.loc[targets,columns].to_numpy(dtype=float)
    distance=(((observed[:,None,:]-targetstyle[None,:,:])/np.asarray(scales))**2).sum(axis=2)
    eligible=opponent[:,None]!=targets[None,:]
    weights=np.exp(-.5*distance)*(distance<=radius**2)*eligible
    values=group[['offense','defense']].to_numpy(dtype=float)
    counts=eligible.sum(axis=0)
    mean=np.einsum('nt,nk->tk',eligible.astype(float),values)/np.maximum(counts[:,None],1)
    residual=values[:,None,:]-mean[None,:,:]
    support=weights.sum(axis=0)
    result=(weights[:,:,None]*residual).sum(axis=0)/(support[:,None]+prior)
    return result,support,(weights>0).sum(axis=0)


def build_snapshot(base,pairs,long,rid):
    require(rid in FAMILIES,'Unknown round')
    require(set(cf.KEYS+BASE).issubset(pairs) and not pairs.duplicated(cf.KEYS).any(),'Invalid reference matrix')
    require((pairs.Team1ID<pairs.Team2ID).all() and pairs.Season.nunique()==1,'Require ordered one-season pairs')
    p=profiles(long);a=pairs.Team1ID.to_numpy(dtype=int);b=pairs.Team2ID.to_numpy(dtype=int)
    ids=sorted(set(a)|set(b));require(set(ids)<=set(p.index),'Missing seeded profile')
    require((p.loc[ids,'detailed_games']>=10).all(),'Fewer than ten detailed games for seeded team')
    out=pairs[cf.KEYS+BASE].copy();support=pairs[cf.KEYS].copy()
    diagnostic=[]
    if rid=='20':
        names=['pace_mean','pace_sd','three_share','shot_variance']
        for dest,name in zip(CONTROLS[rid],names):out[dest]=p.loc[a,name].to_numpy()-p.loc[b,name].to_numpy()
        z=context20(p,a,b,out.diff_strength.to_numpy(),out[cf.CONSENSUS].to_numpy())
        out[FEATURES[rid]]=z
        support['minimum_exposure']=np.minimum(p.loc[a,'detailed_games'].to_numpy(),p.loc[b,'detailed_games'].to_numpy())
        for family in FAMILIES[rid]:diagnostic.append({'family':family,'minimum_support':float(support.minimum_exposure.min()),'unit':'detailed games','rating_fits':0})
    else:
        require(not base.TeamID.duplicated().any(),'Duplicate base TeamID')
        lookup=base.set_index('TeamID')
        needed=set(long.TeamID)|set(long.OpponentID)
        require(needed<=set(lookup.index),'Missing cached opponent adjustment')
        require(np.isfinite(lookup.loc[sorted(needed),['adj_offense','adj_defense']].to_numpy()).all(),'Missing cached offense/defense effects')
        g=long.copy()
        g['offense']=g.eff+g.OpponentID.map(lookup.adj_defense)-3*g.home
        g['defense']=g.OpponentID.map(lookup.adj_offense)-g.allowed_eff-3*g.home
        grouped=g.groupby(['TeamID','OpponentID'],sort=True)[['offense','defense']].mean().reset_index()
        direct=grouped.groupby('TeamID')[['offense','defense']].mean()
        nonhome=g.loc[g.home.le(0)].groupby(['TeamID','OpponentID'])[['offense','defense']].mean().groupby('TeamID').agg(['sum','count'])
        p['neutral_offense']=direct.offense;p['neutral_defense']=direct.defense
        for k in ['offense','defense']:
            sums=nonhome[(k,'sum')].reindex(p.index,fill_value=0)
            n=nonhome[(k,'count')].reindex(p.index,fill_value=0)
            p['nonhome_'+k]=(sums-n*direct[k])/(n+5)
        raw_names=['neutral_offense','neutral_defense','nonhome_offense','nonhome_defense']
        for dest,name in zip(CONTROLS[rid],raw_names):out[dest]=p.loc[a,name].to_numpy()-p.loc[b,name].to_numpy()
        style_defs=[['pace_mean','three_share'],['forced_turnovers','offensive_rebounds']]
        all_results={};all_support={}
        for family,cols in zip(FAMILIES[rid],style_defs):
            scale=p[cols].std(ddof=0).to_numpy();require(np.isfinite(scale).all() and (scale>1e-12).all(),'Style dimension has no variation')
            response={};ss={}
            for team in ids:
                group=grouped.loc[grouped.TeamID.eq(team)]
                require(not group.empty,'No response games for seeded team')
                targets=[target for target in ids if target!=team]
                vv,nn,cc=response_matrix(group,targets,p,cols,scale)
                for target,v,n,c in zip(targets,vv,nn,cc):
                    response[(team,target)]=v;ss[(team,target)]=(float(n),int(c))
            all_results[family]=response;all_support[family]=ss
        for j,family in enumerate(FAMILIES[rid]):
            z=np.array([all_results[family][(x,y)]-all_results[family][(y,x)] for x,y in zip(a,b)])
            out[FEATURES[rid][2*j:2*j+2]]=z
            support['support_'+family]=[min(all_support[family][(x,y)][0],all_support[family][(y,x)][0]) for x,y in zip(a,b)]
            diagnostic.append({'family':family,'minimum_support':float(support['support_'+family].min()),
                'zero_support_pairs':int(support['support_'+family].eq(0).sum()),'unit':'weighted distinct opponents','rating_fits':0})
        support['minimum_exposure']=support[[c for c in support if c.startswith('support_')]].min(axis=1)
    for dup,control in zip(DUPLICATE,CONTROLS[rid]):out[dup]=out[control]
    require(np.isfinite(out[BASE+CONTROLS[rid]+FEATURES[rid]+DUPLICATE].to_numpy()).all(),'Nonfinite constructed feature')
    prof=base[[c for c in ['Gender','Season','TeamID','seed','strength','games'] if c in base]].merge(p.reset_index(),on='TeamID',how='left',validate='one_to_one')
    season=int(pairs.Season.iloc[0])
    coverage=pd.DataFrame([{'Season':season,'teams':len(ids),'potential_matchups':len(pairs),'candidates':4,
        'controls':4,'minimum_support':float(support.minimum_exposure.min()),'rating_fits':0,'tournament_labels_read':False}])
    for row in diagnostic:row['Season']=season;row['round']=rid
    return out,prof,coverage,support,pd.DataFrame(diagnostic)


def registry(rid):
    rows=[{'feature':f,'family':'consensus_reference','role':'reference','new_candidate':False} for f in BASE]
    for f in CONTROLS[rid]:rows.append({'feature':f,'family':'unconditional_controls','role':'control','new_candidate':False})
    for i,f in enumerate(FEATURES[rid]):rows.append({'feature':f,'family':FAMILIES[rid][i//2],'role':'candidate','new_candidate':True})
    for f in DUPLICATE:rows.append({'feature':f,'family':'duplication_diagnostic','role':'diagnostic','new_candidate':False})
    d=pd.DataFrame(rows);d['cutoff_day']=132;d['swap_parity']=-1
    d['availability']='pre-cutoff regular-season box scores and previously verified consensus reference'
    d['evidence']='prepared hypothesis, no results until user execution'
    return d
