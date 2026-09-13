from __future__ import annotations
import itertools, json, shutil, subprocess
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
import possession_workflow as w
ROOT=Path(__file__).resolve().parents[1]
def data(seasons=range(2013,2020),gender='M'):
    rng=np.random.default_rng(912);ids=np.arange(1101,1113) if gender=='M' else np.arange(3101,3113)
    records=[];seedrows=[];targets=[]
    for season in seasons:
        for i,t in enumerate(ids):seedrows.append({'Season':season,'TeamID':int(t),'Seed':f'W{i+1:02d}'})
        # Two separate rounds spread throughout the season, each with 12 teams.
        # Shuffling opponents prevents an artificial team-id/time association.
        pairs=list(itertools.combinations(ids,2));rng.shuffle(pairs)
        allpairs=pairs+list(reversed(pairs))
        for j,(a,b) in enumerate(allpairs):
            values=[]
            for t in (a,b):
                q=(6-(int(t)%100-1))/40
                a3=int(rng.integers(18,27));m3=int(rng.binomial(a3,np.clip(.34+q/3,.1,.6)))
                m2=int(rng.binomial(60-a3,np.clip(.49+q/2,.2,.7)));ft=int(rng.binomial(18,.72))
                values.append(dict(TeamID=int(t),FGM=m2+m3,FGA=60,FGM3=m3,FGA3=a3,FTM=ft,FTA=18,OR=10,DR=27,TO=12,Score=2*m2+3*m3+ft))
            if values[0]['Score']==values[1]['Score']:values[0]['Score']+=1;values[0]['FTM']+=1
            values.sort(key=lambda x:x['Score'],reverse=True)
            day=20+j*112//len(allpairs)
            row={'Season':season,'DayNum':day,'WLoc':['H','A','N'][j%3],'NumOT':0}
            for side,v in zip(('W','L'),values):row.update({side+k:v for k,v in v.items()})
            records.append(row)
        for j in range(7):
            a,b=int(ids[j]),int(ids[(j+4)%12]);winner,loser=(a,b) if (j+season)%3 else (b,a)
            targets.append({'Season':season,'DayNum':136+j,'WTeamID':winner,'LTeamID':loser,'WScore':75,'LScore':64,'WLoc':'N','NumOT':0})
    detailed=pd.DataFrame(records)
    compact=detailed[['Season','DayNum','WTeamID','LTeamID','WScore','LScore','WLoc','NumOT']].copy()
    return compact,detailed,pd.DataFrame(seedrows),pd.DataFrame(targets)



