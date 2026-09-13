"""Round 08: fixed-set, four-season feature tests with verified reuse and no cloud calls."""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, os, platform, sys, time, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent/'frozen'))
import research_workflow as rf
import shot_features as sf
import possession_features as pf

require=sf.require
sha=rf.sha;atomic_json=rf.atomic_json;atomic_csv=rf.atomic_csv;event=rf.event
SEASONS=[2016,2017,2018,2019];SNAPSHOTS=list(range(2013,2020))
CONFIG={'round':'08-possession-accounting','validation_seasons':SEASONS,'snapshot_seasons':SNAPSHOTS,
 'genders':['M','W'],'recipes':pf.RECIPES,'parameters':pf.PARAMETERS,
 'C':.1,'max_iter':2000,'seed':20260911,'threads':2,'minimum_prior_seasons':3,
 'include_first_four':False,'new_classifier_fit_cap':25,'new_rating_fits':0,
 'primary_comparison':'anchor_both minus anchor_rates',
 'screen':{'mean_delta_at_most':-.0005,'minimum_improved_seasons':3,'worst_delta_at_most':.003},
 'scope':'Four previously-used exploratory historical seasons, not untouched tests or leaderboard',
 'automatic_promotion':False}
SOURCES=['possession_features.py','possession_workflow.py','possession_plots.py','run_round08.py',
         'frozen/shot_features.py','frozen/research_workflow.py']
FIT_FILES=['model.json','metrics.json','predictions.csv']
ORIGINS={('M',2017):('temporal','fits/M_2017_anchor'),('M',2018):('schedule','fits/M_2018_anchor'),
         ('M',2019):('shooting','fits/M_2019_anchor'),('W',2016):('record','fits/W_2016_anchor'),
         ('W',2017):('record','fits/W_2017_anchor'),('W',2018):('schedule','fits/W_2018_anchor'),
         ('W',2019):('shooting','fits/W_2019_anchor')}


def read_json(path):return json.loads(Path(path).read_text())
def read_csv(path):return pd.read_csv(path,float_precision='round_trip')
def environment():
    return {**{k:importlib.metadata.version(k) for k in ('numpy','pandas','scipy','scikit-learn','plotly')},'python':platform.python_version()}

def safe_file(root,relative):
    root=Path(root);rel=Path(relative)
    require(not rel.is_absolute() and '..' not in rel.parts,'Unsafe relative file path')
    p=root/rel
    require(p.is_file() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents),'Missing or symlinked file: '+str(p))
    return p

def output_dir(p):
    p=Path(p);require(not p.is_symlink() and not any(q.is_symlink() for q in p.parents),'Unsafe output directory')
    p.mkdir(parents=True,exist_ok=True)

def checkpoint(folder,names):
    folder=Path(folder)
    if not (folder/'complete.json').exists():return False
    c=read_json(safe_file(folder,'complete.json'))
    require(c.get('complete') is True and set(c.get('outputs',{}))==set(names),'Wrong checkpoint output scope: '+str(folder))
    for n,h in c['outputs'].items():require(sha(safe_file(folder,n))==h,'Corrupt checkpoint: '+str(folder/n))
    return True

def seal(folder,names,**kw):rf.finish_checkpoint(folder,names,**kw)

def stage_seal(out,stage,names):atomic_json(out/(stage+'_hashes.json'),{n:sha(safe_file(out,n)) for n in names})
def stage_check(out,stage,names):
    c=read_json(safe_file(out,stage+'_hashes.json'));require(set(c)==set(names),'Stage scope mismatch')
    for n,h in c.items():require(sha(safe_file(out,n))==h,'Stage artifact changed: '+n)

def expected_scores(kit):
    records={}
    for round_,filename in [('04','metrics.csv'),('05','replication_metrics.csv'),('06','metrics.csv'),('07','replication_metrics.csv')]:
        for row in read_csv(kit/'evidence'/('round'+round_)/filename).query("recipe=='anchor'").to_dict('records'):
            key=(row['Gender'],int(row['Season']))
            if key in records:require(abs(records[key]-row['brier'])<1e-14,'Inconsistent baseline evidence')
            records[key]=row['brier']
    return records


