"""Round 09: women's bracket eligibility; fixed controls, 12-fit cap, no cloud writes."""
from __future__ import annotations
import argparse, hashlib, json, os, traceback, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import bracket_features as bf
from bracket_io import (rf,sf,require,sha,event,read_json,read_csv,safe_file,output_dir,
                        atomic_json,atomic_csv,environment,checkpoint,seal,stage_seal,
                        stage_check,validate_model,replay,FIT_FILES)
SEASONS=[2016,2017,2018,2019];YEARS=list(range(2013,2020))
SOURCES=['bracket_features.py','bracket_workflow.py','bracket_io.py','bracket_plots.py','run_round09.py',
         'frozen/research_workflow.py','frozen/shot_features.py']
ORIGINS={2016:('record','fits/W_2016_anchor'),2017:('record','fits/W_2017_anchor'),
         2018:('schedule','fits/W_2018_anchor'),2019:('shooting','fits/W_2019_anchor')}
CONFIG={'round':'09-bracket-eligibility','genders':['W'],'seasons':SEASONS,'train_first_season':2013,
        'recipes':bf.RECIPES,'parameters':bf.PARAMETERS,'C':.1,'max_iter':2000,'seed':20260911,
        'threads':2,'fit_cap':12,'new_rating_fits':0,'scope':'Repeatedly-used 2016--2019 historical main draw, not leaderboard',
        'primary':'scaled_given_status','thresholds':{'mean_delta':-.0005,'improved_seasons':3,'worst_delta':.003},
        'feature_availability':'After announced bracket, before NCAA games','automatic_promotion':False}
SNAP_FILES=['matchups.csv','context.csv','coverage.json']
PREP_FILES=['prepare.json','coverage.csv','feature_registry.csv','prior_replay.csv']
EVAL_FILES=['metrics.csv','predictions.csv','ablations.csv','aggregate.csv','decisions.json','coefficients.csv',
            'training_overlap.csv','cohort_metrics.csv','support_by_fold.csv','evaluation_receipt.json','summary.json']


def preflight(kit,repo,shooting,schedule,record):
    paths={k:Path(v).expanduser() for k,v in locals().copy().items()}
    for k,p in paths.items():
        require(p.is_dir() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents),'Missing/unsafe '+k)
        paths[k]=p.resolve()
    values=list(paths.values())
    for i,a in enumerate(values):
        for b in values[i+1:]:require(not a.is_relative_to(b) and not b.is_relative_to(a),'Kits must be sibling folders')
    kit,repo=paths['kit'],paths['repo'];c=read_json(safe_file(kit,'constraints.json'))
    expected=read_json(safe_file(kit,'MANIFEST.json'))['sha256']
    required=SOURCES+['constraints.json']+[str(p.relative_to(kit)) for p in (kit/'evidence').rglob('*') if p.is_file()]
    for n in required:require(n in expected and sha(safe_file(kit,n))==expected[n],'Delivered code/evidence changed: '+n)
    for n,h in c['frozen_sources'].items():require(sha(safe_file(kit,n))==h,'Frozen fit source changed')
    require(environment()==c['environment'],'Environment differs; preserve it and report rather than reinstalling')
    state=rf.repository_state(repo);require(state==c['state'],'Repository state differs from returned evidence')
    raw=repo/'data/kaggle/raw'
    for n,h in c['data'].items():require(sha(safe_file(raw,n))==h,'Raw input changed: '+n)
    roots={k:paths[k]/'private_runs'/fp for k,fp in c['fingerprints'].items()}
    upstream={}
    def remember(key,rel):
        name=key+'/'+rel;digest=sha(safe_file(roots[key],rel))
        require(name in c['upstream_pins'] and digest==c['upstream_pins'][name],'Unpinned or changed upstream artifact: '+name)
        upstream[name]=digest
    for key in roots:remember(key,'manifest.json')
    for s in YEARS:
        rel=f'snapshots/W_{s}';names=['teams.csv','coverage.json','opponent_exclusion_audit.csv']
        require(checkpoint(roots['shooting']/rel,names),'Base snapshot missing')
        for n in names+['complete.json']:remember('shooting',rel+'/'+n)
    for key,rel in ORIGINS.values():
        require(checkpoint(roots[key]/rel,FIT_FILES),'Anchor checkpoint missing')
        for n in FIT_FILES+['complete.json']:remember(key,rel+'/'+n)
    evidence={str(p.relative_to(kit)):sha(p) for p in sorted((kit/'evidence').rglob('*')) if p.is_file()}
    identity={'config':CONFIG,'source':{n:sha(kit/n) for n in SOURCES},'constraints_sha256':sha(kit/'constraints.json'),
              'environment':environment(),'data':c['data'],'upstream_files':upstream,'evidence_sha256':evidence,
              'reference_commit':c['reference_commit'],'upstream_fingerprints':c['fingerprints']}
    fp=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();out=kit/'private_runs'/fp
    output_dir(out);output_dir(kit/'reports');m=dict(identity,fingerprint=fp)
    if (out/'manifest.json').exists():require(read_json(out/'manifest.json')==m,'Run identity mismatch')
    else:atomic_json(out/'manifest.json',m)
    atomic_json(kit/'reports/latest_run.json',{'run_dir':str(out),'fingerprint':fp})
    atomic_json(out/'preflight.json',{'status':'PASS','state':state,'base_snapshots_verified':7,'reference_models_verified':4,
                                    'raw_inputs_verified':len(c['data']),'repository_source_imported':False})
    event('preflight_pass',base_snapshots=7,reference_classifiers=4,new_rating_fits=0)
    return dict(kit=kit,repo=repo,raw=raw,directory=out,state=state,identity=identity,fingerprint=fp,**roots)


