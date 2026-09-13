"""Synthetic-only source/cache fixtures. Never imported by execution commands."""
from pathlib import Path
import itertools, shutil, subprocess, sys
import numpy as np
import pandas as pd
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import validation_workflow as w

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
    root=Path(root)
    kit=root/'march_temporal_validation';repo=root/'repo'
    temporal=root/'march_temporal_form';shooting=root/'march_shooting_research'
    record=root/'march_record_validation';schedule=root/'march_schedule_research'
    for p in [kit,repo,temporal,shooting,record,schedule]:p.mkdir(parents=True)
    for n in w.SOURCES+['07_womens_temporal_change_replication.ipynb']:
        (kit/n).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/n,kit/n)
    raw=repo/'data/kaggle/raw';raw.mkdir(parents=True)
    for g in ['M','W']:
        for name,frame in zip(['RegularSeasonCompactResults','RegularSeasonDetailedResults','NCAATourneySeeds','NCAATourneyCompactResults'],data(gender=g)):
            frame.to_csv(raw/(g+name+'.csv'),index=False)
    (repo/'notebooks').mkdir();(repo/'src').mkdir()
    for n in w.wf.ALLOWED_DIRTY:(repo/n).write_text('{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}')
    (repo/'src/constant.py').write_text('VALUE = 1\n');(repo/'.gitignore').write_text('data/\n')
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL).decode().strip()
    git('init','-b','main');git('config','user.name','Synthetic Test');git('config','user.email','test@example.invalid')
    git('add','.');git('commit','-m','synthetic fixture');head=git('rev-parse','HEAD')
    git('update-ref','refs/remotes/origin/main',head)
    for n in w.wf.ALLOWED_DIRTY:(repo/n).write_text((repo/n).read_text()+'\n')
    # Only the synthetic copy's pinned reference is changed so child processes can use it.
    path=kit/'frozen/research_workflow.py'
    path.write_text(path.read_text().replace(w.wf.EXPECTED_SHA,head))
    with patch.object(w.wf,'EXPECTED_SHA',head):state=w.wf.repository_state(repo)
    roots={'temporal':temporal/'private_runs'/('e'*64),'shooting':shooting/'private_runs'/('a'*64),
           'record':record/'private_runs'/('c'*64),'schedule':schedule/'private_runs'/('b'*64)}
    for p in roots.values():p.mkdir(parents=True)
    compact,detail,seeds,target=data(gender='W');coverage=[];upstream06={};upstream05={}
    for s in range(2013,2020):
        base,audit=w.sf.build_snapshot(compact,detail,seeds,'W',s)
        folder=roots['shooting']/f'snapshots/W_{s}'
        w.atomic_csv(folder/'teams.csv',base);w.atomic_csv(folder/'opponent_exclusion_audit.csv',audit)
        w.atomic_json(folder/'coverage.json',{'Season':s,'synthetic':True})
        w.seal(folder,['teams.csv','coverage.json','opponent_exclusion_audit.csv'])
        for n in ['teams.csv','coverage.json','opponent_exclusion_audit.csv','complete.json']:
            upstream06[f'shooting/snapshots/W_{s}/'+n]=w.sha(folder/n)
        early=w.ff.fit_early(detail,s);ef=roots['temporal']/f'early_ratings/W_{s}'
        w.atomic_json(ef/'model.json',early);w.seal(ef,['model.json'])
        features,late=w.ff.build_snapshot(detail,base,'W',s,early)
        f=roots['temporal']/f'snapshots/W_{s}'
        w.atomic_csv(f/'features.csv',features);w.atomic_csv(f/'late_residuals.csv',late)
        cover={'Gender':'W','Season':s,'teams':len(features),'early_physical_games':early['early_physical_games'],
               'late_physical_games':len(late)//2,'early_model_sha256':w.sha(ef/'model.json')}
        w.atomic_json(f/'coverage.json',cover);w.seal(f,['features.csv','coverage.json','late_residuals.csv']);coverage.append(cover)
    context={'temporal':roots['temporal'],'shooting':roots['shooting'],'raw':raw}
    bundle=w.matrices(context);pairs,y,x,_=bundle
    origins={(2016,'anchor'):'record',(2017,'anchor'):'record',(2017,'anchor_change'):'temporal',
             (2018,'anchor'):'schedule',(2019,'anchor'):'shooting',(2019,'anchor_change'):'temporal'}
    rows06=[];rows05=[]
    for (s,recipe),prefix in origins.items():
        ti,vi=w.ref.split(x,s);model=w.wf.fitted_model(x.iloc[ti],y[ti],w.RECIPES[recipe]);model['train_seasons']=list(range(2013,s))
        prob=w.wf.predict(model,x.iloc[vi]);pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=prob;pred['squared_error']=(prob-y[vi])**2
        row={'Gender':'W','Season':s,'recipe':recipe,'brier':float(np.mean((prob-y[vi])**2)),
             'log_loss':float(-np.mean(y[vi]*np.log(prob)+(1-y[vi])*np.log1p(-prob))),'games':len(vi)}
        f=roots[prefix]/f'fits/W_{s}_{recipe}'
        w.atomic_json(f/'model.json',model);w.atomic_json(f/'metrics.json',row);w.atomic_csv(f/'predictions.csv',pred);w.seal(f,w.FIT_FILES)
        for n in w.FIT_FILES+['complete.json']:
            key=f'{prefix}/fits/W_{s}_{recipe}/'+n
            (upstream05 if prefix=='schedule' else upstream06)[key]=w.sha(f/n)
        if s in w.DISCOVERY:rows06.append(row)
        if recipe=='anchor':rows05.append(row)
    df=pd.DataFrame(rows06);ctrl=df.query("recipe=='anchor'")[['Season','brier']].rename(columns={'brier':'anchor_brier'})
    df=df.merge(ctrl,on='Season');df['delta_vs_anchor']=df.brier-df.anchor_brier
    w.atomic_csv(roots['temporal']/'metrics.csv',df)
    w.atomic_csv(roots['temporal']/'coverage.csv',pd.DataFrame(coverage));w.atomic_csv(roots['temporal']/'feature_registry.csv',w.ff.registry(w.ANCHOR))
    for n in ['summary.json','decisions.json','prepare.json','evaluation_receipt.json']:
        w.atomic_json(roots['temporal']/n,{'synthetic':True,'status':'COMPLETE'})
    w.atomic_json(roots['temporal']/'preflight.json',{'state':state})
    m05={'fingerprint':'c'*64,'upstream_fingerprint':'a'*64,'prior_fingerprint':'b'*64,'upstream_files':upstream05}
    w.atomic_json(roots['record']/'manifest.json',m05)
    w.atomic_json(roots['record']/'preflight.json',{'state':state})
    w.atomic_csv(roots['record']/'replication_metrics.csv',pd.DataFrame(rows05))
    m06={'fingerprint':'e'*64,'prior_fingerprint':'c'*64,'upstream_fingerprint':'a'*64,
         'source':{old:w.sha(kit/new) for new,old in [('reference_form_workflow.py','form_workflow.py'),('form_features.py','form_features.py'),
              ('frozen/research_workflow.py','frozen/research_workflow.py'),('frozen/shot_features.py','frozen/shot_features.py')]},
         'environment':w.ref.environment(),'data':{p.name:w.sha(p) for p in raw.glob('*.csv')},
         'config':{'recipes':w.ref.RECIPES,'parameters':w.ff.PARAMETERS,'C':.1,'max_iter':2000,'threads':2,'seed':20260911},
         'upstream_files':upstream06,'evidence_sha256':{'manifest.json':w.sha(roots['record']/'manifest.json')},'reference_commit':head}
    w.atomic_json(roots['temporal']/'manifest.json',m06)
    for prefix,dest in [('temporal','evidence'),('record','evidence05')]:
        (kit/dest).mkdir()
        for p in roots[prefix].iterdir():
            if p.is_file():shutil.copy2(p,kit/dest/p.name)
    return dict(kit=kit,repo=repo,temporal=temporal,shooting=shooting,record=record,schedule=schedule,head=head)