def preflight(kit,repo,shooting,schedule,record,temporal):
    locations={k:Path(p).expanduser() for k,p in locals().copy().items()}
    for k,p in locations.items():
        require(p.is_dir() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents),'Missing/unsafe '+k+' directory')
        locations[k]=p.resolve()
    allpaths=list(locations.values())
    for i,a in enumerate(allpaths):
        for b in allpaths[i+1:]:require(not a.is_relative_to(b) and not b.is_relative_to(a),'Keep kits beside each other')
    kit,repo=locations['kit'],locations['repo'];c=read_json(safe_file(kit,'constraints.json'))
    published=read_json(safe_file(kit,'MANIFEST.json'))['sha256']
    protected=SOURCES+['constraints.json']+[str(p.relative_to(kit)) for p in (kit/'evidence').rglob('*') if p.is_file()]
    for n in protected:
        require(n in published and sha(safe_file(kit,n))==published[n],'Delivered implementation or evidence changed: '+n)
    for n,h in c['frozen_sources'].items():require(sha(safe_file(kit,n))==h,'Frozen fitting code changed')
    require(environment()==c['environment'],'Environment differs from prior experiments; do not reinstall blindly')
    state=rf.repository_state(repo)
    require(state==c['state'],'Repository differs from returned evidence; preserve edits and inspect')
    raw=repo/'data/kaggle/raw'
    for n,h in c['data'].items():require(sha(safe_file(raw,n))==h,'Raw data changed: '+n)
    roots={k:locations[k]/'private_runs'/fp for k,fp in c['fingerprints'].items()}
    for k,p in roots.items():require(p.is_dir() and not p.is_symlink(),'Missing existing cache: '+k+'; no automatic rebuild')
    upstream={}
    def remember(prefix,rel):
        key=prefix+'/'+rel;digest=sha(safe_file(roots[prefix],rel))
        require(key not in c['upstream_pins'] or c['upstream_pins'][key]==digest,'Upstream hash differs: '+key)
        upstream[key]=digest
    for key,round_ in [('shooting',None),('schedule','04'),('record','05'),('temporal','06')]:
        remember(key,'manifest.json')
        manifest=read_json(roots[key]/'manifest.json')
        require(manifest['fingerprint']==c['fingerprints'][key],'Cache manifest fingerprint mismatch')
        if round_ is not None:require(sha(roots[key]/'manifest.json')==sha(kit/'evidence'/('round'+round_)/'manifest.json'),'Returned manifest mismatch')
    for g in ['M','W']:
        for s in SNAPSHOTS:
            rel=f'snapshots/{g}_{s}';names=['teams.csv','coverage.json','opponent_exclusion_audit.csv']
            require(checkpoint(roots['shooting']/rel,names),'Missing base snapshot '+rel)
            for n in names+['complete.json']:remember('shooting',rel+'/'+n)
    for prefix,rel in ORIGINS.values():
        require(checkpoint(roots[prefix]/rel,FIT_FILES),'Missing baseline classifier '+rel)
        for n in FIT_FILES+['complete.json']:remember(prefix,rel+'/'+n)
    evidence={str(p.relative_to(kit)):sha(p) for p in sorted((kit/'evidence').rglob('*')) if p.is_file()}
    identity={'config':CONFIG,'source':{n:sha(safe_file(kit,n)) for n in SOURCES},
              'constraints_sha256':sha(kit/'constraints.json'),'environment':environment(),'data':c['data'],
              'upstream_files':upstream,'evidence_sha256':evidence,'reference_commit':c['reference_commit'],
              'upstream_fingerprints':c['fingerprints']}
    fingerprint=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    out=kit/'private_runs'/fingerprint;output_dir(out);output_dir(kit/'reports')
    manifest=dict(identity,fingerprint=fingerprint)
    if (out/'manifest.json').exists():require(read_json(out/'manifest.json')==manifest,'Output manifest mismatch')
    else:atomic_json(out/'manifest.json',manifest)
    atomic_json(kit/'reports/latest_run.json',{'fingerprint':fingerprint,'run_dir':str(out)})
    atomic_json(out/'preflight.json',{'status':'PASS','state':state,'base_snapshots_verified':14,
                'reference_classifiers_verified':7,'raw_inputs_verified':len(c['data']),
                'upstream_missing':False,'repository_source_imported':False})
    event('preflight_pass',base_snapshots=14,existing_classifiers=7,new_rating_fits=0)
    return dict(kit=kit,repo=repo,raw=raw,directory=out,identity=identity,state=state,
                fingerprint=fingerprint,expected_scores=expected_scores(kit),**roots)