def preservation(ctx):
    require(rf.repository_state(ctx['repo'])==ctx['state'],'Repository changed during stage')
    require(environment()==ctx['identity']['environment'],'Environment changed during stage')
    for n,h in ctx['identity']['source'].items():require(sha(safe_file(ctx['kit'],n))==h,'Kit source changed')
    require(sha(ctx['kit']/'constraints.json')==ctx['identity']['constraints_sha256'],'Constraints changed')
    for n,h in ctx['identity']['data'].items():require(sha(safe_file(ctx['raw'],n))==h,'Raw input changed')
    for n,h in ctx['identity']['upstream_files'].items():
        k,r=n.split('/',1);require(sha(safe_file(ctx[k],r))==h,'Upstream file changed')
    for n,h in ctx['identity']['evidence_sha256'].items():require(sha(safe_file(ctx['kit'],n))==h,'Evidence changed')
    event('preservation_pass',repository=True,raw=True,upstream=True)


def matrices(ctx):
    xs=[];ds=[]
    for s in YEARS:
        folder=ctx['directory']/f'snapshots/W_{s}'
        require(checkpoint(folder,SNAP_FILES),'Incomplete new bracket table')
        xs.append(read_csv(folder/'matchups.csv'));ds.append(read_csv(folder/'context.csv'))
    allx=pd.concat(xs,ignore_index=True);alld=pd.concat(ds,ignore_index=True)
    labels=read_csv(ctx['raw']/'WNCAATourneyCompactResults.csv')
    pairs,y=sf.tournament_pairs(labels,'W',YEARS)
    x=pairs.merge(allx,on=bf.KEYS,how='left',validate='one_to_one')
    d=pairs.merge(alld,on=bf.KEYS,how='left',validate='one_to_one')
    require(len(x)==len(pairs) and np.isfinite(x[bf.ALL].to_numpy()).all(),'Missing features for target matchup')
    reverse=x.copy();reverse[bf.ALL]=-reverse[bf.ALL]
    return pairs,y,x,reverse,d