def build_fixture(root):
    root=Path(root);args={'kit':root/'march_possession_research','repo':root/'repo'}
    for k,name in [('shooting','march_shooting_research'),('schedule','march_schedule_research'),('record','march_record_validation'),('temporal','march_temporal_form')]:args[k]=root/name
    for p in args.values():p.mkdir(parents=True)
    kit=args['kit'];repo=args['repo']
    for n in w.SOURCES+['08_possession_matchup_features.ipynb']:
        p=kit/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/n,p)
    raw=repo/'data/kaggle/raw';raw.mkdir(parents=True)
    for g in ['M','W']:
        for n,df in zip(['RegularSeasonCompactResults','RegularSeasonDetailedResults','NCAATourneySeeds','NCAATourneyCompactResults'],data(gender=g)):
            w.atomic_csv(raw/(g+n+'.csv'),df)
    (repo/'notebooks').mkdir();(repo/'src').mkdir()
    for n in w.rf.ALLOWED_DIRTY:(repo/n).write_text('{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}')
    (repo/'src/constant.py').write_text('VALUE = 1\n');(repo/'.gitignore').write_text('data/\n')
    def git(*a):return subprocess.check_output(['git','-C',str(repo),*a],stderr=subprocess.DEVNULL).decode().strip()
    git('init','-b','main');git('config','user.name','Synthetic Test');git('config','user.email','test@example.invalid')
    git('add','.');git('commit','-m','synthetic fixture');head=git('rev-parse','HEAD');git('update-ref','refs/remotes/origin/main',head)
    for n in w.rf.ALLOWED_DIRTY:(repo/n).write_text((repo/n).read_text()+'\n')
    p=kit/'frozen/research_workflow.py';p.write_text(p.read_text().replace(w.rf.EXPECTED_SHA,head))
    with patch.object(w.rf,'EXPECTED_SHA',head):state=w.rf.repository_state(repo)
    fp={k:c*64 for k,c in [('shooting','a'),('schedule','b'),('record','c'),('temporal','d')]}
    roots={k:args[k]/'private_runs'/h for k,h in fp.items()};pins={};scores=[]
    for k,p in roots.items():p.mkdir(parents=True);w.atomic_json(p/'manifest.json',{'fingerprint':fp[k],'synthetic':True})
    for g in ['M','W']:
        compact,detail,seeds,target=data(gender=g);bases=[]
        for s in range(2013,2020):
            base,audit=w.sf.build_snapshot(compact,detail,seeds,g,s);bases.append(base)
            folder=roots['shooting']/f'snapshots/{g}_{s}'
            w.atomic_csv(folder/'teams.csv',base);w.atomic_csv(folder/'opponent_exclusion_audit.csv',audit);w.atomic_json(folder/'coverage.json',{'synthetic':True})
            w.seal(folder,['teams.csv','coverage.json','opponent_exclusion_audit.csv'])
            for p in folder.iterdir():pins['shooting/'+str(p.relative_to(roots['shooting']))]=w.sha(p)
        base=pd.concat(bases,ignore_index=True);pairs,y=w.sf.tournament_pairs(target,g,list(range(2013,2020)));x=w.sf.pair_features(base,pairs)
        for s in w.SEASONS:
            ti,vi=w.rf.split_indices(x,s);m=w.rf.fitted_model(x.iloc[ti],y[ti],w.pf.BASE);m['train_seasons']=list(range(2013,s))
            p=w.rf.predict(m,x.iloc[vi]);row={'Gender':g,'Season':s,'recipe':'anchor','brier':float(np.mean((p-y[vi])**2)),
              'log_loss':float(-np.mean(y[vi]*np.log(p)+(1-y[vi])*np.log1p(-p))),'games':len(vi)}
            scores.append(row)
            if (g,s) not in w.ORIGINS:continue
            key,rel=w.ORIGINS[(g,s)];folder=roots[key]/rel
            pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=p;pred['squared_error']=(p-y[vi])**2
            w.atomic_json(folder/'model.json',m);w.atomic_json(folder/'metrics.json',row);w.atomic_csv(folder/'predictions.csv',pred);w.seal(folder,w.FIT_FILES)
            for p in folder.iterdir():pins[key+'/'+str(p.relative_to(roots[key]))]=w.sha(p)
    frame=pd.DataFrame(scores)
    for number,k in [('04','schedule'),('05','record'),('06','temporal'),('07',None)]:
        dest=kit/'evidence'/('round'+number);dest.mkdir(parents=True)
        if k is not None:shutil.copy2(roots[k]/'manifest.json',dest/'manifest.json')
        out=frame.copy()
        if number=='07':
            out=frame[frame.Gender=='W'].copy();extra=out.copy();extra['recipe']='anchor_change';extra['brier']+=.001
            out=pd.concat([out,extra],ignore_index=True);out['delta_vs_anchor']=np.where(out.recipe=='anchor',0.,.001)
            out['role']=np.where(out.Season.isin([2017,2019]),'discovery / selection','additional exploratory replication')
        w.atomic_csv(dest/('metrics.csv' if number in ['04','06'] else 'replication_metrics.csv'),out)
    constraints={'reference_commit':head,'environment':w.environment(),'data':{p.name:w.sha(p) for p in raw.glob('*.csv')},
       'fingerprints':fp,'upstream_pins':pins,'state':state,'frozen_sources':{n:w.sha(kit/n) for n in ['frozen/research_workflow.py','frozen/shot_features.py']}}
    w.atomic_json(kit/'constraints.json',constraints)
    w.atomic_json(kit/'MANIFEST.json',{'sha256':{str(p.relative_to(kit)):w.sha(p) for p in kit.rglob('*') if p.is_file() and p.name!='MANIFEST.json'}})
    return args,head