def preservation(ctx):
    require(rf.repository_state(ctx['repo'])==ctx['state'],'Repository changed during stage')
    require(environment()==ctx['identity']['environment'],'Environment changed during stage')
    for n,h in ctx['identity']['source'].items():require(sha(safe_file(ctx['kit'],n))==h,'Kit source changed during stage')
    require(sha(ctx['kit']/'constraints.json')==ctx['identity']['constraints_sha256'],'Constraints changed')
    for n,h in ctx['identity']['data'].items():require(sha(safe_file(ctx['raw'],n))==h,'Raw data changed during stage')
    for n,h in ctx['identity']['upstream_files'].items():
        root,rel=n.split('/',1);require(sha(safe_file(ctx[root],rel))==h,'Prior checkpoint changed during stage')
    for n,h in ctx['identity']['evidence_sha256'].items():require(sha(safe_file(ctx['kit'],n))==h,'Evidence changed')
    event('preservation_pass',repository=True,raw=True,upstream=True)


def matrices(ctx,g):
    bases=[];rates=[]
    for s in SNAPSHOTS:
        bases.append(read_csv(ctx['shooting']/f'snapshots/{g}_{s}/teams.csv'))
        folder=ctx['directory']/f'snapshots/{g}_{s}'
        require(checkpoint(folder,['rates.csv','coverage.json']),'Missing new rate snapshot')
        rates.append(read_csv(folder/'rates.csv'))
    base=pd.concat(bases,ignore_index=True);r=pd.concat(rates,ignore_index=True)
    labels=read_csv(ctx['raw']/(g+'NCAATourneyCompactResults.csv'))
    pairs,y=sf.tournament_pairs(labels,g,SNAPSHOTS)
    x,diagnostics=pf.pair_features(base,r,pairs)
    reverse,_=pf.pair_features(base,r,pairs.rename(columns={'Team1ID':'Team2ID','Team2ID':'Team1ID'}))
    require(np.max(np.abs(x[pf.ALL].to_numpy()+reverse[pf.ALL].to_numpy()))<1e-10,'Broken feature team-swap parity')
    return pairs,y,x,reverse,diagnostics


def validate_model(model,cols,season,train_count):
    require(model['columns']==cols and model['C']==CONFIG['C'] and model['fit_intercept'] is False,'Model recipe mismatch')
    require(model['physical_train_games']==train_count and model['train_seasons']==list(range(2013,season)),'Model training years mismatch')
    inds=model['active_indices'];require(len(inds)==len(set(inds)) and all(0<=i<len(cols) for i in inds),'Invalid active indices')
    require(len(inds)==len(model['coefficients'])==len(model['scales']),'Model dimension mismatch')
    require(np.isfinite(model['coefficients']).all() and np.isfinite(model['scales']).all() and (np.array(model['scales'])>0).all(),'Invalid model coefficients or scales')