def prepare(ctx):
    out=ctx['directory'];seeds=read_csv(ctx['raw']/'WNCAATourneySeeds.csv');built=0;reused=0;coverage=[]
    for s in YEARS:
        folder=out/f'snapshots/W_{s}'
        if checkpoint(folder,SNAP_FILES):reused+=1;origin='checkpoint'
        else:
            base=read_csv(ctx['shooting']/f'snapshots/W_{s}/teams.csv')
            x,d,c=bf.build_season(base,seeds,s)
            atomic_csv(folder/'matchups.csv',x);atomic_csv(folder/'context.csv',d);atomic_json(folder/'coverage.json',c)
            seal(folder,SNAP_FILES);built+=1;origin='new_aggregation'
        coverage.append(read_json(folder/'coverage.json'));event('bracket_table_complete',season=s,source=origin,completed=s-2012,total=7)
    bundle=matrices(ctx);records=[]
    scores=read_csv(ctx['kit']/'evidence/round08/metrics.csv').query("Gender=='W' and recipe=='anchor'").set_index('Season').brier.to_dict()
    for s in SEASONS:
        root,rel=ORIGINS[s];metric,_,_=replay(ctx[root]/rel,bf.BASE,s,bundle)
        require(s in scores and abs(scores[s]-metric['brier'])<1e-12,'Replay differs from returned score')
        records.append({'Gender':'W','Season':s,'brier':metric['brier'],'status':'VERIFIED_REPLAY','origin':root})
    atomic_csv(out/'prior_replay.csv',pd.DataFrame(records));atomic_csv(out/'coverage.csv',pd.DataFrame(coverage));atomic_csv(out/'feature_registry.csv',bf.registry())
    atomic_json(out/'prepare.json',{'status':'COMPLETE','base_snapshots_reused':7,'new_bracket_tables':built,'bracket_table_reuses':reused,
        'all_pairs_per_season':2016,'new_rating_fits':0,'new_classifier_fits':0,'baseline_replays':4,
        'new_candidate_features':2,'seed_status_controls':1,'tournament_labels_read_by_feature_builder':False,'actual_venue_measured':False})
    preservation(ctx);stage_seal(out,'prepare',PREP_FILES)


def obtain(ctx,season,recipe,bundle,budget):
    cols=bf.RECIPES[recipe];pairs,y,x,rev,_=bundle;ti,vi=rf.split_indices(x,season)
    if recipe=='anchor':
        root,rel=ORIGINS[season];metric,model,pred=replay(ctx[root]/rel,cols,season,bundle);origin='upstream_replay'
    else:
        folder=ctx['directory']/f'fits/W_{season}_{recipe}'
        if checkpoint(folder,FIT_FILES):metric,model,pred=replay(folder,cols,season,bundle);origin='local_checkpoint'
        else:
            require(budget>0,'Fit budget exhausted before fitting')
            model=rf.fitted_model(x.iloc[ti],y[ti],cols);model['train_seasons']=list(range(2013,season))
            validate_model(model,cols,season,len(ti));p=rf.predict(model,x.iloc[vi]);q=rf.predict(model,rev.iloc[vi])
            require(np.isfinite(p).all() and ((p>0)&(p<1)).all() and np.max(abs(p+q-1))<1e-10,'Invalid/complement-inconsistent predictions')
            metric={'Gender':'W','Season':season,'recipe':recipe,'games':len(vi),'brier':float(np.mean((p-y[vi])**2)),
                    'log_loss':float(-np.mean(y[vi]*np.log(p)+(1-y[vi])*np.log1p(-p)))}
            pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=p;pred['squared_error']=(p-y[vi])**2
            atomic_json(folder/'model.json',model);atomic_json(folder/'metrics.json',metric);atomic_csv(folder/'predictions.csv',pred);seal(folder,FIT_FILES);origin='new_fit'
    row={k:metric[k] for k in ['Gender','Season','games','brier','log_loss']}
    row.update(recipe=recipe,train_games=len(ti),train_last_season=season-1,feature_count=len(cols),active_features=len(model['active_indices']),source=origin,evidence=CONFIG['scope'])
    pred=pred.copy();pred['recipe']=recipe
    pred['squared_error']=(pred.probability-pred.y)**2
    return row,model,pred,origin


