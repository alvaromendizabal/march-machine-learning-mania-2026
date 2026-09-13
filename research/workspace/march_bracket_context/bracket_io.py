"""Small checked I/O and native-JSON model replay; no model deserialization code execution."""
from __future__ import annotations
import hashlib, importlib.metadata, json, os, platform, sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent/'frozen'))
import research_workflow as rf
import shot_features as sf
require=sf.require
sha=rf.sha
event=rf.event
FIT_FILES=['model.json','metrics.json','predictions.csv']

def read_json(p):return json.loads(Path(p).read_text())
def read_csv(p):return pd.read_csv(p,float_precision='round_trip')
def environment():
    return {**{k:importlib.metadata.version(k) for k in ['numpy','pandas','scipy','scikit-learn','plotly']},'python':platform.python_version()}
def safe_file(root,relative):
    root=Path(root);rel=Path(relative)
    require(not rel.is_absolute() and '..' not in rel.parts,'Unsafe relative path')
    p=root/rel
    require(p.is_file() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents),'Missing/symlinked input: '+str(p))
    return p

def output_dir(p):
    p=Path(p)
    require(not p.is_symlink() and not any(q.is_symlink() for q in p.parents),'Unsafe output directory')
    p.mkdir(parents=True,exist_ok=True)

def checked_output(p):
    p=Path(p);output_dir(p.parent)
    require(not p.is_symlink() and not p.with_suffix(p.suffix+'.partial').is_symlink(),'Unsafe output file')
    return p

def atomic_json(p,obj):rf.atomic_json(checked_output(p),obj)
def atomic_csv(p,obj):rf.atomic_csv(checked_output(p),obj)

def checkpoint(folder,names):
    folder=Path(folder)
    if not (folder/'complete.json').exists():return False
    c=read_json(safe_file(folder,'complete.json'))
    require(c.get('complete') is True and set(c.get('outputs',{}))==set(names),'Checkpoint scope mismatch')
    for n,h in c['outputs'].items():require(sha(safe_file(folder,n))==h,'Corrupt checkpoint: '+str(folder/n))
    return True

def seal(folder,names):
    atomic_json(Path(folder)/'complete.json',{'complete':True,'outputs':{n:sha(safe_file(folder,n)) for n in names}})

def stage_seal(out,stage,names):atomic_json(out/(stage+'_hashes.json'),{n:sha(safe_file(out,n)) for n in names})
def stage_check(out,stage,names):
    c=read_json(safe_file(out,stage+'_hashes.json'));require(set(c)==set(names),'Stage output scope mismatch')
    for n,h in c.items():require(sha(safe_file(out,n))==h,'Stage output changed: '+n)

def normalize_metric(m,y,p,gender,season):
    require(len(y)>0 and len(y)==len(p),'Prediction/target length mismatch')
    require(np.isin(y,[0,1]).all() and np.isfinite(p).all() and ((p>0)&(p<1)).all(),'Invalid replay values')
    brier=float(np.mean((p-y)**2));loss=float(-np.mean(y*np.log(p)+(1-y)*np.log1p(-p)))
    require('brier' in m and np.isfinite(m['brier']) and abs(m['brier']-brier)<1e-12,'Replay Brier mismatch')
    for name,value in [('Gender',gender),('Season',season),('games',len(y))]:
        require(name not in m or m[name]==value,'Replay identity mismatch: '+name)
    if 'log_loss' in m:require(np.isfinite(m['log_loss']) and abs(m['log_loss']-loss)<1e-10,'Stored log loss inconsistent')
    return dict(m,Gender=gender,Season=season,games=len(y),log_loss=loss,log_loss_source='verified_predictions')

def validate_model(m,cols,season,ntrain):
    require(m['columns']==cols and m['C']==.1 and m['fit_intercept'] is False,'Different fitted recipe')
    require(m['physical_train_games']==ntrain and m['train_seasons']==list(range(2013,season)),'Training history differs')
    idx=m['active_indices']
    require(len(idx)>0 and len(idx)==len(set(idx)) and all(isinstance(i,int) and 0<=i<len(cols) for i in idx),'Invalid active columns')
    require(len(idx)==len(m['scales'])==len(m['coefficients']),'Model dimension mismatch')
    require(np.isfinite(m['coefficients']).all() and np.isfinite(m['scales']).all() and (np.array(m['scales'])>0).all(),'Invalid fitted values')

def replay(folder,cols,season,bundle):
    require(checkpoint(folder,FIT_FILES),'Reference checkpoint incomplete')
    pairs,y,x,_,_=bundle;ti,vi=rf.split_indices(x,season)
    m=read_json(safe_file(folder,'model.json'));validate_model(m,cols,season,len(ti))
    p=rf.predict(m,x.iloc[vi]);rev=x.iloc[vi].copy();rev[cols]=-rev[cols];q=rf.predict(m,rev)
    require(np.max(np.abs(p+q-1))<1e-10,'Prediction team-swap failure')
    saved=read_csv(safe_file(folder,'predictions.csv'));keys=['Gender','Season','Team1ID','Team2ID']
    require(saved[keys].reset_index(drop=True).equals(pairs.iloc[vi][keys].reset_index(drop=True)),'Reference keys/order differ')
    require(np.array_equal(saved.y.to_numpy(),y[vi]) and np.max(np.abs(saved.probability.to_numpy()-p))<1e-12,'Saved predictions differ')
    metric=normalize_metric(read_json(safe_file(folder,'metrics.json')),y[vi],p,'W',season)
    return metric,m,saved