def normalized_replay_metrics(metric, saved, gender, season):
    """Recompute optional diagnostics from already-verified predictions, without refitting.

    Historical checkpoints need not have stored log_loss. Missing metadata is not
    zero loss, and present-but-inconsistent metadata is an error, not an imputation.
    This function returns a new dictionary; upstream files remain byte-identical.
    """
    require({'Gender','Season','y','probability'}.issubset(saved.columns),
            'Replay diagnostic columns missing')
    require(len(saved)>0 and saved.Gender.eq(gender).all() and saved.Season.eq(season).all(),
            'Replay diagnostic population or season mismatch')
    y=saved.y.to_numpy(dtype=float);p=saved.probability.to_numpy(dtype=float)
    require(np.isfinite(y).all() and np.isin(y,[0,1]).all(), 'Invalid replay labels')
    require(np.isfinite(p).all() and ((p>0)&(p<1)).all(), 'Invalid replay probabilities')
    brier=float(np.mean((p-y)**2))
    loss=float(-np.mean(y*np.log(p)+(1-y)*np.log1p(-p)))
    require('brier' in metric and np.isfinite(float(metric['brier'])) and
            abs(float(metric['brier'])-brier)<1e-12, 'Saved Brier diagnostic mismatch')
    for name,value in [('Gender',gender),('Season',season),('games',len(saved))]:
        require(name not in metric or metric[name]==value, 'Saved diagnostic identity mismatch: '+name)
    if 'log_loss' in metric:
        require(isinstance(metric['log_loss'],(int,float)) and
                np.isfinite(metric['log_loss']) and abs(float(metric['log_loss'])-loss)<1e-10,
                'Stored log_loss differs from verified predictions')
    return dict(metric,Gender=gender,Season=season,games=len(saved),log_loss=loss,
                log_loss_source='recomputed_from_verified_predictions',
                cached_log_loss_present=('log_loss' in metric))


def replay(folder,cols,s,bundle):
    require(checkpoint(folder,FIT_FILES),'Incomplete classifier checkpoint')
    pairs,y,x,reverse,_=bundle;ti,vi=rf.split_indices(x,s)
    model=read_json(folder/'model.json');validate_model(model,cols,s,len(ti))
    p=rf.predict(model,x.iloc[vi]);q=rf.predict(model,reverse.iloc[vi]);saved=read_csv(folder/'predictions.csv')
    require(np.isfinite(p).all() and ((p>0)&(p<1)).all(),'Invalid replay probabilities')
    keys=['Gender','Season','Team1ID','Team2ID']
    require(saved[keys].reset_index(drop=True).equals(pairs.iloc[vi][keys].reset_index(drop=True)),'Saved prediction keys or order differ')
    require(np.array_equal(saved.y.to_numpy(),y[vi]),'Saved labels differ')
    require(np.max(np.abs(saved.probability.to_numpy()-p))<1e-12,'Saved prediction replay mismatch')
    metric=read_json(folder/'metrics.json')
    require(abs(float(np.mean((p-y[vi])**2))-metric['brier'])<1e-12,'Saved Brier differs from replay')
    require(np.max(np.abs(p+q-1))<1e-10,'Probability team-swap failure')
    metric=normalized_replay_metrics(metric,saved,str(pairs.iloc[vi].Gender.iloc[0]),s)
    return metric,model,saved


PREPARE_FILES=['prepare.json','coverage.csv','feature_registry.csv','prior_replay.csv']
EVAL_FILES=['metrics.csv','predictions.csv','ablations.csv','aggregate.csv','decisions.json','evaluation_receipt.json',
            'coefficients.csv','training_redundancy.csv','matchup_diagnostics.csv','summary.json']