def effects(metrics):
    require(not metrics.duplicated(['Season','recipe']).any(),'Duplicate result')
    wide=metrics.pivot(index='Season',columns='recipe',values='brier')
    require(wide.index.tolist()==SEASONS and set(wide.columns)==set(bf.RECIPES) and np.isfinite(wide.to_numpy()).all(),'Incomplete metric grid')
    return pd.DataFrame([{'Gender':'W','Season':int(s),'comparison':name,'delta_brier':float(r[a]-r[b])}
            for s,r in wide.iterrows() for name,a,b in [
                ('status_vs_anchor','seed_status','anchor'),('host_given_status','host_context','seed_status'),
                ('scaled_given_status','host_context_scaled','seed_status'),('scaling_given_host','host_context_scaled','host_context')]])


def decision(eff):
    d=eff.loc[eff.comparison.eq(CONFIG['primary'])].sort_values('Season')
    require(d.Season.tolist()==SEASONS and np.isfinite(d.delta_brier).all(),'Incomplete primary comparison')
    v=d.delta_brier.to_numpy();t=CONFIG['thresholds'];ok=v.mean()<=t['mean_delta'] and (v<0).sum()>=t['improved_seasons'] and v.max()<=t['worst_delta']
    return {'Gender':'W','comparison':CONFIG['primary'],'mean_delta':float(v.mean()),'worst_delta':float(v.max()),
            'improved_seasons':int((v<0).sum()),'decision':'CONSIDER_CONFIRMED_VENUE_REPLICATION' if ok else 'DO_NOT_EXPAND_AUTOMATICALLY',
            'thresholds':t,'automatic_promotion':False,'actual_home_advantage_proven':False,'significance_claim':False}


def evaluate(ctx):
    out=ctx['directory'];stage_check(out,'prepare',PREP_FILES);bundle=matrices(ctx);pairs,y,x,_,diag=bundle
    rows=[];predictions=[];coeff=[];overlap=[];support=[];new=0;reuse=0;up=0
    for s in SEASONS:
        ti,vi=rf.split_indices(x,s);corr=x.iloc[ti][bf.ALL].corr()
        support.append({'Season':s,'train_games':len(ti),'validation_games':len(vi),
                        'policy_training_seasons':int(x.iloc[ti].loc[x.iloc[ti].Season.ge(2015),'Season'].nunique()),
                        'eligible_train_games':int(x.iloc[ti][bf.HOST[0]].ne(0).sum()),'eligible_validation_games':int(x.iloc[vi][bf.HOST[0]].ne(0).sum())})
        for f in bf.HOST+bf.SCALED:
            r=corr.loc[f,bf.BASE+bf.STATUS].dropna();name=r.abs().idxmax() if len(r) else 'training_constant'
            overlap.append({'Season':s,'feature':f,'closest_control':name,'training_correlation':float(r[name]) if len(r) else np.nan})
        for recipe in bf.RECIPES:
            row,model,pred,origin=obtain(ctx,s,recipe,bundle,CONFIG['fit_cap']-new)
            new+=origin=='new_fit';reuse+=origin=='local_checkpoint';up+=origin=='upstream_replay';rows.append(row);predictions.append(pred)
            for i,c in zip(model['active_indices'],model['coefficients']):coeff.append({'Season':s,'recipe':recipe,'feature':model['columns'][i],'standardized_coefficient':c})
            event('comparison_complete',season=s,recipe=recipe,brier=row['brier'],source=origin,completed=len(rows),total=16)
    metrics=pd.DataFrame(rows);anchors=metrics.query("recipe=='anchor'")[['Season','brier']].rename(columns={'brier':'anchor_brier'})
    metrics=metrics.merge(anchors,on='Season',validate='many_to_one');metrics['delta_vs_anchor']=metrics.brier-metrics.anchor_brier
    pred=pd.concat(predictions,ignore_index=True);e=effects(metrics);d=decision(e)
    cohorts=pred.merge(diag[bf.KEYS+['cohort']],on=bf.KEYS,how='left',validate='many_to_one')
    cm=cohorts.groupby(['Season','recipe','cohort']).agg(games=('y','size'),brier=('squared_error','mean')).reset_index()
    aggregate=metrics.groupby('recipe',sort=False).agg(seasons=('Season','nunique'),games=('games','sum'),mean_brier=('brier','mean'),mean_delta=('delta_vs_anchor','mean')).reset_index()
    receipt={'new_classifier_fits':int(new),'upstream_replays':int(up),'local_reuses':int(reuse),'total_comparisons':16,'new_rating_fits':0}
    for n,f in [('metrics.csv',metrics),('predictions.csv',pred),('ablations.csv',e),('aggregate.csv',aggregate),
                ('coefficients.csv',pd.DataFrame(coeff)),('training_overlap.csv',pd.DataFrame(overlap)),('cohort_metrics.csv',cm),('support_by_fold.csv',pd.DataFrame(support))]:atomic_csv(out/n,f)
    atomic_json(out/'decisions.json',d);atomic_json(out/'evaluation_receipt.json',receipt)
    atomic_json(out/'summary.json',dict(status='COMPLETE',phase='women_bracket_context',fingerprint=ctx['fingerprint'],**receipt,
       new_candidates=2,seed_status_control=1,decision=d,current_submitted_brier=.1222672,research_target_brier=.1097454,new_leaderboard_score=None,
       github_updated=False,aws_resources_modified=False,repository_modified=False,raw_modified=False,upstream_modified=False,
       limitations=['Repeatedly-used 2016--2019 seasons; no untouched-test claim','Seed-derived eligibility is not verified venue/home status',
                    'No pre2015 home advantage is encoded; 2016 fit has only 2015 policy-era training',
                    'Documented venue exceptions are not selectively patched; archived venue validation remains open',
                    'Pure features conditional on announced bracket; unsupported play-ins/later years stop',
                    'Fixed compact logistic is not the best submitted production model']))
    preservation(ctx);stage_seal(out,'evaluation',EVAL_FILES)


