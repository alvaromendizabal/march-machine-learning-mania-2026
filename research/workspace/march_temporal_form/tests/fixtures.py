"""Synthetic basketball and filesystem fixtures. Never loaded by real-data commands."""
from pathlib import Path
import itertools,subprocess,shutil,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import form_workflow as w


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
    root=Path(root);kit=root/'march_temporal_form';repo=root/'repo';shooting=root/'march_shooting_research';record=root/'march_record_validation'
    for p in [kit,repo,shooting,record]:p.mkdir(parents=True)
    for n in ['form_features.py','form_workflow.py','form_plots.py','run_round06.py','06_temporal_form_features.ipynb']:
        shutil.copy2(ROOT/n,kit/n)
    shutil.copytree(ROOT/'frozen',kit/'frozen',ignore=shutil.ignore_patterns('__pycache__'))
    raw=repo/'data/kaggle/raw';raw.mkdir(parents=True)
    for g in ['M','W']:
        for name,f in zip(['RegularSeasonCompactResults','RegularSeasonDetailedResults','NCAATourneySeeds','NCAATourneyCompactResults'],data(gender=g)):
            f.to_csv(raw/(g+name+'.csv'),index=False)
    (repo/'notebooks').mkdir()
    for n in w.wf.ALLOWED_DIRTY:(repo/n).write_text('{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}')
    (repo/'src').mkdir();(repo/'src/constant.py').write_text('VALUE = 1\n');(repo/'.gitignore').write_text('data/\n')
    def git(*a):return subprocess.check_output(['git','-C',str(repo),*a],stderr=subprocess.DEVNULL).decode().strip()
    git('init','-b','main');git('config','user.name','Synthetic Test');git('config','user.email','test@example.invalid');git('add','.');git('commit','-m','synthetic fixture')
    head=git('rev-parse','HEAD');git('update-ref','refs/remotes/origin/main',head)
    for n in w.wf.ALLOWED_DIRTY:(repo/n).write_text((repo/n).read_text()+'\n')
    ancestor=shooting/'private_runs'/('a'*64);previous=record/'private_runs'/('c'*64)
    ancestor.mkdir(parents=True);previous.mkdir(parents=True)
    upstream={};evidence=kit/'evidence';evidence.mkdir()
    baseline_rows=[]
    for g in ['M','W']:
        compact,detail,seeds,targets=data(gender=g);bases=[]
        for s in range(2013,2020):
            base,audit=w.sf.build_snapshot(compact,detail,seeds,g,s);bases.append(base)
            f=ancestor/f'snapshots/{g}_{s}'
            w.atomic_csv(f/'teams.csv',base);w.atomic_csv(f/'opponent_exclusion_audit.csv',audit)
            w.atomic_json(f/'coverage.json',{'Gender':g,'Season':s,'synthetic':True});w.seal(f,['teams.csv','opponent_exclusion_audit.csv','coverage.json'])
            for n in ['teams.csv','opponent_exclusion_audit.csv','coverage.json','complete.json']:upstream[f'snapshots/{g}_{s}/'+n]=w.sha(f/n)
        bases=pd.concat(bases,ignore_index=True);pairs,y=w.sf.tournament_pairs(targets,g,list(range(2013,2020)));x=w.sf.pair_features(bases,pairs)
        for s in ([2017,2019] if g=='W' else [2019]):
            ti,vi=w.split(x,s);model=w.wf.fitted_model(x.iloc[ti],y[ti],w.ANCHOR);model['train_seasons']=list(range(2013,s))
            prob=w.wf.predict(model,x.iloc[vi]);f=(previous if s==2017 else ancestor)/f'fits/{g}_{s}_anchor'
            pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=prob;pred['squared_error']=(prob-y[vi])**2
            metric={'Gender':g,'Season':s,'recipe':'anchor','brier':float(np.mean((prob-y[vi])**2))}
            w.atomic_json(f/'model.json',model);w.atomic_json(f/'metrics.json',metric);w.atomic_csv(f/'predictions.csv',pred);w.seal(f,['model.json','metrics.json','predictions.csv'])
            baseline_rows.append(metric)
            if s==2019:
                for n in ['model.json','metrics.json','predictions.csv','complete.json']:upstream[f'fits/{g}_{s}_anchor/'+n]=w.sha(f/n)
    rows=[]
    for s,d in zip([2016,2017,2018,2019],[.000175229,-.00079667,-.001411386,.001337704]):
        anchor=next((r['brier'] for r in baseline_rows if r['Gender']=='W' and r['Season']==s),.15)
        for recipe,delta in [('anchor',0.),('anchor_record',d)]:
            rows.append({'Gender':'W','Season':s,'recipe':recipe,'brier':anchor+delta,'anchor_brier':anchor,'delta_vs_anchor':delta,'role':'synthetic prior fixture'})
    w.atomic_csv(previous/'replication_metrics.csv',pd.DataFrame(rows))
    from unittest.mock import patch
    with patch.object(w.wf,'EXPECTED_SHA',head):state=w.wf.repository_state(repo)
    w.atomic_json(previous/'preflight.json',{'state':state})
    w.atomic_json(previous/'summary.json',{'status':'COMPLETE','synthetic':True})
    w.atomic_json(previous/'gate.json',{'decision':'STOP_EXPANSION','synthetic':True})
    w.atomic_json(previous/'replication_receipt.json',{'new_classifier_fits':5,'synthetic':True})
    w.atomic_json(previous/'ablation_receipt.json',{'status':'SKIPPED_BY_GATE'})
    m04={'fingerprint':'b'*64,'upstream_fingerprint':'a'*64,'upstream_files':upstream}
    m05={'fingerprint':'c'*64,'prior_fingerprint':'b'*64,'upstream_fingerprint':'a'*64,'config':{'recipes':{'anchor':w.ANCHOR}},
         'source':{f'frozen/{n}':w.sha(kit/'frozen'/n) for n in ['research_workflow.py','shot_features.py']},
         'environment':w.environment(),'data':{p.name:w.sha(p) for p in raw.glob('*.csv')},'reference_commit':head}
    w.atomic_json(previous/'manifest.json',m05)
    for p in previous.glob('*'):
        if p.is_file():shutil.copy2(p,evidence/p.name)
    w.atomic_json(evidence/'upstream04_manifest.json',m04)
    return {'kit':kit,'repo':repo,'shooting':shooting,'record':record,'head':head}