def prepare(ctx):
    out=ctx['directory'];coverage=[];built=0;reused=0;completed=0
    for g in ['M','W']:
        detail=read_csv(ctx['raw']/(g+'RegularSeasonDetailedResults.csv'))
        for s in SNAPSHOTS:
            folder=out/f'snapshots/{g}_{s}'
            if checkpoint(folder,['rates.csv','coverage.json']):
                reused+=1;event('rate_snapshot_reused',gender=g,season=s,completed=completed+1,total=14)
            else:
                base=read_csv(ctx['shooting']/f'snapshots/{g}_{s}/teams.csv')
                rates,c=pf.build_snapshot(detail,base,g,s)
                atomic_csv(folder/'rates.csv',rates);atomic_json(folder/'coverage.json',c)
                seal(folder,['rates.csv','coverage.json']);built+=1
                event('rate_snapshot_complete',gender=g,season=s,completed=completed+1,total=14)
            coverage.append(read_json(folder/'coverage.json'));completed+=1
    replays=[]
    for g in ['M','W']:
        bundle=matrices(ctx,g)
        for s in SEASONS:
            if (g,s) not in ORIGINS:continue
            prefix,rel=ORIGINS[(g,s)];metric,_,_=replay(ctx[prefix]/rel,pf.BASE,s,bundle)
            require(abs(metric['brier']-ctx['expected_scores'][(g,s)])<1e-12,'Prior result differs from uploaded evidence')
            replays.append({'Gender':g,'Season':s,'brier':metric['brier'],'status':'VERIFIED_REPLAY','origin':prefix})
    atomic_csv(out/'prior_replay.csv',pd.DataFrame(replays));atomic_csv(out/'coverage.csv',pd.DataFrame(coverage));atomic_csv(out/'feature_registry.csv',pf.registry())
    atomic_json(out/'prepare.json',{'status':'COMPLETE','base_snapshots_reused':14,'new_rate_snapshots':built,
                'local_snapshot_reuses':reused,'new_rating_fits':0,'new_classifier_fits':0,'baseline_replays':7,
                'new_mechanistic_definitions':4,'basic_rate_controls':6,'snapshot_functions_read_tournament_labels':False,
                'tournament_labels_used_for_replay_only':True})
    preservation(ctx);stage_seal(out,'prepare',PREPARE_FILES)


def obtain(ctx,g,s,recipe,bundle,new_budget):
    cols=pf.RECIPES[recipe];pairs,y,x,reverse,_=bundle;ti,vi=rf.split_indices(x,s)
    if recipe=='anchor' and (g,s) in ORIGINS:
        prefix,rel=ORIGINS[(g,s)];m,model,pred=replay(ctx[prefix]/rel,cols,s,bundle);origin='upstream_replay'
    else:
        folder=ctx['directory']/f'fits/{g}_{s}_{recipe}'
        if checkpoint(folder,FIT_FILES):m,model,pred=replay(folder,cols,s,bundle);origin='local_checkpoint'
        else:
            require(new_budget>0,'New-fit budget exhausted before fitting')
            model=rf.fitted_model(x.iloc[ti],y[ti],cols);model['train_seasons']=list(range(2013,s))
            validate_model(model,cols,s,len(ti));p=rf.predict(model,x.iloc[vi]);q=rf.predict(model,reverse.iloc[vi])
            require(np.isfinite(p).all() and ((p>0)&(p<1)).all(),'Invalid probability')
            require(np.max(np.abs(p+q-1))<1e-10,'Probability complement violation')
            m={'Gender':g,'Season':s,'recipe':recipe,'games':len(vi),'train_games':len(ti),'train_last_season':s-1,
               'brier':float(np.mean((p-y[vi])**2)),
               'log_loss':float(-np.mean(y[vi]*np.log(p)+(1-y[vi])*np.log1p(-p))),
               'feature_count':len(cols),'active_features':len(model['active_indices']),
               'swap_error':float(np.max(np.abs(p+q-1)))}
            pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=p;pred['squared_error']=(p-y[vi])**2
            atomic_json(folder/'model.json',model);atomic_json(folder/'metrics.json',m);atomic_csv(folder/'predictions.csv',pred)
            seal(folder,FIT_FILES);origin='new_fit'
    row={k:m[k] for k in ['Gender','Season','brier','log_loss','games']}
    row.update(recipe=recipe,train_games=len(ti),train_last_season=s-1,feature_count=len(cols),active_features=len(model['active_indices']),source=origin,
               evidence=CONFIG['scope'])
    pred=pred.copy();pred['recipe']=recipe
    return row,model,pred,origin


