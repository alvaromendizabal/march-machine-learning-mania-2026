"""Round 06: fixed-reference temporal-form investigation, manual CPU execution only."""
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, os, platform, sys, time, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
KIT=Path(__file__).resolve().parent
sys.path.insert(0,str(KIT/'frozen'))
import research_workflow as wf
import shot_features as sf
import form_features as ff

ANCHOR=list(sf.ANCHOR_COLS)
RECIPES={'anchor':ANCHOR,'anchor_level':ANCHOR+ff.LEVEL_COLS,
         'anchor_change':ANCHOR+ff.CHANGE_COLS,'anchor_both':ANCHOR+ff.ALL_COLS}
CONFIG={'round':'06-frozen-early-rating-form','seasons':[2017,2019],'genders':['M','W'],
    'snapshot_seasons':list(range(2013,2020)),'recipes':RECIPES,'parameters':ff.PARAMETERS,
    'C':0.1,'max_iter':2000,'seed':20260911,'threads':2,'main_draw_only':True,
    'max_new_rating_fits':14,'max_new_classifier_fits':13,'automatic_promotion':False,
    'review_rule':{'mean_delta_at_most':-0.0005,'both_seasons_improve':True},
    'scope':'Exploratory previously-used history, not independent replication or leaderboard'}
sha,atomic_json,atomic_csv=wf.sha,wf.atomic_json,wf.atomic_csv
require=sf.require
START=time.monotonic()

def event(name,**kw):
    print(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'event':name,'elapsed_seconds':round(time.monotonic()-START,3),**kw},default=str),flush=True)

def read_json(p):return json.loads(Path(p).read_text())
def read_csv(p):return pd.read_csv(p,float_precision='round_trip')

def safe_file(root,rel):
    root=Path(root);rel=Path(rel)
    require(not rel.is_absolute() and '..' not in rel.parts and str(rel) not in ('','.'),'Unsafe relative path')
    p=root/rel
    require(p.is_file() and not p.is_symlink(),'Missing or symlinked file: '+str(p))
    require(not any(q.is_symlink() for q in p.parents),'Symlinked parent path')
    require(p.resolve().is_relative_to(root.resolve()),'Input escapes root')
    return p

def verify_checkpoint(folder,names):
    folder=Path(folder)
    require(not folder.is_symlink(),'Symlinked checkpoint')
    if not (folder/'complete.json').exists():return False
    r=read_json(safe_file(folder,'complete.json'))
    require(r.get('complete') is True and set(names)<=set(r.get('outputs',{})),'Invalid checkpoint receipt')
    for n,d in r['outputs'].items():
        require(Path(n).name==n,'Unsafe checkpoint member')
        require(sha(safe_file(folder,n))==d,'Corrupt checkpoint: '+str(folder/n))
    return True

def seal(folder,names):
    atomic_json(Path(folder)/'complete.json',{'complete':True,'outputs':{n:sha(Path(folder)/n) for n in names}})