def report(ctx):
    from bracket_plots import render
    out=ctx['directory'];stage_check(out,'evaluation',EVAL_FILES);stage_check(out,'prepare',PREP_FILES)
    html=render(out,ctx['kit']/'evidence/round08');preservation(ctx)
    names=[n for n in EVAL_FILES if n!='predictions.csv']+PREP_FILES+['preflight.json','manifest.json','prepare_hashes.json','evaluation_hashes.json']
    dest=ctx['kit']/'reports/milestone_09_return.zip';partial=dest.with_suffix('.zip.partial')
    require(not dest.is_symlink() and not partial.is_symlink(),'Unsafe return path')
    with zipfile.ZipFile(partial,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for n in names:z.write(safe_file(out,n),n)
        z.writestr('return_integrity.json',json.dumps({'sha256':{n:sha(out/n) for n in names},'excluded':['raw','models','game-level predictions','private notebooks']},indent=2))
    os.replace(partial,dest)
    atomic_json(ctx['kit']/'reports/latest_report.json',{'status':'COMPLETE','return_zip':str(dest),'html':str(html),'plotly_figures':10,'return_sha256':sha(dest)})
    event('report_complete',return_zip=str(dest),plotly_figures=10)


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','evaluate','report']);args=p.parse_args()
    kit=Path(__file__).resolve().parent;home=Path.home()
    paths={'kit':kit,'repo':Path(os.environ.get('MARCH_REPO',str(home/'march-machine-learning-mania-2026'))),
           **{k:Path(os.environ.get('MARCH_'+k.upper()+'_KIT',str(home/name))) for k,name in
              [('shooting','march_shooting_research'),('schedule','march_schedule_research'),('record','march_record_validation')]}}
    event('stage_start',stage=args.stage)
    try:
        ctx=preflight(**paths);globals()[args.stage](ctx);event('stage_complete',stage=args.stage)
    except Exception as e:
        output_dir(kit/'reports');atomic_json(kit/'reports/failure.json',{'status':'STOP','stage':args.stage,'error_type':type(e).__name__,'error':str(e),'completed_checkpoints_preserved':True})
        raise
if __name__=='__main__':main()