def effects(metrics):
    require(not metrics.duplicated(['Gender','Season','recipe']).any(),'Duplicate metric key')
    wide=metrics.pivot(index=['Gender','Season'],columns='recipe',values='brier')
    require(set(wide.columns)==set(pf.RECIPES) and np.isfinite(wide.to_numpy()).all(),'Incomplete metric grid')
    rows=[]
    for (g,s),r in wide.iterrows():
        for name,full,base in [('rates_vs_anchor','anchor_rates','anchor'),('mechanism_vs_anchor','anchor_mechanism','anchor'),
                              ('both_vs_anchor','anchor_both','anchor'),('mechanism_given_rates','anchor_both','anchor_rates'),
                              ('rates_given_mechanism','anchor_both','anchor_mechanism')]:
            rows.append({'Gender':g,'Season':s,'comparison':name,'delta_brier':float(r[full]-r[base]),
                         'meaning':'negative favors inclusion; fixed input sets'})
    return pd.DataFrame(rows)


def decisions(ablation):
    results=[];threshold=CONFIG['screen']
    for g in ['M','W']:
        d=ablation.query("Gender == @g and comparison == 'mechanism_given_rates'").sort_values('Season')
        require(d.Season.tolist()==SEASONS and np.isfinite(d.delta_brier).all(),'Primary comparison incomplete')
        values=d.delta_brier.to_numpy();ok=(values.mean()<=threshold['mean_delta_at_most'] and
          np.count_nonzero(values<0)>=threshold['minimum_improved_seasons'] and values.max()<=threshold['worst_delta_at_most'])
        results.append({'Gender':g,'comparison':'mechanism_given_rates','mean_delta':float(values.mean()),
             'improved_seasons':int(np.count_nonzero(values<0)),'worst_delta':float(values.max()),
             'decision':'CONSIDER_LATER_ERA_REPLICATION' if ok else 'DO_NOT_EXPAND_AUTOMATICALLY',
             'automatic_promotion':False,'significance_claim':False,
             'reason':'Compute-allocation gate on repeatedly-used historical seasons, not production selection'})
    return results


def evaluate(ctx):
    out=ctx['directory'];stage_check(out,'prepare',PREPARE_FILES)
    rows=[];predictions=[];coeff=[];redundancy=[];diags=[];new=0;local=0;upstream=0;count=0
    for g in ['M','W']:
        bundle=matrices(ctx,g);pairs,y,x,_,diag=bundle;diags.append(diag.loc[diag.Season.isin(SEASONS)])
        for s in SEASONS:
            ti,_=rf.split_indices(x,s)
            correlation=x.iloc[ti][pf.ALL].corr()
            for f in pf.MECHANISM:
                candidates=correlation.loc[f,pf.BASE+pf.RATES].dropna()
                best=candidates.abs().idxmax() if len(candidates) else 'undefined_training_constant'
                value=float(candidates[best]) if len(candidates) else np.nan
                redundancy.append({'Gender':g,'Season':s,'feature':f,'closest_control':best,'training_correlation':value})
            for recipe in pf.RECIPES:
                row,model,pred,origin=obtain(ctx,g,s,recipe,bundle,CONFIG['new_classifier_fit_cap']-new)
                new+=origin=='new_fit';local+=origin=='local_checkpoint';upstream+=origin=='upstream_replay';count+=1
                rows.append(row);predictions.append(pred)
                for i,c in zip(model['active_indices'],model['coefficients']):
                    coeff.append({'Gender':g,'Season':s,'recipe':recipe,'feature':model['columns'][i],'standardized_coefficient':c})
                event('comparison_complete',gender=g,season=s,recipe=recipe,brier=row['brier'],source=origin,completed=count,total=32)
    metrics=pd.DataFrame(rows);anchors=metrics.query("recipe=='anchor'")[['Gender','Season','brier']].rename(columns={'brier':'anchor_brier'})
    metrics=metrics.merge(anchors,on=['Gender','Season'],validate='many_to_one');metrics['delta_vs_anchor']=metrics.brier-metrics.anchor_brier
    a=effects(metrics);d=decisions(a)
    atomic_csv(out/'metrics.csv',metrics);atomic_csv(out/'predictions.csv',pd.concat(predictions,ignore_index=True))
    atomic_csv(out/'ablations.csv',a);atomic_csv(out/'aggregate.csv',rf.aggregate(metrics));atomic_json(out/'decisions.json',{'results':d,'thresholds':CONFIG['screen']})
    atomic_csv(out/'coefficients.csv',pd.DataFrame(coeff));atomic_csv(out/'training_redundancy.csv',pd.DataFrame(redundancy));atomic_csv(out/'matchup_diagnostics.csv',pd.concat(diags,ignore_index=True))
    receipt={'new_classifier_fits':int(new),'upstream_classifier_replays':int(upstream),'local_checkpoint_reuses':int(local),'total_comparisons':32,'new_rating_fits':0}
    atomic_json(out/'evaluation_receipt.json',receipt)
    atomic_json(out/'summary.json',dict(status='COMPLETE',phase='possession_accounting',fingerprint=ctx['fingerprint'],
       **receipt,validation_seasons=SEASONS,base_snapshots_reused=14,new_mechanistic_features=4,ordinary_rate_controls=6,
       primary_comparison='anchor_both minus anchor_rates',decisions=d,current_submitted_brier=.1222672,
       research_target_brier=.1097454,new_leaderboard_score=None,github_updated=False,repository_modified=False,
       raw_modified=False,upstream_modified=False,aws_resources_modified=False,automatic_promotion=False,
       limitations=['Previously-used seasons and repeated feature searches; no untouched-test or significance claim',
          'Odds combination and possession-state approximations are hypotheses, not fitted neutral-game forecasts',
          'Box-score rebounds omit team rebounds and mix some free-throw misses; no play-by-play state model',
          'Rate controls are not new concepts to the full repository; novelty must beat rate-augmented control',
          'Simple separate-gender classifier is not the winning pooled-XGBoost/conference production recipe']))
    preservation(ctx);stage_seal(out,'evaluation',EVAL_FILES)


