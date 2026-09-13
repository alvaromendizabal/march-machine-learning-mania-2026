"""Synthetic 64-team fields; cached ratings are artificial inputs, not real data."""
from __future__ import annotations
import json, shutil, subprocess
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
import bracket_workflow as w
ROOT=Path(__file__).resolve().parents[1]


def toy_data():
    rng=np.random.default_rng(20260912);seeds=[];bases=[];targets=[]
    ids=np.arange(3101,3165)
    for year in w.YEARS:
        order=rng.permutation(ids)
        seedmap={int(t):f'{"WXYZ"[i//16]}{i%16+1:02d}' for i,t in enumerate(order)}
        rows=[]
        for t in ids:
            rank=int(seedmap[int(t)][1:]);seeds.append({'Season':year,'TeamID':int(t),'Seed':seedmap[int(t)]})
            row={'Gender':'W','Season':year,'TeamID':int(t),'seed':float(rank),'games':30.,'detailed_coverage':1.,'detailed_games':30.,'clean_games':28.}
            for f in w.sf.CONTROL+w.sf.RESIDUAL+w.sf.PROFILE:
                if f not in row:row[f]=float(rng.normal(0,1))
            row.update(strength=float(10-rank+rng.normal()),schedule_strength=float(rng.normal()),margin=float(10-rank+rng.normal()),margin_sd=float(8+rng.uniform(0,6)),win_rate=float(.85-rank*.03))
            for side in ['','opp_']:
                for shot,rate in [('two',.5),('three',.35),('free',.75)]:row[side+shot+'_posterior']=rate+rng.normal(0,.015)
                row[side+'three_share']=.35+rng.normal(0,.04)
            for rate,value in [('two',.5),('three',.35),('share',.35)]:
                row['profile_'+rate+'_league']=value;row['profile_'+rate+'_offense']=float(rng.normal(0,.01));row['profile_'+rate+'_allowance']=float(rng.normal(0,.01))
            rows.append(row)
        base=pd.DataFrame(rows);bases.append(base)
        # Full artificial knockout draw, seeded positions fixed before choosing winners.
        positions=[1,16,8,9,5,12,4,13,6,11,3,14,7,10,2,15]
        teams=[int(t) for region in 'WXYZ' for n in positions for t,s in seedmap.items() if s==f'{region}{n:02d}']
        round_=0
        while len(teams)>1:
            nxt=[]
            for i in range(0,len(teams),2):
                a,b=teams[i:i+2];sa=int(seedmap[a][1:]);sb=int(seedmap[b][1:]);prob=1/(1+np.exp((sa-sb)/4))
                win,lose=(a,b) if rng.random()<prob else (b,a)
                targets.append({'Season':year,'DayNum':136+round_*3,'WTeamID':win,'LTeamID':lose,'WScore':80,'LScore':70,'WLoc':'N'})
                nxt.append(win)
            teams=nxt;round_+=1
    return pd.DataFrame(seeds),bases,pd.DataFrame(targets)


def manifest(kit):
    w.atomic_json(kit/'MANIFEST.json',{'sha256':{str(p.relative_to(kit)):w.sha(p) for p in kit.rglob('*') if p.is_file() and p.name!='MANIFEST.json' and '__pycache__' not in p.parts and 'private_runs' not in p.parts and 'reports' not in p.parts}})


def build_fixture(root):
    root=Path(root);args={k:root/n for k,n in [('kit','march_bracket_context'),('repo','repo'),('shooting','march_shooting_research'),('schedule','march_schedule_research'),('record','march_record_validation')]}
    for p in args.values():p.mkdir(parents=True)
    kit=args['kit'];repo=args['repo']
    for n in w.SOURCES+['09_womens_bracket_context.ipynb']:
        p=kit/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/n,p)
    shutil.copytree(ROOT/'evidence',kit/'evidence')
    raw=repo/'data/kaggle/raw';raw.mkdir(parents=True)
    seeds,bases,target=toy_data();w.atomic_csv(raw/'WNCAATourneySeeds.csv',seeds);w.atomic_csv(raw/'WNCAATourneyCompactResults.csv',target)
    (repo/'notebooks').mkdir();(repo/'src').mkdir();(repo/'src/value.py').write_text('VALUE = 1\n');(repo/'.gitignore').write_text('data/\n')
    for n in w.rf.ALLOWED_DIRTY:(repo/n).write_text('{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}\n')
    def git(*a):return subprocess.check_output(['git','-C',str(repo),*a],stderr=subprocess.DEVNULL).decode().strip()
    git('init','-b','main');git('config','user.name','Synthetic Test');git('config','user.email','test@example.invalid');git('add','.');git('commit','-m','synthetic test fixture');head=git('rev-parse','HEAD');git('update-ref','refs/remotes/origin/main',head)
    for n in w.rf.ALLOWED_DIRTY:(repo/n).write_text((repo/n).read_text()+'\n')
    p=kit/'frozen/research_workflow.py';p.write_text(p.read_text().replace(w.rf.EXPECTED_SHA,head))
    with patch.object(w.rf,'EXPECTED_SHA',head):state=w.rf.repository_state(repo)
    fps={k:char*64 for k,char in [('shooting','a'),('schedule','b'),('record','c')]};roots={k:args[k]/'private_runs'/v for k,v in fps.items()};pins={}
    for k,p in roots.items():p.mkdir(parents=True);w.atomic_json(p/'manifest.json',{'fingerprint':fps[k],'synthetic':True})
    for year,base in zip(w.YEARS,bases):
        p=roots['shooting']/f'snapshots/W_{year}'
        w.atomic_csv(p/'teams.csv',base);w.atomic_json(p/'coverage.json',{'synthetic':True});w.atomic_csv(p/'opponent_exclusion_audit.csv',pd.DataFrame({'synthetic':[True]}))
        w.seal(p,['teams.csv','coverage.json','opponent_exclusion_audit.csv'])
    base=pd.concat(bases,ignore_index=True);pairs,y=w.sf.tournament_pairs(target,'W',w.YEARS);x=w.sf.pair_features(base,pairs);scores=[]
    for s in w.SEASONS:
        ti,vi=w.rf.split_indices(x,s);m=w.rf.fitted_model(x.iloc[ti],y[ti],w.bf.BASE);m['train_seasons']=list(range(2013,s));p=w.rf.predict(m,x.iloc[vi]);brier=float(np.mean((p-y[vi])**2))
        root_,rel=w.ORIGINS[s];folder=roots[root_]/rel
        pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=p
        # Intentionally missing log_loss and squared_error, mirroring older schema variations.
        metric={'Gender':'W','Season':s,'brier':brier,'games':len(vi)}
        w.atomic_json(folder/'model.json',m);w.atomic_json(folder/'metrics.json',metric);w.atomic_csv(folder/'predictions.csv',pred);w.seal(folder,w.FIT_FILES)
        scores.append(dict(metric,recipe='anchor'))
    w.atomic_csv(kit/'evidence/round08/metrics.csv',pd.DataFrame(scores))
    for k,p in roots.items():
        for f in p.rglob('*'):
            if f.is_file():pins[k+'/'+str(f.relative_to(p))]=w.sha(f)
    constraints={'reference_commit':head,'state':state,'data':{p.name:w.sha(p) for p in raw.glob('*.csv')},'environment':w.environment(),'fingerprints':fps,'upstream_pins':pins,'frozen_sources':{n:w.sha(kit/n) for n in ['frozen/research_workflow.py','frozen/shot_features.py']}}
    w.atomic_json(kit/'constraints.json',constraints);manifest(kit)
    return args,head