def environment():
    return dict({n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','scikit-learn','plotly']},python=platform.python_version())

def source_identity(kit):
    return {n:sha(safe_file(kit,n)) for n in ['form_features.py','form_workflow.py','form_plots.py','run_round06.py',
                                             'frozen/research_workflow.py','frozen/shot_features.py']}

def preflight(kit,repo,shooting,record):
    # Avoid resolving a symlink away before checking it.
    for p in map(Path,[kit,repo,shooting,record]):require(not p.is_symlink(),'Symlinked top-level directory')
    kit,repo,shooting,record=map(lambda p:Path(p).resolve(),[kit,repo,shooting,record])
    for parent in [repo,shooting,record]:
        require(not kit.is_relative_to(parent) and not parent.is_relative_to(kit),'Keep research kits beside each other')
    m05=read_json(safe_file(kit,'evidence/manifest.json'))
    m04=read_json(safe_file(kit,'evidence/upstream04_manifest.json'))
    require(m05['prior_fingerprint']==m04['fingerprint'] and m05['upstream_fingerprint']==m04['upstream_fingerprint'],'Broken upstream identity chain')
    require(CONFIG['C']==wf.CONFIG['logistic_C'] and CONFIG['seed']==wf.CONFIG['seed'],'Frozen learner constants changed')
    require(ANCHOR==m05['config']['recipes']['anchor'],'Frozen anchor changed')
    for n in ['research_workflow.py','shot_features.py']:
        require(sha(safe_file(kit,'frozen/'+n))==m05['source']['frozen/'+n],'Frozen reference source mismatch')
    state=wf.repository_state(repo)
    require(state==read_json(kit/'evidence/preflight.json')['state'],'Repository differs from last returned report; preserve, do not reset')
    require(environment()==m05['environment'],'Environment changed; do not reinstall blindly')
    raw=repo/'data/kaggle/raw'
    for n,d in m05['data'].items():require(sha(safe_file(raw,n))==d,'Raw input changed: '+n)
    ancestor=shooting/'private_runs'/m05['upstream_fingerprint']
    previous=record/'private_runs'/m05['fingerprint']
    require(ancestor.is_dir() and previous.is_dir(),'Prior private cache missing; no automatic rebuild')
    require(read_json(safe_file(previous,'manifest.json'))==m05,'Returned manifest does not match private cache')
    upstream={}
    def remember(root,prefix,n):upstream[prefix+'/'+n]=sha(safe_file(root,n))
    for n in ['manifest.json','summary.json','gate.json','replication_metrics.csv','replication_receipt.json','ablation_receipt.json','preflight.json']:
        require(sha(safe_file(previous,n))==sha(safe_file(kit,'evidence/'+n)),'Returned evidence differs: '+n)
        remember(previous,'record',n)
    for g in ['M','W']:
        for s in range(2013,2020):
            rel=f'snapshots/{g}_{s}'
            require(verify_checkpoint(ancestor/rel,['teams.csv','coverage.json','opponent_exclusion_audit.csv']),'Missing base snapshot')
            for n in ['teams.csv','coverage.json','opponent_exclusion_audit.csv','complete.json']:
                key=rel+'/'+n
                require(sha(safe_file(ancestor,key))==m04['upstream_files'][key],'Base snapshot differs: '+key)
                remember(ancestor,'shooting',key)
    for g,s,root,prefix in [('W',2017,previous,'record'),('M',2019,ancestor,'shooting'),('W',2019,ancestor,'shooting')]:
        rel=f'fits/{g}_{s}_anchor'
        require(verify_checkpoint(root/rel,['model.json','metrics.json','predictions.csv']),'Missing reusable reference classifier')
        for n in ['model.json','metrics.json','predictions.csv','complete.json']:
            remember(root,prefix,rel+'/'+n)
            if prefix=='shooting':require(upstream[prefix+'/'+rel+'/'+n]==m04['upstream_files'][rel+'/'+n],'Upstream classifier changed')
    identity={'config':CONFIG,'source':source_identity(kit),'environment':environment(),'data':m05['data'],
       'evidence_sha256':{p.name:sha(p) for p in sorted((kit/'evidence').iterdir()) if p.is_file()},
       'upstream_files':upstream,'upstream_fingerprint':m05['upstream_fingerprint'],
       'prior_fingerprint':m05['fingerprint'],'reference_commit':m05['reference_commit']}
    fingerprint=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    out=kit/'private_runs'/fingerprint;out.mkdir(parents=True,exist_ok=True)
    manifest=dict(identity,fingerprint=fingerprint)
    if (out/'manifest.json').exists():require(read_json(out/'manifest.json')==manifest,'Output identity mismatch')
    else:atomic_json(out/'manifest.json',manifest)
    atomic_json(kit/'reports/latest_run.json',{'fingerprint':fingerprint,'run_dir':str(out)})
    atomic_json(out/'preflight.json',{'status':'PASS','state':state,'base_snapshots_verified':14,
       'existing_classifiers_verified':3,'raw_files_verified':len(m05['data']),
       'repository_source_imported':False,'known_notebook_edits_preserved':True})
    event('preflight_pass',snapshots=14,reusable_anchor_classifiers=3)
    return {'kit':kit,'repo':repo,'raw':raw,'shooting':ancestor,'record':previous,
            'directory':out,'identity':identity,'state':state,'fingerprint':fingerprint}

def preservation(ctx):
    require(wf.repository_state(ctx['repo'])==ctx['state'],'Repository changed during execution')
    require(source_identity(ctx['kit'])==ctx['identity']['source'],'Kit source changed during execution')
    for n,d in ctx['identity']['data'].items():require(sha(safe_file(ctx['raw'],n))==d,'Raw bytes changed during execution')
    for n,d in ctx['identity']['upstream_files'].items():
        prefix,rel=n.split('/',1);require(sha(safe_file(ctx[prefix],rel))==d,'Upstream file changed during execution')
    event('preservation_pass',raw=True,upstream=True,repository=True)

def prepare(ctx):
    out=ctx['directory'];ratings_new=ratings_reused=snap_new=snap_reused=0;coverage=[]
    for g in ['M','W']:
        detailed=read_csv(ctx['raw']/(g+'RegularSeasonDetailedResults.csv'))
        for s in range(2013,2020):
            base=read_csv(ctx['shooting']/f'snapshots/{g}_{s}/teams.csv')
            eroot=out/'early_ratings'/f'{g}_{s}'
            if verify_checkpoint(eroot,['model.json']):ratings_reused+=1;early=read_json(eroot/'model.json')
            else:
                event('early_rating_started',gender=g,season=s)
                early=ff.fit_early(detailed,s);atomic_json(eroot/'model.json',early);seal(eroot,['model.json']);ratings_new+=1
            froot=out/'snapshots'/f'{g}_{s}'
            if verify_checkpoint(froot,['features.csv','coverage.json','late_residuals.csv']):snap_reused+=1
            else:
                features,games=ff.build_snapshot(detailed,base,g,s,early)
                atomic_csv(froot/'features.csv',features);atomic_csv(froot/'late_residuals.csv',games)
                audit={'Gender':g,'Season':s,'teams':len(features),'early_physical_games':early['early_physical_games'],
                   'late_physical_games':len(games)//2,'excluded_unknown_orientations':int((~games.known_early).sum()),
                   'teams_with_no_usable_late_games':int(features.late_games.eq(0).sum()),
                   'teams_missing_first_or_second_window':int((features.first_window_games.eq(0)|features.second_window_games.eq(0)).sum()),
                   'new_feature_count':4,'earliest_late_day':int(games.DayNum.min()),'latest_late_day':int(games.DayNum.max()),
                   'early_max_day':early['max_training_day'],'early_model_sha256':sha(eroot/'model.json')}
                atomic_json(froot/'coverage.json',audit);seal(froot,['features.csv','coverage.json','late_residuals.csv']);snap_new+=1
            a=read_json(froot/'coverage.json');require(a['early_model_sha256']==sha(eroot/'model.json'),'Snapshot/early model identity mismatch')
            coverage.append(a);event('form_snapshot_ready',gender=g,season=s,completed=len(coverage),total=14)
    atomic_csv(out/'coverage.csv',pd.DataFrame(coverage));atomic_csv(out/'feature_registry.csv',ff.registry(ANCHOR))
    # Fail before tournament fitting if pair construction, timing, or swaps are wrong.
    for g in ['M','W']:
        bundle=matrices(ctx,g)
        require(len(bundle[0])>0,'No historical matchups')
    atomic_json(out/'prepare.json',{'status':'COMPLETE','new_early_rating_fits':ratings_new,'early_rating_checkpoint_reuses':ratings_reused,
       'new_feature_snapshots':snap_new,'feature_snapshot_reuses':snap_reused,'base_snapshots_reused':14,
       'new_classifier_fits':0,'new_feature_definitions':4,'feature_swap_error':0.0})
    seal(out/'prepared',[])

def matrices(ctx,g):
    bases=[];forms=[]
    for s in range(2013,2020):
        root=ctx['directory']/f'snapshots/{g}_{s}'
        require(verify_checkpoint(root,['features.csv','coverage.json','late_residuals.csv']),'Run prepare first')
        bases.append(read_csv(ctx['shooting']/f'snapshots/{g}_{s}/teams.csv'));forms.append(read_csv(root/'features.csv'))
    bases=pd.concat(bases,ignore_index=True);forms=pd.concat(forms,ignore_index=True)
    pairs,y=sf.tournament_pairs(read_csv(ctx['raw']/(g+'NCAATourneyCompactResults.csv')),g,list(range(2013,2020)))
    swapped=pairs.rename(columns={'Team1ID':'Team2ID','Team2ID':'Team1ID'})
    x=sf.pair_features(bases,pairs);flipped=sf.pair_features(bases,swapped)
    for p,frame in [(pairs,x),(swapped,flipped)]:
        extra=ff.pair_features(forms,p)
        frame[ff.ALL_COLS]=extra[ff.ALL_COLS].to_numpy()
    require(np.max(np.abs(x[RECIPES['anchor_both']].to_numpy()+flipped[RECIPES['anchor_both']].to_numpy()))<1e-10,'Feature swap invariant failed')
    # Support is a data-quality diagnostic, not validation-driven feature selection.
    participating=pd.concat([pairs[['Gender','Season','Team1ID']].rename(columns={'Team1ID':'TeamID'}),
                              pairs[['Gender','Season','Team2ID']].rename(columns={'Team2ID':'TeamID'})]).drop_duplicates()
    used=participating.merge(forms,on=['Gender','Season','TeamID'],how='left',validate='one_to_one')
    require(used.early_games.gt(0).all() and used.late_games.gt(0).all(),'A tournament team has no early or late support; investigate, do not fabricate form')
    return pairs,y,x,flipped

def split(x,s):
    ti,vi=wf.split_indices(x,s)
    require(set(x.iloc[ti].Season)==set(range(2013,s)),'Unexpected tournament training seasons')
    require((x.iloc[ti].Season<s).all(),'Temporal label leak')
    return ti,vi

def checked_model(model,cols,s,n):
    require(model['columns']==cols and model['C']==CONFIG['C'] and model['fit_intercept'] is False,'Cached recipe mismatch')
    require(model['train_seasons']==list(range(2013,s)) and model['physical_train_games']==n,'Cached training split mismatch')
    ids=model['active_indices']
    require(ids==sorted(set(ids)) and all(type(i)is int and 0<=i<len(cols) for i in ids),'Invalid active indices')
    require(len(ids)>0 and len(ids)==len(model['scales'])==len(model['coefficients']),'Invalid model dimensions')
    require(np.isfinite(model['scales']).all() and np.min(model['scales'])>0 and np.isfinite(model['coefficients']).all(),'Nonfinite model')

def score_checkpoint(folder,g,s,recipe,cols,bundle,origin):
    require(verify_checkpoint(folder,['model.json','metrics.json','predictions.csv']),'No complete classifier')
    pairs,y,x,flipped=bundle;ti,vi=split(x,s)
    model=read_json(folder/'model.json');checked_model(model,cols,s,len(ti))
    train_values=x.iloc[ti][cols].to_numpy(float)
    expected_scales=np.sqrt(np.mean(np.vstack([train_values,-train_values])**2,axis=0))
    active=np.flatnonzero(expected_scales>1e-12)
    require(model['active_indices']==active.tolist(),'Training-supported inputs differ from cached model')
    require(np.allclose(np.asarray(model['scales']),expected_scales[active],rtol=1e-12,atol=1e-12),'Cached scaling differs from training-only RMS')
    p=wf.predict(model,x.iloc[vi]);p2=wf.predict(model,flipped.iloc[vi]);stored=read_csv(folder/'predictions.csv')
    require(stored[pairs.columns].reset_index(drop=True).equals(pairs.iloc[vi].reset_index(drop=True)),'Cached prediction IDs differ')
    require(np.array_equal(stored.y.to_numpy(),y[vi]) and np.max(np.abs(stored.probability.to_numpy()-p))<1e-12,'Prediction replay mismatch')
    brier=float(np.mean((p-y[vi])**2));m=read_json(folder/'metrics.json')
    require(abs(m['brier']-brier)<1e-12,'Cached Brier differs from replay')
    swap=float(np.max(np.abs(p+p2-1)));require(swap<1e-12,'Probability swap failure')
    row={'Gender':g,'Season':s,'recipe':recipe,'games':len(vi),'train_games':len(ti),
       'train_last_season':s-1,'brier':brier,'log_loss':float(-np.mean(y[vi]*np.log(np.clip(p,1e-15,1-1e-15))+(1-y[vi])*np.log(np.clip(1-p,1e-15,1-1e-15)))),
       'feature_count':len(cols),'active_features':len(model['active_indices']),'source':origin,'swap_error':swap,
       'evidence':'Previously-used exploratory historical main draw, not leaderboard'}
    return row,stored,model

def obtain_fit(ctx,g,s,recipe,cols,bundle):
    old=None
    if recipe=='anchor':
        if s==2019:old=ctx['shooting']/f'fits/{g}_{s}_anchor'
        elif g=='W' and s==2017:old=ctx['record']/f'fits/W_{s}_anchor'
    if old is not None:
        row,pred,model=score_checkpoint(old,g,s,recipe,cols,bundle,'upstream_replay')
        if g=='W' and s==2017:
            evidence=read_csv(ctx['kit']/'evidence/replication_metrics.csv')
            expected=evidence.loc[(evidence.Season==s)&(evidence.recipe=='anchor'),'brier'].iloc[0]
            require(abs(expected-row['brier'])<1e-12,'Returned 2017 baseline does not replay')
        return row,pred,model,'upstream'
    root=ctx['directory']/f'fits/{g}_{s}_{recipe}'
    if verify_checkpoint(root,['model.json','metrics.json','predictions.csv']):
        return (*score_checkpoint(root,g,s,recipe,cols,bundle,'checkpoint_replay'),'reused')
    pairs,y,x,_=bundle;ti,vi=split(x,s)
    event('classifier_started',gender=g,season=s,recipe=recipe)
    model=wf.fitted_model(x.iloc[ti],y[ti],cols);model['train_seasons']=list(range(2013,s))
    p=wf.predict(model,x.iloc[vi]);require(np.isfinite(p).all(),'Invalid classifier predictions')
    pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=p;pred['squared_error']=(p-y[vi])**2
    atomic_json(root/'model.json',model);atomic_csv(root/'predictions.csv',pred)
    atomic_json(root/'metrics.json',{'Gender':g,'Season':s,'recipe':recipe,'brier':float(np.mean((p-y[vi])**2))})
    seal(root,['model.json','metrics.json','predictions.csv'])
    return (*score_checkpoint(root,g,s,recipe,cols,bundle,'new_fit'),'new')

def review_decisions(metrics):
    rows=[]
    for g in CONFIG['genders']:
        for recipe in list(RECIPES)[1:]:
            d=metrics.loc[(metrics.Gender==g)&(metrics.recipe==recipe),'delta_vs_anchor']
            require(len(d)==2 and np.isfinite(d).all(),'Need two exploratory seasons per recipe')
            qualifies=bool(d.mean()<=-.0005 and (d<0).all())
            rows.append({'Gender':g,'recipe':recipe,'mean_delta':float(d.mean()),'worst_delta':float(d.max()),
              'improved_seasons':int((d<0).sum()),'decision':'CONSIDER_UNCHANGED_REPLICATION' if qualifies else 'DO_NOT_EXPAND_AUTOMATICALLY',
              'automatic_promotion':False,'statistical_significance_claim':False})
    return rows

def evaluate(ctx):
    require(verify_checkpoint(ctx['directory']/'prepared',[]),'Run preparation before evaluation')
    counts={'new':0,'reused':0,'upstream':0};rows=[];predictions=[];redundancy=[];coefficients=[]
    for g in CONFIG['genders']:
        bundle=matrices(ctx,g);_,_,x,_=bundle
        for s in CONFIG['seasons']:
            ti,_=split(x,s)
            for c in ff.ALL_COLS:
                training=x.iloc[ti]
                supported=[a for a in ANCHOR if training[a].std()>1e-12]
                corr=(training[supported].corrwith(training[c]).abs().dropna()
                      if supported and training[c].std()>1e-12 else pd.Series(dtype=float))
                redundancy.append({'Gender':g,'Season':s,'feature':c,'max_abs_anchor_correlation':float(corr.max()) if len(corr) else 0.,
                     'most_correlated_anchor':str(corr.idxmax()) if len(corr) else '', 'training_last_season':s-1})
            for recipe,cols in RECIPES.items():
                row,pred,model,origin=obtain_fit(ctx,g,s,recipe,cols,bundle);counts[origin]+=1
                require(counts['new']<=13,'Classifier fit budget exceeded')
                rows.append(row);predictions.append(pred.assign(recipe=recipe))
                if recipe=='anchor_both':
                    coef=dict(zip([cols[i] for i in model['active_indices']],model['coefficients']))
                    coefficients.extend({'Gender':g,'Season':s,'feature':c,'standardized_coefficient':coef.get(c,0.)} for c in ff.ALL_COLS)
                event('classifier_progress',completed=len(rows),total=16,new=counts['new'],reused=counts['reused']+counts['upstream'])
    out=ctx['directory'];metrics=pd.DataFrame(rows)
    controls=metrics.query("recipe=='anchor'")[['Gender','Season','brier']].rename(columns={'brier':'anchor_brier'})
    metrics=metrics.merge(controls,on=['Gender','Season'],validate='many_to_one');metrics['delta_vs_anchor']=metrics.brier-metrics.anchor_brier
    atomic_csv(out/'metrics.csv',metrics);atomic_csv(out/'predictions.csv',pd.concat(predictions,ignore_index=True))
    abl=[]
    for (g,s),group in metrics.groupby(['Gender','Season']):
        v=group.set_index('recipe').brier
        for family,without,with_ in [('level','anchor','anchor_level'),('change','anchor','anchor_change'),
             ('level_given_change','anchor_change','anchor_both'),('change_given_level','anchor_level','anchor_both')]:
            abl.append({'Gender':g,'Season':s,'comparison':family,'brier_delta':float(v[with_]-v[without]),
                        'meaning':'Adding named family; negative is better; fixed other columns'})
    atomic_csv(out/'ablations.csv',pd.DataFrame(abl));atomic_csv(out/'training_redundancy.csv',pd.DataFrame(redundancy))
    atomic_csv(out/'coefficients.csv',pd.DataFrame(coefficients));atomic_json(out/'decisions.json',{'decisions':review_decisions(metrics)})
    atomic_json(out/'evaluation_receipt.json',{'status':'COMPLETE','new_classifier_fits':counts['new'],
       'local_checkpoint_reuses':counts['reused'],'upstream_anchor_replays':counts['upstream'],'total_comparisons':16})
    seal(out/'evaluated',[])
    atomic_json(out/'evaluation_hashes.json',{n:sha(out/n) for n in ['metrics.csv','predictions.csv','ablations.csv','coefficients.csv','training_redundancy.csv','decisions.json','evaluation_receipt.json']})

def report(ctx):
    from form_plots import make_report
    out=ctx['directory'];require(verify_checkpoint(out/'evaluated',[]),'Run evaluation first')
    for n,d in read_json(out/'evaluation_hashes.json').items():require(sha(safe_file(out,n))==d,'Evaluation output changed: '+n)
    metrics=read_csv(out/'metrics.csv');decisions=read_json(out/'decisions.json')
    require(decisions['decisions']==review_decisions(metrics),'Decision differs from saved metrics')
    evaluation=read_json(out/'evaluation_receipt.json');prep=read_json(out/'prepare.json')
    preservation(ctx)
    summary={'status':'COMPLETE','phase':'fixed_early_rating_temporal_form','new_feature_definitions':4,
       'validation_seasons':CONFIG['seasons'],'genders':CONFIG['genders'],'new_rating_fits_this_execution':prep['new_early_rating_fits'],
       'new_classifier_fits_this_execution':evaluation['new_classifier_fits'],'upstream_anchor_replays':evaluation['upstream_anchor_replays'],
       'classifier_checkpoint_reuses':evaluation['local_checkpoint_reuses'],'early_rating_checkpoint_reuses':prep['early_rating_checkpoint_reuses'],
       'base_snapshots_reused':14,'decisions':decisions['decisions'],'automatic_feature_promotion':False,
       'prior_record_family':'Not promoted; additional-season mean delta +0.00023875434741482682; expansion stopped',
       'current_submitted_brier':.1222672,'research_target_brier':.1097454,'new_leaderboard_score':None,
       'raw_modified':False,'repository_modified':False,'upstream_modified':False,'github_updated':False,
       'aws_resources_modified':False,'fingerprint':ctx['fingerprint'],
       'limitations':['Previously-used seasons and multiple comparisons, not untouched tests',
          'Frozen early ratings can be stale; residuals are not identified true improvement or momentum',
          'Conditional family comparisons do not show causal importance',
          'Fixed logistic reference is not the final submitted production model',
          'No guarantee of leaderboard improvement; further stable replication and production transfer required']}
    atomic_json(out/'summary.json',summary);html=make_report(out,ctx['kit']/'evidence')
    names=['summary.json','metrics.csv','ablations.csv','decisions.json','evaluation_receipt.json','prepare.json',
           'preflight.json','manifest.json','feature_registry.csv','coverage.csv','training_redundancy.csv','coefficients.csv']
    target=ctx['kit']/'reports/milestone_06_return.zip';tmp=target.with_suffix('.partial')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for n in names:z.write(out/n,n)
    os.replace(tmp,target)
    atomic_json(ctx['kit']/'reports/latest_report.json',{'html':str(html),'return_zip':str(target),'run_dir':str(out),'figures':10})
    event('report_complete',return_zip=str(target))

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','evaluate','report'])
    for name,env,default in [('repo','MARCH_REPO','march-machine-learning-mania-2026'),
       ('shooting','MARCH_SHOOTING_KIT','march_shooting_research'),('record','MARCH_RECORD_KIT','march_record_validation')]:
        p.add_argument('--'+name,type=Path,default=Path(os.getenv(env,str(Path.home()/default))))
    a=p.parse_args()
    try:
        ctx=preflight(KIT,a.repo,a.shooting,a.record);globals()[a.stage](ctx);preservation(ctx)
        atomic_json(KIT/'reports'/f'{a.stage}_receipt.json',{'status':'PASS','stage':a.stage,'fingerprint':ctx['fingerprint']})
    except Exception as e:
        atomic_json(KIT/'reports/failure.json',{'status':'STOP','stage':a.stage,'exception':type(e).__name__,
            'message':str(e),'checkpoints_preserved':True,'automatic_retry':False})
        raise
if __name__=='__main__':main()