def report(ctx):
    from possession_plots import render
    out=ctx['directory'];stage_check(out,'evaluation',EVAL_FILES)
    html=render(out,ctx['kit']/'evidence/round07')
    preservation(ctx)
    names=['summary.json','metrics.csv','ablations.csv','aggregate.csv','decisions.json','evaluation_receipt.json',
           'coefficients.csv','training_redundancy.csv','feature_registry.csv','coverage.csv','prior_replay.csv',
           'prepare.json','preflight.json','manifest.json','prepare_hashes.json','evaluation_hashes.json']
    if (out/'cache_migration.json').is_file():names.append('cache_migration.json')
    destination=ctx['kit']/'reports/milestone_08_return.zip';partial=destination.with_suffix('.zip.partial')
    return_hashes={n:sha(safe_file(out,n)) for n in names}
    with zipfile.ZipFile(partial,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for n in names:z.write(safe_file(out,n),n)
        z.writestr('return_integrity.json',json.dumps({'sha256':return_hashes,'excluded':['raw rows','models','per-game predictions','private notebooks']},indent=2))
    os.replace(partial,destination)
    atomic_json(ctx['kit']/'reports/latest_report.json',{'return_zip':str(destination),'html':str(html),
                 'return_sha256':sha(destination),'plotly_figures':10,'status':'COMPLETE'})
    event('report_complete',return_zip=str(destination),html=str(html),plotly_figures=10)


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','evaluate','report']);args=p.parse_args()
    kit=Path(__file__).resolve().parent
    paths={'kit':kit,'repo':Path(os.environ.get('MARCH_REPO',str(Path.home()/'march-machine-learning-mania-2026')))}
    for key,default in [('shooting','march_shooting_research'),('schedule','march_schedule_research'),
                         ('record','march_record_validation'),('temporal','march_temporal_form')]:
        paths[key]=Path(os.environ.get('MARCH_'+key.upper()+'_KIT',str(Path.home()/default)))
    try:
        event('stage_start',stage=args.stage)
        ctx=preflight(**paths);globals()[args.stage](ctx)
        event('stage_complete',stage=args.stage)
    except Exception as e:
        output_dir(kit/'reports');atomic_json(kit/'reports/failure.json',{'status':'STOP','stage':args.stage,'exception':type(e).__name__,
                  'message':str(e),'completed_checkpoints_preserved':True,'instruction':'Preserve the notebook and log. Do not reset or blindly repeat.'})
        raise

if __name__=='__main__':main()
