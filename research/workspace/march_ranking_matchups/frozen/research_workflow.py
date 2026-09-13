"""Bounded, content-addressed shooting research. No cloud calls or Git writes."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import warnings
import zipfile

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits

from shot_features import (ALL_FEATURES, ANCHOR_COLS, CONTROL, RECIPES, RESIDUAL_COLS,
                           PROFILE_COLS, build_snapshot, feature_registry,
                           pair_features, tournament_pairs, require)

EXPECTED_SHA='84b8fb36644a6558beded6dad84f5645ea4405d3'
ALLOWED_DIRTY={'notebooks/00_data_audit_and_preparation.ipynb',
               'notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb'}
CONFIG={'round':'02-shooting-research','first_season':2013,'cutoff_day':132,
        'exclude_seasons':[2020],'smoke_seasons':[2019],
        'panel_seasons':[2016,2017,2018,2019,2021],
        'genders':['M','W'],'logistic_C':0.1,'max_iter':2000,'minimum_prior_seasons':3,
        'include_first_four':False,'threads':2,'seed':20260911,
        'anchor_columns':ANCHOR_COLS,'new_residual_columns':RESIDUAL_COLS,
        'new_profile_columns':PROFILE_COLS,
        'promotion_mean_delta':-0.001,'promotion_positive_seasons':3,'max_worst_season_delta':0.01,
        'scope':'exploratory previously-used 2016-2021 seasons, NOT untouched validation or leaderboard'}
START=time.monotonic()


def event(name:str,**kwargs) -> None:
    print(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                      'elapsed_seconds':round(time.monotonic()-START,3),'event':name,**kwargs},default=str),flush=True)


def sha(path:Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()


def atomic_json(path:Path,data:dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.partial')
    tmp.write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False,default=str)+'\n')
    os.replace(tmp,path)


def atomic_csv(path:Path,frame:pd.DataFrame) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.partial')
    frame.to_csv(tmp,index=False,float_format='%.17g')
    os.replace(tmp,path)


def git(repo:Path,*args:str) -> bytes:
    env=os.environ.copy();env['GIT_OPTIONAL_LOCKS']='0'
    r=subprocess.run(['git','-C',str(repo),*args],env=env,capture_output=True,timeout=30,check=False)
    if r.returncode:
        raise RuntimeError('Read-only Git check failed: '+r.stderr.decode(errors='replace')[:500])
    return r.stdout


def repository_state(repo:Path) -> dict:
    head=git(repo,'rev-parse','HEAD').decode().strip()
    require(head==EXPECTED_SHA,'HEAD differs from the audited commit; do not reset the checkout')
    require(git(repo,'rev-parse','refs/remotes/origin/main').decode().strip()==EXPECTED_SHA,
            'Recorded origin/main differs; review the source version')
    require(git(repo,'diff','--name-only','--diff-filter=U')==b'', 'Unmerged Git files')
    changed=set()
    for args in [('diff','--name-only','-z'),('diff','--cached','--name-only','-z')]:
        changed.update(p.decode() for p in git(repo,*args).split(b'\0') if p)
    require(changed<=ALLOWED_DIRTY,'Unexpected tracked changes: '+str(sorted(changed-ALLOWED_DIRTY)))
    # Verify all executable/configuration inputs against Git objects WITHOUT importing them.
    tracked=git(repo,'ls-files','-z').split(b'\0')
    blobs={}
    for b in tracked:
        if not b: continue
        name=b.decode()
        if name.startswith(('src/','configs/')) or name in ('pyproject.toml','uv.lock'):
            path=repo/name
            require(path.is_file() and not path.is_symlink(),f'Missing or symlinked tracked source: {name}')
            expected=git(repo,'show',EXPECTED_SHA+':'+name)
            actual=path.read_bytes()
            require(actual==expected,f'Working source differs from Git object: {name}')
            blobs[name]=hashlib.sha256(actual).hexdigest()
    details={}
    for name in sorted(changed):
        path=repo/name
        require(path.is_file() and not path.is_symlink(),f'Unexpected notebook file state: {name}')
        details[name]=sha(path)
    return {'head':head,'dirty_notebooks_left_untouched':details,'computational_source_sha256':blobs,
            'index_sha256':hashlib.sha256(git(repo,'ls-files','--stage','-z')).hexdigest()}


def preflight(kit:Path,repo:Path) -> dict:
    require(not kit.is_relative_to(repo), 'Keep the research kit beside the repository, not inside it')
    event('preflight_started')
    state=repository_state(repo)
    raw=repo/'data/kaggle/raw'
    expected=json.loads((kit/'expected_inputs.json').read_text())
    measured={}
    for i,(name,digest) in enumerate(sorted(expected.items()),1):
        path=raw/name
        require(path.is_file() and not path.is_symlink(),f'Missing raw input: {name}')
        measured[name]=sha(path)
        require(measured[name]==digest,f'Raw snapshot changed: {name}. Do not overwrite or redownload it.')
        event('input_verified',file=name,completed=i,total=len(expected))
    source={p.name:sha(p) for p in [kit/'shot_features.py',kit/'research_workflow.py',kit/'run_round02.py']}
    environment={k:importlib.metadata.version(k) for k in ('numpy','pandas','scipy','scikit-learn','plotly')}
    environment['python']=platform.python_version()
    identity={'config':CONFIG,'source':source,'data':measured,'environment':environment,'reference_commit':EXPECTED_SHA}
    fingerprint=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    directory=kit/'private_runs'/fingerprint
    directory.mkdir(parents=True,exist_ok=True)
    atomic_json(directory/'manifest.json',dict(identity,fingerprint=fingerprint))
    atomic_json(directory/'preflight.json',{'status':'PASS_ISOLATED_RESEARCH','state':state,
                'raw_tables_hashed':len(measured),'original_worktree_clean_gate_still_unresolved':bool(state['dirty_notebooks_left_untouched']),
                'isolation_resolution':'Known two notebook edits are preserved and never imported. Only this isolated kit executes.',
                'repo_source_imported':False})
    atomic_json(kit/'reports/latest_run.json',{'fingerprint':fingerprint,'run_dir':str(directory)})
    return {'directory':directory,'identity':identity,'state':state,'raw':raw,'fingerprint':fingerprint}


def final_preservation(repo:Path,ctx:dict) -> None:
    require(repository_state(repo)==ctx['state'],'Repository changed while research ran; do not start another stage')
    for name,digest in ctx['identity']['data'].items():
        require(sha(ctx['raw']/name)==digest,f'Input changed during stage: {name}')
    event('preservation_verified',repository_unchanged=True,raw_data_unchanged=True)


def checkpoint_ok(receipt:Path) -> bool:
    if not receipt.exists(): return False
    record=json.loads(receipt.read_text())
    require(record.get('complete') is True,'Incomplete checkpoint receipt')
    for name,digest in record['outputs'].items():
        p=receipt.parent/name
        require(p.is_file() and sha(p)==digest,'Corrupt checkpoint: '+str(p))
    return True


def finish_checkpoint(folder:Path,names:list[str],**metadata) -> None:
    atomic_json(folder/'complete.json',{'complete':True,'outputs':{n:sha(folder/n) for n in names},**metadata})


def prepare(ctx:dict,phase:str) -> None:
    end=2019 if phase=='smoke' else 2021
    seasons=[s for s in range(2013,end+1) if s!=2020]
    total=len(seasons)*2
    count=0;reused=0;built=0
    for gender in ('M','W'):
        tables={name:pd.read_csv(ctx['raw']/(gender+name+'.csv')) for name in
                ('RegularSeasonCompactResults','RegularSeasonDetailedResults','NCAATourneySeeds')}
        # No tournament target file is read by this stage.
        for season in seasons:
            folder=ctx['directory']/'snapshots'/f'{gender}_{season}'
            if checkpoint_ok(folder/'complete.json'):
                reused+=1;event('snapshot_reused',gender=gender,season=season,completed=count+1,total=total)
            else:
                event('snapshot_started',gender=gender,season=season,completed=count,total=total)
                with threadpool_limits(limits=2):
                    snap,audit=build_snapshot(tables['RegularSeasonCompactResults'],tables['RegularSeasonDetailedResults'],
                                              tables['NCAATourneySeeds'],gender,season)
                atomic_csv(folder/'teams.csv',snap)
                atomic_csv(folder/'opponent_exclusion_audit.csv',audit)
                seeded=snap.loc[snap.seed.notna()]
                check={'gender':gender,'season':season,'teams':len(snap),'seeded_teams':len(seeded),
                       'minimum_seeded_detail_coverage':float(seeded.detailed_coverage.min()),
                       'minimum_seeded_detail_games':int(seeded.detailed_games.min()),
                       'cutoff_day':132,'tournament_labels_read':False}
                require(check['seeded_teams']>0,'No seeded teams')
                require(check['minimum_seeded_detail_coverage']>=.8 and check['minimum_seeded_detail_games']>=10,
                        'Seeded team detail coverage failed')
                atomic_json(folder/'coverage.json',check)
                finish_checkpoint(folder,['teams.csv','opponent_exclusion_audit.csv','coverage.json'],**check)
                built+=1
                event('snapshot_complete',gender=gender,season=season,completed=count+1,total=total)
            count+=1
    atomic_csv(ctx['directory']/'feature_registry.csv',feature_registry())
    atomic_json(ctx['directory']/f'prepare_{phase}.json',{'status':'PASS','new_snapshots':built,
                'reused_snapshots':reused,'new_matchup_candidates':14,'anchor_features':16,
                'snapshot_rating_fits_per_new_snapshot':5,'tournament_classifiers_fitted':0})


def fitted_model(x:pd.DataFrame,y:np.ndarray,columns:list[str]) -> dict:
    values=x[columns].to_numpy(dtype=float)
    require(np.isfinite(values).all(),'Nonfinite training features')
    require(np.isin(y,[0,1]).all() and np.unique(y).size==2,'Training requires both classes')
    require(len(values)==len(y),'Training alignment mismatch')
    # Paired orientations preserve p(A,B)=1-p(B,A). Each physical game has total weight 1.
    mirrored=np.vstack([values,-values]);labels=np.r_[y,1-y]
    scale=np.sqrt(np.mean(mirrored**2,axis=0))
    active=scale>1e-12
    require(active.any(),'No training-supported columns')
    clf=LogisticRegression(C=CONFIG['logistic_C'],fit_intercept=False,solver='lbfgs',
                           max_iter=CONFIG['max_iter'],tol=1e-7,random_state=CONFIG['seed'])
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning)
        with threadpool_limits(limits=2):
            clf.fit(mirrored[:,active]/scale[active],labels,sample_weight=np.full(len(labels),.5))
    return {'columns':columns,'active_indices':np.flatnonzero(active).tolist(),
            'scales':scale[active].tolist(),'coefficients':clf.coef_[0].tolist(),
            'removed_training_constant':[columns[i] for i in np.flatnonzero(~active)],
            'fit_intercept':False,'C':CONFIG['logistic_C'],'physical_train_games':len(values),
            'iterations':int(clf.n_iter_[0]),'selection':'training support/constant only, no capacity competition'}


def predict(model:dict,x:pd.DataFrame) -> np.ndarray:
    v=x[model['columns']].to_numpy(dtype=float)[:,model['active_indices']]
    require(np.isfinite(v).all(),'Nonfinite prediction features')
    return expit((v/np.asarray(model['scales']))@np.asarray(model['coefficients']))


def split_indices(frame:pd.DataFrame,season:int) -> tuple[np.ndarray,np.ndarray]:
    train=np.flatnonzero(frame.Season.to_numpy()<season)
    val=np.flatnonzero(frame.Season.to_numpy()==season)
    require(len(train)>0 and len(val)>0,'Empty temporal split')
    require(len(frame.iloc[train].Season.unique())>=CONFIG['minimum_prior_seasons'],'Fewer than three prior seasons')
    return train,val


def evaluate(ctx:dict,phase:str) -> None:
    seasons=CONFIG['smoke_seasons'] if phase=='smoke' else CONFIG['panel_seasons']
    end=max(seasons)
    if phase=='panel':
        smoke=ctx['directory']/'smoke_summary.json'
        require(smoke.is_file(),'Run notebook 02 / smoke first')
        sm=json.loads(smoke.read_text())
        require(sm.get('status')=='COMPLETE','Smoke did not complete')
        require(not sm.get('clearly_unproductive_smoke',False),'All smoke challengers were clearly worse. Inspect before panel expansion.')
    records=[];new=0;reused=0;task=0;total=2*len(seasons)*len(RECIPES)
    for gender in ('M','W'):
        train_seasons=[s for s in range(2013,end+1) if s!=2020]
        snapshots=[]
        for s in train_seasons:
            folder=ctx['directory']/'snapshots'/f'{gender}_{s}'
            require(checkpoint_ok(folder/'complete.json'),f'Missing snapshot {gender} {s}; run prepare for this phase')
            snapshots.append(pd.read_csv(folder/'teams.csv',float_precision='round_trip'))
        teams=pd.concat(snapshots,ignore_index=True)
        labels=pd.read_csv(ctx['raw']/(gender+'NCAATourneyCompactResults.csv'))
        pairs,y=tournament_pairs(labels,gender,train_seasons)
        features=pair_features(teams,pairs)
        swapped=pairs.rename(columns={'Team1ID':'Team2ID','Team2ID':'Team1ID'})
        flipped=pair_features(teams,swapped)
        swap_error=float(np.max(np.abs(features[ALL_FEATURES].to_numpy()+flipped[ALL_FEATURES].to_numpy())))
        require(swap_error<1e-10,'Feature team-swap invariant failed')
        for season in seasons:
            ti,vi=split_indices(features,season)
            train,valid=features.iloc[ti],features.iloc[vi]
            for recipe,cols in RECIPES.items():
                folder=ctx['directory']/'fits'/f'{gender}_{season}_{recipe}'
                if checkpoint_ok(folder/'complete.json'):
                    metric=json.loads((folder/'metrics.json').read_text());reused+=1
                    event('fit_reused',gender=gender,season=season,recipe=recipe,completed=task+1,total=total)
                else:
                    event('fit_started',gender=gender,season=season,recipe=recipe,completed=task,total=total)
                    model=fitted_model(train,y[ti],cols)
                    p=predict(model,valid)
                    reverse=predict(model,flipped.iloc[vi])
                    probability_swap_error=float(np.max(np.abs(p+reverse-1.)))
                    require(probability_swap_error<1e-10,'Probability complement test failed')
                    require(np.isfinite(p).all() and ((p>0)&(p<1)).all(),'Invalid probabilities')
                    metric={'Gender':gender,'Season':season,'recipe':recipe,'games':len(vi),
                            'train_games':len(ti),'train_last_season':int(train.Season.max()),
                            'brier':float(np.mean((p-y[vi])**2)),
                            'log_loss':float(-np.mean(y[vi]*np.log(np.clip(p,1e-15,1))+(1-y[vi])*np.log(np.clip(1-p,1e-15,1)))),
                            'feature_count':len(cols),'active_features':len(model['active_indices']),
                            'swap_error':probability_swap_error,'feature_swap_error':swap_error,
                            'evidence':'exploratory historical main draw; not leaderboard'}
                    pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=p
                    pred['squared_error']=(p-y[vi])**2
                    model['train_seasons']=sorted(map(int,train.Season.unique()))
                    atomic_json(folder/'model.json',model)
                    atomic_json(folder/'metrics.json',metric)
                    atomic_csv(folder/'predictions.csv',pred)
                    finish_checkpoint(folder,['model.json','metrics.json','predictions.csv'],recipe=recipe,season=season,gender=gender)
                    new+=1;event('fit_complete',**metric,completed=task+1,total=total)
                records.append(metric);task+=1
    metrics=pd.DataFrame(records)
    a=metrics.loc[metrics.recipe=='anchor',['Gender','Season','brier']].rename(columns={'brier':'anchor_brier'})
    metrics=metrics.merge(a,on=['Gender','Season'],validate='many_to_one')
    metrics['delta_vs_anchor']=metrics.brier-metrics.anchor_brier
    atomic_csv(ctx['directory']/f'{phase}_metrics.csv',metrics)
    aggregated=aggregate(metrics)
    atomic_csv(ctx['directory']/f'{phase}_aggregate.csv',aggregated)
    effect=ablation_effects(metrics)
    atomic_csv(ctx['directory']/f'{phase}_ablations.csv',effect)
    unproductive=bool((metrics.loc[metrics.recipe!='anchor','delta_vs_anchor']>0.01).all())
    summary={'status':'COMPLETE','phase':phase,'fingerprint':ctx['fingerprint'],
             'new_tournament_classifier_fits':new,'reused_tournament_classifier_fits':reused,
             'total_tournament_classifier_fits':len(metrics),'new_matchup_candidates':14,
             'fixed_anchor_features':16,'model':'same logistic C=0.1 for all four recipes; no hyperparameter search',
             'validation_seasons':seasons,'minimum_train_season':2013,
             'clearly_unproductive_smoke':unproductive if phase=='smoke' else False,
             'current_submitted_brier':0.1222672,'research_target_brier':0.1097454,
             'new_leaderboard_score':None,'github_updated':False,'repo_modified':False,
             'raw_modified':False,'uses_2022_2026_targets':False,
             'not_final_submitted_model_reproduction':True,
             'limitations':['Previously-consumed historical seasons: exploratory, not an untouched test.',
                            'Residuals mix luck, defense, opponent personnel and model misspecification.',
                            'Men and women fitted separately; published domain findings need empirical validation in both.',
                            'Attribution is conditional on this fixed reference, not the final pooled XGBoost recipe.'],
             'next_step':'Review smoke; notebook 03 expands the unchanged recipe to the five-season panel.' if phase=='smoke'
                         else 'Review season stability and paired ablations before promotion or new hypotheses.'}
    if phase=='panel':
        summary['practical_screen']=panel_screen(metrics)
    atomic_json(ctx['directory']/f'{phase}_summary.json',summary)


def aggregate(metrics:pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for (gender,recipe),g in metrics.groupby(['Gender','recipe'],sort=True):
        rows.append({'Gender':gender,'recipe':recipe,'seasons':len(g),'games':int(g.games.sum()),
                     'mean_season_brier':float(g.brier.mean()),
                     'game_weighted_brier':float(np.average(g.brier,weights=g.games)),
                     'mean_season_delta':float(g.delta_vs_anchor.mean()),
                     'improved_seasons':int((g.delta_vs_anchor<0).sum()),
                     'worst_season_delta':float(g.delta_vs_anchor.max())})
    # Combined scores weighted by physical games, never an unweighted mean of gender metrics.
    for recipe,g in metrics.groupby('recipe',sort=True):
        per_season=[
            float(np.average(v.brier,weights=v.games)) for _,v in g.groupby('Season')]
        rows.append({'Gender':'combined','recipe':recipe,'seasons':len(per_season),'games':int(g.games.sum()),
                     'mean_season_brier':float(np.mean(per_season)),
                     'game_weighted_brier':float(np.average(g.brier,weights=g.games)),
                     'mean_season_delta':float(np.mean([np.average(v.delta_vs_anchor,weights=v.games) for _,v in g.groupby('Season')])),
                     'improved_seasons':None,'worst_season_delta':None})
    return pd.DataFrame(rows)


def ablation_effects(metrics:pd.DataFrame) -> pd.DataFrame:
    wide=metrics.pivot(index=['Gender','Season'],columns='recipe',values='brier')
    rows=[]
    for (g,s),v in wide.iterrows():
        for name,with_,without in [('residual_alone','anchor_residual','anchor'),
                                  ('profile_alone','anchor_profile','anchor'),
                                  ('both','anchor_both','anchor'),
                                  ('residual_given_profile','anchor_both','anchor_profile'),
                                  ('profile_given_residual','anchor_both','anchor_residual')]:
            rows.append({'Gender':g,'Season':int(s),'comparison':name,
                         'delta_brier':float(v[with_]-v[without]),
                         'sign':'negative favors inclusion; fixed input sets, no capacity replacements'})
    return pd.DataFrame(rows)


def panel_screen(metrics:pd.DataFrame) -> list[dict]:
    out=[];rng=np.random.default_rng(CONFIG['seed'])
    for (g,r),f in metrics.loc[metrics.recipe!='anchor'].groupby(['Gender','recipe'],sort=True):
        d=f.delta_vs_anchor.to_numpy()
        draws=rng.choice(d,size=(5000,len(d)),replace=True).mean(axis=1)
        good=(d.mean()<=-0.001 and np.count_nonzero(d<0)>=3 and d.max()<=.01)
        out.append({'Gender':g,'recipe':r,'mean_delta':float(d.mean()),
                    'descriptive_season_bootstrap_95pct':[float(np.quantile(draws,.025)),float(np.quantile(draws,.975))],
                    'passes_preregistered_practical_screen':bool(good),
                    'decision':'candidate for stronger-model transfer test' if good else 'do not promote; inspect ablations',
                    'caution':'Five reused seasons and multiple comparisons; this is not confirmatory significance.'})
    return out


def report(ctx:dict,phase:str,kit:Path) -> None:
    from research_plots import make_report
    make_report(ctx['directory'],phase)
    out=kit/'reports';out.mkdir(exist_ok=True)
    summary=json.loads((ctx['directory']/f'{phase}_summary.json').read_text())
    atomic_json(out/'milestone_02_summary.json',summary)
    archive=out/'milestone_02_return.zip'
    allow=[f'{phase}_summary.json',f'{phase}_metrics.csv',f'{phase}_aggregate.csv',f'{phase}_ablations.csv',
           'feature_registry.csv','manifest.json','preflight.json',f'prepare_{phase}.json']
    # Metadata and generated metrics only; no raw rows, source notebooks, auth files or models.
    temp=archive.with_suffix('.partial')
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
        for name in allow:
            p=ctx['directory']/name
            if p.is_file():z.write(p,name)
    os.replace(temp,archive)
    atomic_json(out/'latest_report.json',{'phase':phase,'html':str(ctx['directory']/f'{phase}_report.html'),
                                          'return_zip':str(archive),'run_dir':str(ctx['directory'])})
    event('return_report_ready',path=str(archive),html=str(ctx['directory']/f'{phase}_report.html'))


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['prepare','evaluate','report'])
    parser.add_argument('--phase',choices=['smoke','panel'],default='smoke')
    parser.add_argument('--repo',type=Path,default=Path(os.getenv('MARCH_REPO',str(Path.home()/'march-machine-learning-mania-2026'))))
    args=parser.parse_args()
    kit=Path(__file__).resolve().parent;repo=args.repo.expanduser().resolve()
    ctx=None
    try:
        ctx=preflight(kit,repo)
        if args.stage=='prepare':prepare(ctx,args.phase)
        elif args.stage=='evaluate':evaluate(ctx,args.phase)
        else:report(ctx,args.phase,kit)
        final_preservation(repo,ctx)
        event('stage_passed',stage=args.stage,phase=args.phase,fingerprint=ctx['fingerprint'])
    except Exception as e:
        data={'status':'STOP','stage':args.stage,'phase':args.phase,'error':str(e),'exception':type(e).__name__,
              'note':'Completed checkpoints remain. Do not reset, wipe, or automatically increase limits.'}
        atomic_json(kit/'reports/failure.json',data)
        event('STOP',**data)
        raise

if __name__=='__main__':main()
