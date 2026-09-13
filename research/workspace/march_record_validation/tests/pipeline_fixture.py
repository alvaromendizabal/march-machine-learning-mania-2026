"""Synthetic-only fixture builder; never used by production preflight."""
from pathlib import Path
import shutil
from unittest.mock import patch
import pandas as pd
import numpy as np
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import record_workflow as r
from fixtures import data,write_fixture


def build_fixture(root):
    root=Path(root);kit=root/'kit';kit.mkdir();repo=root/'repo';repo.mkdir()
    shooting=root/'march_shooting_research';shooting.mkdir()
    schedule=root/'march_schedule_research';schedule.mkdir()
    for n in ['record_workflow.py','record_plots.py','run_round05.py']:
        shutil.copy2(ROOT/n,kit/n)
    shutil.copytree(ROOT/'frozen',kit/'frozen',ignore=shutil.ignore_patterns('__pycache__'))
    for p in ROOT.glob('*.ipynb'):shutil.copy2(p,kit/p.name)
    head=write_fixture(repo,shooting)
    ancestor=shooting/'private_runs'/('a'*64);ancestor.mkdir(parents=True)
    old=schedule/'private_runs'/('b'*64);old.mkdir(parents=True)
    base_frames=[];schedule_frames=[]
    compact,detail,seeds,targets=data(seasons=range(2013,2020),gender='W')
    upstream={}
    for s in range(2013,2020):
        b,a=r.rf.build_snapshot(compact,detail,seeds,'W',s)
        base_frames.append(b)
        f=ancestor/f'snapshots/W_{s}'
        r.atomic_csv(f/'teams.csv',b);r.atomic_csv(f/'opponent_exclusion_audit.csv',a)
        r.atomic_json(f/'coverage.json',{'gender':'W','season':s,'synthetic':True})
        r.seal(f,['teams.csv','opponent_exclusion_audit.csv','coverage.json'])
        for n in ['teams.csv','opponent_exclusion_audit.csv','coverage.json','complete.json']:
            upstream[f'snapshots/W_{s}/'+n]=r.sha(f/n)
        sf,sg=r.sf.build_schedule_snapshot(compact,b,'W',s)
        if s<2019:
            schedule_frames.append(sf)
            f=old/f'snapshots/W_{s}'
            r.atomic_csv(f/'features.csv',sf);r.atomic_json(f/'audit.json',{'season':s,'synthetic':True})
            r.seal(f,['features.csv','audit.json'])
    base=pd.concat(base_frames,ignore_index=True)
    pairs,y=r.rf.tournament_pairs(targets,'W',list(range(2013,2020)))
    x=r.rf.pair_features(base,pairs)
    # Only the two prior 2018 recipes need schedule features; no 2019 record fit is fabricated.
    p18=pairs.loc[pairs.Season<=2018].copy()
    extra=r.sf.matchup_features(pd.concat(schedule_frames,ignore_index=True),p18)
    x.loc[x.Season<=2018,r.RECORD]=extra[r.RECORD].to_numpy()
    rows=[]
    for s,recipe,folder in [(2018,'anchor',old),(2018,'anchor_record',old),(2019,'anchor',ancestor)]:
        ti,vi=r.temporal_split(x,s);cols=r.BASE_RECIPES[recipe]
        model=r.wf.fitted_model(x.iloc[ti],y[ti],cols);model['train_seasons']=list(range(2013,s))
        p=r.wf.predict(model,x.iloc[vi]);f=folder/f'fits/W_{s}_{recipe}'
        metric={'Gender':'W','Season':s,'recipe':recipe,'brier':float(np.mean((p-y[vi])**2)),
                'games':len(vi),'train_games':len(ti)}
        pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=p;pred['squared_error']=(p-y[vi])**2
        r.atomic_json(f/'model.json',model);r.atomic_json(f/'metrics.json',metric);r.atomic_csv(f/'predictions.csv',pred)
        r.seal(f,['model.json','metrics.json','predictions.csv'])
        if s==2018:rows.append(metric)
        else:
            for n in ['model.json','metrics.json','predictions.csv','complete.json']:
                upstream[f'fits/W_2019_anchor/'+n]=r.sha(f/n)
    evidence=kit/'evidence';evidence.mkdir()
    m=pd.DataFrame(rows);m['anchor_brier']=m.loc[m.recipe=='anchor','brier'].iloc[0]
    m['delta_vs_anchor']=m.brier-m.anchor_brier
    r.atomic_csv(old/'metrics.csv',m);r.atomic_csv(old/'ablations.csv',m[['recipe','delta_vs_anchor']])
    r.atomic_json(old/'summary.json',{'status':'COMPLETE','synthetic':True})
    r.atomic_json(old/'prepare.json',{'status':'COMPLETE','synthetic':True})
    with patch.object(r.wf,'EXPECTED_SHA',head):
        r.atomic_json(old/'preflight.json',{'state':r.wf.repository_state(repo)})
    manifest={'fingerprint':'b'*64,'upstream_fingerprint':'a'*64,
       'config':{'feature_parameters':r.sf.PARAMETERS,'recipes':r.BASE_RECIPES},
       'source':{'reference/research_workflow.py':r.sha(kit/'frozen/research_workflow.py'),
                 'reference/shot_features.py':r.sha(kit/'frozen/shot_features.py'),
                 'schedule_features.py':r.sha(kit/'frozen/schedule_features.py')},
       'reference_commit':head,'environment':r.environment(),
       'data':{p.name:r.sha(p) for p in (repo/'data/kaggle/raw').glob('*.csv')},'upstream_files':upstream}
    r.atomic_json(old/'manifest.json',manifest)
    for n in ['manifest.json','preflight.json','metrics.csv','summary.json','prepare.json','ablations.csv']:
        shutil.copy2(old/n,evidence/n)
    return {'kit':kit,'repo':repo,'schedule':schedule,'shooting':shooting,'head':head}
