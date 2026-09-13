"""Read-only upstream reuse and bounded seven-feature experiments.

No AWS/Kaggle clients, Git mutations, legacy feature rebuilding, pickle loading,
submission generation, or automatic full-panel expansion.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import time
import zipfile
import numpy as np
import pandas as pd

KIT=Path(__file__).resolve().parent
# Frozen, reviewed copies shipped in this kit; never import the AWS repository.
sys.path.insert(0,str(KIT/'reference'))
import shot_features as reference_features
import research_workflow as reference_workflow
from schedule_features import (PARAMETERS,QUALITY_COLS,RECORD_COLS,NEW_COLS,
                                build_schedule_snapshot,matchup_features,registry,require)

ANCHOR=reference_features.ANCHOR_COLS
RECIPES={'anchor':ANCHOR,'anchor_quality':ANCHOR+QUALITY_COLS,
         'anchor_record':ANCHOR+RECORD_COLS,'anchor_both':ANCHOR+NEW_COLS}
CONFIG={'round':'04-quality-wins-and-reference-record','validation_season':2018,
        'training_seasons':list(range(2013,2018)),'genders':['M','W'],
        'anchor_columns':ANCHOR,'recipes':RECIPES,'feature_parameters':PARAMETERS,
        'logistic_C':.1,'max_iter':2000,'minimum_prior_seasons':3,
        'scale_policy':'RMS over training mirrored orientations; no validation scaling',
        'mirrored_physical_game_weight':1.,'threads':2,'seed':20260911,
        'include_first_four':False,'max_new_classifier_fits':8,
        'screen_to_replicate_delta':-.001,
        'scope':'Exploratory 2018 known historical season, NOT untouched validation or 2026 leaderboard',
        'no_automatic_feature_promotion':True}
sha=reference_workflow.sha
atomic_json=reference_workflow.atomic_json
atomic_csv=reference_workflow.atomic_csv
START=time.monotonic()

def event(name,**data):
    print(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                       'event':name,'elapsed_seconds':round(time.monotonic()-START,3),**data},default=str),flush=True)

def read_json(p):
    return json.loads(Path(p).read_text())

def code_identity(kit):
    names=['schedule_features.py','schedule_workflow.py','schedule_plots.py','run_round04.py',
           'reference/shot_features.py','reference/research_workflow.py','reference/run_round02.py']
    return {name:sha(kit/name) for name in names}

def verify_checkpoint(folder,required):
    """Validate hashes before reading any upstream file; no executable model formats."""
    folder=Path(folder)
    require(not folder.is_symlink(),'Symlinked checkpoint directory')
    receipt=folder/'complete.json'
    if not receipt.exists():return False
    require(not receipt.is_symlink(),'Symlinked checkpoint receipt')
    r=read_json(receipt)
    require(r.get('complete') is True,'Incomplete checkpoint receipt')
    outputs=r.get('outputs',{})
    require(set(required)<=set(outputs),'Checkpoint missing expected outputs')
    for name,digest in outputs.items():
        require(Path(name).name==name and name not in ('.','..'),'Unsafe checkpoint filename')
        p=folder/name
        require(p.is_file() and not p.is_symlink() and sha(p)==digest,'Corrupt checkpoint: '+str(p))
    return True

def seal(folder,names,**metadata):
    atomic_json(Path(folder)/'complete.json',{'complete':True,'outputs':{n:sha(Path(folder)/n) for n in names},**metadata})

def read_csv(p):
    return pd.read_csv(p,float_precision='round_trip')

def prior_screens(metrics):
    q=metrics.loc[metrics.recipe!='anchor']
    require(len(q)==6,'Expected six shooting challenger rows')
    return {'all_six_additions_worsened_2019':bool((q.delta_vs_anchor>0).all()),
            'old_clearly_unproductive_flag':bool((q.delta_vs_anchor>.01).all()),
            'explanation':'The old flag required ALL six deltas >0.01. False did not mean a gain.',
            'decision':'Pause automatic shooting-panel expansion; no shooting candidate promoted',
            'scope':'Negative under one fixed recipe/season; not proof of uselessness in every model or season'}

def preflight(kit:Path,repo:Path,prior:Path):
    require(not kit.is_relative_to(repo) and not kit.is_relative_to(prior),'Kit must be separate from repository and prior research')
    evidence=kit/'evidence'
    source_manifest=read_json(evidence/'manifest.json')
    for name,digest in source_manifest['source'].items():
        require(sha(kit/'reference'/name)==digest,'Frozen reference code changed: '+name)
    state=reference_workflow.repository_state(repo)
    source_state=read_json(evidence/'preflight.json')['state']
    require(state==source_state,'Repository differs from milestone 02; preserve changes and inspect, do not reset')
    raw=repo/'data/kaggle/raw'
    for i,(name,digest) in enumerate(sorted(source_manifest['data'].items()),1):
        p=raw/name
        require(p.is_file() and not p.is_symlink() and sha(p)==digest,'Input changed or missing: '+name)
        event('input_verified',completed=i,total=len(source_manifest['data']),file=name)
    environment={k:importlib.metadata.version(k) for k in ('numpy','pandas','scipy','scikit-learn','plotly')}
    environment['python']=platform.python_version()
    require(environment==source_manifest['environment'],'Environment differs from milestone 02; inspect versions before experiment')
    old=prior/'private_runs'/source_manifest['fingerprint']
    require(old.is_dir() and not old.is_symlink(),'Milestone-02 private cache missing. Do not rebuild it automatically.')
    require(read_json(old/'manifest.json')==source_manifest,'Cached manifest does not match the returned report')
    parent_files={}
    for gender in ('M','W'):
        for season in range(2013,2020):
            f=old/'snapshots'/f'{gender}_{season}'
            require(verify_checkpoint(f,['teams.csv','coverage.json','opponent_exclusion_audit.csv']),f'Missing prior snapshot: {gender} {season}')
            for n in ['teams.csv','coverage.json','opponent_exclusion_audit.csv','complete.json']:
                parent_files[str((f/n).relative_to(old))]=sha(f/n)
        for recipe in reference_features.RECIPES:
            f=old/'fits'/f'{gender}_2019_{recipe}'
            require(verify_checkpoint(f,['model.json','metrics.json','predictions.csv']),f'Missing 2019 cached fit: {gender} {recipe}')
            for n in ['model.json','metrics.json','predictions.csv','complete.json']:
                parent_files[str((f/n).relative_to(old))]=sha(f/n)
    identity={'config':CONFIG,'source':code_identity(kit),'environment':environment,
              'data':source_manifest['data'],'reference_commit':source_manifest['reference_commit'],
              'upstream_fingerprint':source_manifest['fingerprint'],'upstream_files':parent_files,
              'evidence_sha256':{p.name:sha(p) for p in sorted(evidence.glob('*')) if p.is_file()}}
    fingerprint=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    directory=kit/'private_runs'/fingerprint
    directory.mkdir(parents=True,exist_ok=True)
    atomic_json(directory/'manifest.json',dict(identity,fingerprint=fingerprint))
    atomic_json(directory/'preflight.json',{'status':'PASS_ISOLATED_CACHE_REUSE','state':state,
                 'upstream_snapshots_verified':14,'raw_hashes_verified':8,
                 'original_notebook_edits_preserved':True,'repository_code_imported':False})
    atomic_json(kit/'reports/latest_run.json',{'run_dir':str(directory),'fingerprint':fingerprint})
    event('preflight_pass',upstream_snapshots=14,raw_inputs=8)
    return {'kit':kit,'repo':repo,'prior':old,'directory':directory,'raw':raw,
            'fingerprint':fingerprint,'identity':identity,'state':state}

def preservation(ctx):
    require(reference_workflow.repository_state(ctx['repo'])==ctx['state'],'Repository changed during stage')
    for name,digest in ctx['identity']['data'].items():
        require(sha(ctx['raw']/name)==digest,'Raw input changed during stage: '+name)
    for name,digest in ctx['identity']['upstream_files'].items():
        require(sha(ctx['prior']/name)==digest,'Upstream cache changed during stage: '+name)
    event('preservation_pass',repository_unchanged=True,raw_unchanged=True,upstream_unchanged=True)

def load_base(ctx,gender,end=2019):
    return pd.concat([read_csv(ctx['prior']/'snapshots'/f'{gender}_{s}'/'teams.csv')
                       for s in range(2013,end+1)],ignore_index=True)

def merged_features(ctx,gender,end,with_schedule):
    base=load_base(ctx,gender,end)
    labels=read_csv(ctx['raw']/(gender+'NCAATourneyCompactResults.csv'))
    pairs,y=reference_features.tournament_pairs(labels,gender,list(range(2013,end+1)))
    require(set(pairs.Season.unique())==set(range(2013,end+1)),'A training season is missing')
    a=reference_features.pair_features(base,pairs)
    swap=pairs.rename(columns={'Team1ID':'Team2ID','Team2ID':'Team1ID'})
    af=reference_features.pair_features(base,swap)
    if with_schedule:
        frames=[]
        for s in range(2013,end+1):
            folder=ctx['directory']/'snapshots'/f'{gender}_{s}'
            require(verify_checkpoint(folder,['features.csv','audit.json']),'Missing schedule snapshot')
            frames.append(read_csv(folder/'features.csv'))
        teams=pd.concat(frames,ignore_index=True)
        extra=matchup_features(teams,pairs);extra_swap=matchup_features(teams,swap)
        a[NEW_COLS]=extra[NEW_COLS];af[NEW_COLS]=extra_swap[NEW_COLS]
    cols=ANCHOR+NEW_COLS if with_schedule else reference_features.ALL_FEATURES
    require(np.max(np.abs(a[cols].to_numpy()+af[cols].to_numpy()))<1e-10,'Feature antisymmetry failed')
    return pairs,y,a,af

def prior_diagnosis(ctx):
    """Replay saved predictions, do not refit or select features from these diagnostics."""
    result=[];checks=[];groups=[]
    expected=read_csv(ctx['kit']/'evidence/smoke_metrics.csv')
    for gender in ('M','W'):
        pairs,y,features,_=merged_features(ctx,gender,2019,False)
        ix=np.flatnonzero(pairs.Season.to_numpy()==2019)
        base_pred=None
        for recipe in reference_features.RECIPES:
            folder=ctx['prior']/'fits'/f'{gender}_2019_{recipe}'
            model=read_json(folder/'model.json')
            require(model['columns']==reference_features.RECIPES[recipe],'Prior model columns differ')
            ids=model['active_indices'];n=len(model['columns'])
            require(ids==sorted(set(ids)) and all(isinstance(i,int) and 0<=i<n for i in ids),'Invalid model indices')
            require(len(ids)==len(model['scales'])==len(model['coefficients']),'Model shape mismatch')
            require(np.isfinite(model['coefficients']).all() and np.isfinite(model['scales']).all()
                    and (np.asarray(model['scales'])>0).all(),'Invalid model parameters')
            require(model['C']==.1 and model['fit_intercept'] is False and model['train_seasons']==list(range(2013,2019)),
                    'Prior classifier protocol changed')
            p=reference_workflow.predict(model,features.iloc[ix])
            stored=read_csv(folder/'predictions.csv')
            require(stored[pairs.columns].reset_index(drop=True).equals(pairs.iloc[ix].reset_index(drop=True)),
                    'Prior prediction game IDs/order mismatch')
            require(np.array_equal(stored.y.to_numpy(),y[ix]),'Prior target alignment mismatch')
            require(np.max(np.abs(stored.probability.to_numpy()-p))<1e-12,'Saved predictions do not reproduce')
            score=float(np.mean((p-y[ix])**2))
            expected_score=float(expected.loc[(expected.Gender==gender)&(expected.recipe==recipe),'brier'].iloc[0])
            require(abs(score-expected_score)<1e-12,'Prior Brier mismatch')
            checks.append({'Gender':gender,'recipe':recipe,'brier_replayed':score,
                           'maximum_prediction_difference':float(np.max(np.abs(stored.probability-p))),
                           'new_fits':0})
            if recipe=='anchor':
                base_pred=p;continue
            part=pairs.iloc[ix].copy();part['recipe']=recipe;part['y']=y[ix]
            part['anchor_probability']=base_pred;part['probability']=p
            part['paired_loss_delta']=(p-y[ix])**2-(base_pred-y[ix])**2
            part['seed_gap']=features.iloc[ix].diff_seed.to_numpy()
            part['anchor_confidence_bin']=pd.cut(np.maximum(base_pred,1-base_pred),[.5,.6,.75,.9,1.00001],
                                          include_lowest=True).astype(str)
            result.append(part)
    per_game=pd.concat(result,ignore_index=True)
    grouped=per_game.groupby(['Gender','recipe','anchor_confidence_bin'],observed=True).agg(
        games=('paired_loss_delta','size'),mean_delta=('paired_loss_delta','mean'),
        total_loss_change=('paired_loss_delta','sum')).reset_index()
    atomic_csv(ctx['directory']/'prior_game_diagnostics.csv',per_game)
    atomic_csv(ctx['directory']/'prior_loss_groups.csv',grouped)
    atomic_csv(ctx['directory']/'prior_replay.csv',pd.DataFrame(checks))
    atomic_json(ctx['directory']/'prior_decision.json',prior_screens(expected))
    event('prior_predictions_replayed',comparisons=8,new_fits=0)

def prepare(ctx):
    prior_diagnosis(ctx)
    built=reused=0
    for gender in ('M','W'):
        compact=read_csv(ctx['raw']/(gender+'RegularSeasonCompactResults.csv'))
        for season in range(2013,2019):
            folder=ctx['directory']/'snapshots'/f'{gender}_{season}'
            if verify_checkpoint(folder,['features.csv','audit.json']):
                reused+=1;event('new_feature_snapshot_reused',gender=gender,season=season,completed=built+reused,total=12)
                continue
            base=read_csv(ctx['prior']/'snapshots'/f'{gender}_{season}'/'teams.csv')
            feats,games=build_schedule_snapshot(compact,base,gender,season)
            atomic_csv(folder/'features.csv',feats)
            audit={'gender':gender,'season':season,'teams':len(feats),'physical_games':len(games)//2,
                   'cutoff_day':132,'ratings_fitted':0,'tournament_labels_used':False,
                   'upstream_team_sha256':sha(ctx['prior']/'snapshots'/f'{gender}_{season}'/'teams.csv')}
            atomic_json(folder/'audit.json',audit);seal(folder,['features.csv','audit.json'])
            built+=1;event('new_feature_snapshot_saved',gender=gender,season=season,completed=built+reused,total=12)
    atomic_csv(ctx['directory']/'feature_registry.csv',registry(ANCHOR))
    atomic_json(ctx['directory']/'prepare.json',{'status':'COMPLETE','new_schedule_snapshots':built,
        'reused_schedule_snapshots':reused,'upstream_snapshots_reused':14,'new_rating_fits':0,
        'new_classifier_fits':0,'prior_prediction_replays':8,'new_matchup_features':7})

def evaluate(ctx):
    require((ctx['directory']/'prepare.json').is_file(),'Run prepare first')
    rows=[];new=reused=0;correlations=[]
    for gender in ('M','W'):
        pairs,y,x,flipped=merged_features(ctx,gender,2018,True)
        ti,vi=reference_workflow.split_indices(x,2018)
        require(set(x.iloc[ti].Season)==set(range(2013,2018)),'Training boundary mismatch')
        # Training-only redundancy diagnostics are reported, not used to adapt the fixed feature sets.
        corr=x.iloc[ti][ANCHOR+NEW_COLS].corr()
        for feat in NEW_COLS:
            v=corr.loc[feat,ANCHOR].abs().dropna()
            correlations.append({'Gender':gender,'feature':feat,'most_correlated_anchor':v.idxmax() if len(v) else '',
                                 'absolute_correlation':float(v.max()) if len(v) else None,
                                 'training_last_season':2017,'selection_changed':False})
        for recipe,cols in RECIPES.items():
            folder=ctx['directory']/'fits'/f'{gender}_2018_{recipe}'
            if verify_checkpoint(folder,['metrics.json','model.json','predictions.csv']):
                metric=read_json(folder/'metrics.json');reused+=1
                event('classifier_reused',gender=gender,recipe=recipe,completed=new+reused,total=8)
            else:
                event('classifier_started',gender=gender,recipe=recipe,completed=new+reused,total=8)
                model=reference_workflow.fitted_model(x.iloc[ti],y[ti],cols)
                p=reference_workflow.predict(model,x.iloc[vi]);r=reference_workflow.predict(model,flipped.iloc[vi])
                require(np.isfinite(p).all() and ((p>0)&(p<1)).all(),'Invalid probability')
                swap=float(np.max(np.abs(p+r-1)))
                require(swap<1e-10,'Probability swap failure')
                metric={'Gender':gender,'Season':2018,'recipe':recipe,'games':len(vi),'train_games':len(ti),
                        'train_last_season':2017,'brier':float(np.mean((p-y[vi])**2)),
                        'log_loss':float(-np.mean(y[vi]*np.log(p)+(1-y[vi])*np.log(1-p))),
                        'feature_count':len(cols),'active_features':len(model['active_indices']),
                        'swap_error':swap,'feature_swap_error':0.,
                        'evidence':'Exploratory 2018 main draw; not production model or leaderboard'}
                pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=p
                pred['squared_error']=(p-y[vi])**2
                model['train_seasons']=list(range(2013,2018))
                atomic_json(folder/'metrics.json',metric);atomic_json(folder/'model.json',model)
                atomic_csv(folder/'predictions.csv',pred);seal(folder,['metrics.json','model.json','predictions.csv'])
                new+=1;event('classifier_saved',**metric,completed=new+reused,total=8)
            rows.append(metric)
    metrics=pd.DataFrame(rows)
    anchor=metrics.loc[metrics.recipe=='anchor',['Gender','brier']].rename(columns={'brier':'anchor_brier'})
    metrics=metrics.merge(anchor,on='Gender',validate='many_to_one')
    metrics['delta_vs_anchor']=metrics.brier-metrics.anchor_brier
    atomic_csv(ctx['directory']/'metrics.csv',metrics)
    atomic_csv(ctx['directory']/'aggregate.csv',reference_workflow.aggregate(metrics))
    wide=metrics.pivot(index=['Gender','Season'],columns='recipe',values='brier');effects=[]
    for (g,s),r in wide.iterrows():
        for label,with_,without in [('quality_alone','anchor_quality','anchor'),('record_alone','anchor_record','anchor'),
                  ('both','anchor_both','anchor'),('quality_given_record','anchor_both','anchor_record'),
                  ('record_given_quality','anchor_both','anchor_quality')]:
            effects.append({'Gender':g,'Season':int(s),'comparison':label,'delta_brier':float(r[with_]-r[without])})
    atomic_csv(ctx['directory']/'ablations.csv',pd.DataFrame(effects))
    atomic_csv(ctx['directory']/'training_redundancy.csv',pd.DataFrame(correlations))
    candidates=metrics.loc[(metrics.recipe!='anchor')&(metrics.delta_vs_anchor<=-.001),['Gender','recipe','delta_vs_anchor']]
    atomic_json(ctx['directory']/'summary.json',{'status':'COMPLETE','phase':'2018_schedule_smoke',
        'validation_seasons':[2018],'new_matchup_candidates':7,'fixed_anchor_features':16,
        'new_classifier_fits':new,'reused_classifier_fits':reused,'total_classifier_fits':8,'new_rating_fits':0,
        'potential_replication_candidates_not_promotions':candidates.to_dict('records'),
        'automatic_feature_promotion':False,'automatic_panel_expansion':False,
        'next_step':'Review losses and add/drop effects; replicate unchanged representation across earlier-year folds only if justified',
        'current_submitted_brier':.1222672,'research_target_brier':.1097454,'new_leaderboard_score':None,
        'github_updated':False,'aws_resources_changed_by_code':False,'raw_modified':False,'repo_modified':False,
        'upstream_modified':False,'not_production_model_reproduction':True,'uses_2022_2026_targets':False,
        'limitations':['One already-consumed historical season, not an untouched test',
          'Seven hypotheses use fixed heuristic constants; no guarantee of gain',
          'Reference expectation is not calibrated, not official WAB or NET',
          'Venue factor and reference percentile are not optimized',
          'Known two tracked notebook edits remain unresolved but unexecuted and preserved'],
        'fingerprint':ctx['fingerprint']})

def report(ctx):
    from schedule_plots import make_report
    require((ctx['directory']/'summary.json').is_file(),'Evaluate before reporting')
    destination=make_report(ctx['directory'])
    # Verify input preservation BEFORE publishing the return archive.
    preservation(ctx)
    names=['summary.json','metrics.csv','aggregate.csv','ablations.csv','feature_registry.csv','training_redundancy.csv',
           'prior_decision.json','prior_replay.csv','prior_loss_groups.csv','manifest.json','preflight.json','prepare.json']
    out=ctx['kit']/'reports';out.mkdir(exist_ok=True)
    archive=out/'milestone_04_return.zip';temp=archive.with_suffix('.partial')
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
        for name in names:z.write(ctx['directory']/name,name)
    os.replace(temp,archive)
    atomic_json(out/'latest_report.json',{'html':str(destination),'return_zip':str(archive),'run_dir':str(ctx['directory'])})
    event('report_published',return_zip=str(archive),html=str(destination))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['prepare','evaluate','report'])
    ap.add_argument('--repo',type=Path,default=Path(os.getenv('MARCH_REPO',str(Path.home()/'march-machine-learning-mania-2026'))))
    ap.add_argument('--prior',type=Path,default=Path(os.getenv('MARCH_SHOOTING_KIT',str(Path.home()/'march_shooting_research'))))
    a=ap.parse_args()
    try:
        ctx=preflight(KIT,a.repo.expanduser().resolve(),a.prior.expanduser().resolve())
        globals()[a.stage](ctx)
        if a.stage!='report':preservation(ctx)
        atomic_json(KIT/'reports'/f'{a.stage}_receipt.json',{'status':'PASS','fingerprint':ctx['fingerprint'],
                    'elapsed_seconds':round(time.monotonic()-START,3)})
        event('stage_pass',stage=a.stage)
    except Exception as e:
        atomic_json(KIT/'reports/failure.json',{'status':'STOP','stage':a.stage,'exception':type(e).__name__,
                    'message':str(e),'checkpoints_preserved':True,'automatic_retry':False})
        raise

if __name__=='__main__':main()
