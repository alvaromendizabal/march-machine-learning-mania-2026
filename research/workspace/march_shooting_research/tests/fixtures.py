"""Small synthetic basketball fixtures. Never evidence about real predictive quality."""
from pathlib import Path
import itertools
import json
import shutil
import subprocess
import numpy as np
import pandas as pd


def data(seasons=range(2013,2022),gender='M'):
    rng=np.random.default_rng(204)
    ids=np.arange(1101,1113) if gender=='M' else np.arange(3101,3113)
    records=[];seedrows=[];targets=[]
    for season in seasons:
        if season==2020:continue
        for i,tid in enumerate(ids):seedrows.append({'Season':season,'TeamID':tid,'Seed':f'W{i+1:02d}'})
        pairs=list(itertools.combinations(ids,2))*2
        for j,(a,b) in enumerate(pairs):
            sides=[]
            for t in (a,b):
                quality=(6-(int(t)%100-1))/40.
                a3=int(rng.integers(17,28));m3=int(rng.binomial(a3,np.clip(.33+quality/3,.1,.6)))
                m2=int(rng.binomial(60-a3,np.clip(.49+quality/2,.2,.7)))
                ft=int(rng.binomial(18,.72))
                sides.append(dict(TeamID=int(t),FGM=m2+m3,FGA=60,FGM3=m3,FGA3=a3,FTM=ft,
                                  FTA=18,OR=10,DR=27,TO=12,Score=2*m2+3*m3+ft))
            if sides[0]['Score']==sides[1]['Score']:
                sides[0]['FTM']+=1;sides[0]['Score']+=1
            sides=sorted(sides,key=lambda x:x['Score'],reverse=True)
            row={'Season':season,'DayNum':20+j//2,'WLoc':['H','A','N'][j%3],'NumOT':0}
            for letter,s in zip(('W','L'),sides):
                row.update({letter+k:v for k,v in s.items()})
            records.append(row)
        for k in range(7):
            a,b=int(ids[k]),int(ids[(k+4)%12])
            # Non-degenerate synthetic tournament labels, unrelated to the experiment objective.
            winner,loser=(a,b) if (season+k)%3 else (b,a)
            targets.append({'Season':season,'DayNum':136+k,'WTeamID':winner,'LTeamID':loser,
                            'WScore':75,'LScore':64,'WLoc':'N','NumOT':0})
    detail=pd.DataFrame(records)
    compact=detail[['Season','DayNum','WTeamID','LTeamID','WScore','LScore','WLoc','NumOT']].copy()
    return compact,detail,pd.DataFrame(seedrows),pd.DataFrame(targets)


def write_fixture(repo:Path,kit:Path):
    raw=repo/'data/kaggle/raw';raw.mkdir(parents=True)
    names=['RegularSeasonCompactResults','RegularSeasonDetailedResults','NCAATourneySeeds','NCAATourneyCompactResults']
    for g in ('M','W'):
        for name,frame in zip(names,data(gender=g)):
            frame.to_csv(raw/(g+name+'.csv'),index=False)
    (repo/'notebooks').mkdir()
    for name in ('00_data_audit_and_preparation.ipynb','01_split_protocol_and_pre_tournament_snapshots.ipynb'):
        (repo/'notebooks'/name).write_text('{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}')
    (repo/'.gitignore').write_text('data/\n')
    def git(*args):
        return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL).decode().strip()
    git('init','-b','main');git('config','user.email','fixture@example.invalid');git('config','user.name','Synthetic Fixture')
    git('add','.');git('commit','-m','synthetic fixture')
    head=git('rev-parse','HEAD');git('update-ref','refs/remotes/origin/main',head)
    for name in ('00_data_audit_and_preparation.ipynb','01_split_protocol_and_pre_tournament_snapshots.ipynb'):
        p=repo/'notebooks'/name;p.write_text(p.read_text()+'\n')
    import hashlib
    expected={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.glob('*.csv')}
    (kit/'expected_inputs.json').write_text(json.dumps(expected))
    return head
