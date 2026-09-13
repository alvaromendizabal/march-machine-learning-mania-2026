"""Bounded women-only replication of the four unchanged record features.

Read-only input caches; no cloud clients, repository imports, pickle loading,
parameter search, promotions, external data downloads or submission generation.
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

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT / 'frozen'))
import research_workflow as wf
import shot_features as rf
import schedule_features as sf

ANCHOR = list(rf.ANCHOR_COLS)
RECORD = list(sf.RECORD_COLS)
SEASONS = [2016, 2017, 2018, 2019]
REPLICATION = [2016, 2017, 2019]
BASE_RECIPES = {'anchor': ANCHOR, 'anchor_record': ANCHOR + RECORD}
DROP_RECIPES = {'drop_' + c.removeprefix('diff_reference_'): ANCHOR + [v for v in RECORD if v != c]
                for c in RECORD}
CONFIG = {
    'round': '05-womens-record-replication', 'gender': 'W', 'seasons': SEASONS,
    'discovery_season': 2018, 'replication_seasons': REPLICATION,
    'first_training_season': 2013, 'minimum_prior_seasons': 3,
    'recipes': {**BASE_RECIPES, **DROP_RECIPES}, 'feature_parameters': sf.PARAMETERS,
    'C': 0.1, 'max_iter': 2000, 'seed': 20260911, 'threads': 2,
    'include_first_four': False, 'scale': 'Training-only RMS; mirrored game weight totals 1',
    'gate': {'mean_delta_at_most': -0.0005, 'minimum_improved_seasons': 2,
             'worst_delta_at_most': 0.003, 'discovery_season_excluded': True},
    'maximum_new_replication_fits': 5, 'maximum_new_ablation_fits': 16,
    'maximum_total_new_classifier_fits': 21, 'automatic_promotion': False,
    'scope': 'Already-consumed exploratory historical main draws; not untouched tests or leaderboard',
}
START = time.monotonic()
sha, atomic_json, atomic_csv = wf.sha, wf.atomic_json, wf.atomic_csv
require = sf.require


def event(name, **values):
    print(json.dumps({'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                      'event': name, 'elapsed_seconds': round(time.monotonic()-START, 3),
                      **values}, default=str), flush=True)


def read_json(path):
    return json.loads(Path(path).read_text())


def read_csv(path):
    return pd.read_csv(path, float_precision='round_trip')


def safe_file(root, rel):
    root = Path(root)
    rel = Path(rel)
    require(not rel.is_absolute() and '..' not in rel.parts and str(rel) not in ('', '.'), 'Unsafe relative path')
    p = root / rel
    require(p.is_file() and not p.is_symlink(), 'Missing/symlinked input: ' + str(p))
    require(not any(q.is_symlink() for q in p.parents if q != root.parent), 'Symlinked parent path')
    require(p.resolve().is_relative_to(root.resolve()), 'Input escapes root')
    return p


def verify_checkpoint(folder, required):
    folder = Path(folder)
    require(not folder.is_symlink(), 'Symlinked checkpoint')
    if not (folder / 'complete.json').exists():
        return False
    receipt = read_json(safe_file(folder, 'complete.json'))
    require(receipt.get('complete') is True, 'Incomplete checkpoint receipt')
    outputs = receipt.get('outputs', {})
    require(set(required) <= set(outputs), 'Checkpoint missing required outputs')
    for name, digest in outputs.items():
        require(Path(name).name == name, 'Unsafe checkpoint member')
        require(sha(safe_file(folder, name)) == digest, 'Corrupt checkpoint: ' + str(folder / name))
    return True


def seal(folder, names, **metadata):
    atomic_json(Path(folder) / 'complete.json', {'complete': True,
                'outputs': {n: sha(Path(folder)/n) for n in names}, **metadata})


def source_identity(kit):
    names = ['record_workflow.py', 'record_plots.py', 'run_round05.py',
             'frozen/research_workflow.py', 'frozen/shot_features.py', 'frozen/schedule_features.py']
    return {n: sha(safe_file(kit, n)) for n in names}


def environment():
    result = {n: importlib.metadata.version(n) for n in ('numpy', 'pandas', 'scipy', 'scikit-learn', 'plotly')}
    result['python'] = platform.python_version()
    return result


def preflight(kit, repo, schedule, shooting):
    kit, repo, schedule, shooting = map(lambda p: Path(p).resolve(), (kit, repo, schedule, shooting))
    for parent in (repo, schedule, shooting):
        require(not kit.is_relative_to(parent) and not parent.is_relative_to(kit), 'Keep kits beside each other')
    old_manifest = read_json(safe_file(kit, 'evidence/manifest.json'))
    for n, upstream in [('research_workflow.py','reference/research_workflow.py'),
                        ('shot_features.py','reference/shot_features.py'),
                        ('schedule_features.py','schedule_features.py')]:
        require(sha(safe_file(kit, 'frozen/'+n)) == old_manifest['source'][upstream], 'Frozen feature/learner source changed: '+n)
    require(CONFIG['C'] == wf.CONFIG['logistic_C'] and CONFIG['seed'] == wf.CONFIG['seed'], 'Learner constants changed')
    require(CONFIG['feature_parameters'] == old_manifest['config']['feature_parameters'], 'Feature constants changed')
    require(BASE_RECIPES['anchor_record'] == old_manifest['config']['recipes']['anchor_record'], 'Reference input columns changed')
    state = wf.repository_state(repo)
    require(state == read_json(kit/'evidence/preflight.json')['state'], 'Repository differs from returned report; preserve, do not reset')
    require(environment() == old_manifest['environment'], 'Environment differs from the completed experiment; do not reinstall blindly')
    raw = repo/'data/kaggle/raw'
    for n,digest in old_manifest['data'].items():
        require(sha(safe_file(raw, n)) == digest, 'Raw data differs: '+n)
    old = schedule/'private_runs'/old_manifest['fingerprint']
    ancestor = shooting/'private_runs'/old_manifest['upstream_fingerprint']
    require(old.is_dir() and ancestor.is_dir(), 'Required private cache missing; no automatic rebuild')
    require(read_json(safe_file(old, 'manifest.json')) == old_manifest, 'Prior manifest mismatch')
    # Verify the files returned by the user's actual experiment against local cached evidence.
    upstream = {}
    def remember(root, prefix, names):
        for n in names:
            upstream[prefix+'/'+n] = sha(safe_file(root, n))
    remember(old,'schedule',['manifest.json'])
    for name in ['metrics.csv','summary.json','ablations.csv','prepare.json','preflight.json']:
        require(sha(safe_file(old,name)) == sha(safe_file(kit,'evidence/'+name)), 'Returned evidence mismatch: '+name)
        remember(old,'schedule',[name])
    # Seven prior rating snapshots, six prior schedule snapshots, three mandatory existing classifiers.
    for season in range(2013,2020):
        root = ancestor/'snapshots'/f'W_{season}'
        require(verify_checkpoint(root,['teams.csv','coverage.json','opponent_exclusion_audit.csv']), 'Missing women rating snapshot')
        for name in ['teams.csv','coverage.json','opponent_exclusion_audit.csv','complete.json']:
            rel = f'snapshots/W_{season}/'+name
            require(sha(safe_file(ancestor,rel)) == old_manifest['upstream_files'][rel], 'Original snapshot identity changed')
            remember(ancestor,'shooting',[rel])
        if season <= 2018:
            root = old/'snapshots'/f'W_{season}'
            require(verify_checkpoint(root,['features.csv','audit.json']), 'Missing prior schedule snapshot')
            remember(old,'schedule',[f'snapshots/W_{season}/'+n for n in ['features.csv','audit.json','complete.json']])
    for season, recipe, root, prefix in [(2018,'anchor',old,'schedule'),(2018,'anchor_record',old,'schedule'),
                                       (2019,'anchor',ancestor,'shooting')]:
        rel = f'fits/W_{season}_{recipe}'
        require(verify_checkpoint(root/rel,['model.json','metrics.json','predictions.csv']), 'Missing reusable classifier')
        remember(root,prefix,[rel+'/'+n for n in ['model.json','metrics.json','predictions.csv','complete.json']])
        if prefix == 'shooting':
            for n in ['model.json','metrics.json','predictions.csv','complete.json']:
                require(upstream[prefix+'/'+rel+'/'+n] == old_manifest['upstream_files'][rel+'/'+n], 'Prior 2019 anchor changed')
    identity = {'config': CONFIG, 'source': source_identity(kit), 'environment': environment(),
                'data': old_manifest['data'], 'prior_fingerprint': old_manifest['fingerprint'],
                'upstream_fingerprint': old_manifest['upstream_fingerprint'], 'upstream_files': upstream,
                'evidence_sha256': {p.name: sha(p) for p in sorted((kit/'evidence').glob('*')) if p.is_file()},
                'reference_commit': old_manifest['reference_commit']}
    fingerprint = hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    directory = kit/'private_runs'/fingerprint
    directory.mkdir(parents=True,exist_ok=True)
    manifest = dict(identity,fingerprint=fingerprint)
    if (directory/'manifest.json').exists():
        require(read_json(directory/'manifest.json') == manifest, 'Existing output manifest mismatch')
    else: atomic_json(directory/'manifest.json',manifest)
    atomic_json(kit/'reports/latest_run.json',{'fingerprint':fingerprint,'run_dir':str(directory)})
    atomic_json(directory/'preflight.json',{'status':'PASS','state':state,'rating_snapshots_verified':7,
                'schedule_snapshots_verified':6,'upstream_classifiers_verified':3,'raw_files_verified':8,
                'repo_source_imported':False,'known_notebook_edits_preserved':True})
    event('preflight_pass',women_only=True,rating_snapshots=7,schedule_snapshots=6,existing_classifiers=3)
    return {'kit':kit,'repo':repo,'raw':raw,'schedule':old,'shooting':ancestor,'directory':directory,
            'identity':identity,'state':state,'fingerprint':fingerprint}


def preservation(ctx):
    require(wf.repository_state(ctx['repo']) == ctx['state'],'Repository changed during run')
    for n,digest in ctx['identity']['data'].items():
        require(sha(safe_file(ctx['raw'],n)) == digest,'Raw input changed during run')
    for rel,digest in ctx['identity']['upstream_files'].items():
        prefix,n = rel.split('/',1)
        require(sha(safe_file(ctx[prefix],n)) == digest,'Upstream cache changed during run')
    event('preservation_pass',repository=True,raw_inputs=True,upstream=True)


def prepare(ctx):
    out = ctx['directory']
    folder = out/'snapshots/W_2019'
    reused = verify_checkpoint(folder,['features.csv','audit.json'])
    if not reused:
        compact=read_csv(ctx['raw']/'WRegularSeasonCompactResults.csv')
        base=read_csv(ctx['shooting']/'snapshots/W_2019/teams.csv')
        features,games=sf.build_schedule_snapshot(compact,base,'W',2019)
        atomic_csv(folder/'features.csv',features)
        atomic_json(folder/'audit.json',{'season':2019,'gender':'W','teams':len(features),
             'regular_season_games':len(games)//2,'cutoff_day':132,'new_rating_fits':0,
             'formulas_identical_to_round04':True,'quality_columns_not_used_for_fitting':True})
        seal(folder,['features.csv','audit.json'])
    atomic_csv(out/'feature_registry.csv',sf.registry(ANCHOR).query("family != 'quality'").assign(
        new_candidate=False, status='Unchanged family under replication; no feature promoted'))
    # Construction check on historical matchups and swapped orientations before any fitting.
    pairs,y,x,flipped = matrices(ctx)
    require(set(pairs.Season)==set(range(2013,2020)), 'Missing historical season')
    atomic_json(out/'prepare.json',{'status':'COMPLETE','base_snapshots_reused':7,
            'schedule_snapshots_reused':6,'new_schedule_snapshots':int(not reused),
            'current_snapshot_checkpoint_reused':int(reused),'new_feature_definitions':0,
            'record_features_under_test':4,'new_rating_fits':0,'new_classifier_fits':0,
            'historical_matchup_rows':len(pairs),'feature_swap_error':float(np.max(np.abs(
                x[ANCHOR+RECORD].to_numpy()+flipped[ANCHOR+RECORD].to_numpy())))})
    seal(out,['prepare.json','feature_registry.csv'],scope='preparation_only')
    event('preparation_complete',new_features=0,unchanged_record_features=4,new_rating_fits=0)


def matrices(ctx):
    base = pd.concat([read_csv(ctx['shooting']/f'snapshots/W_{s}/teams.csv') for s in range(2013,2020)],ignore_index=True)
    extra = pd.concat([read_csv((ctx['schedule'] if s<2019 else ctx['directory'])/f'snapshots/W_{s}/features.csv')
                       for s in range(2013,2020)],ignore_index=True)
    labels=read_csv(ctx['raw']/'WNCAATourneyCompactResults.csv')
    pairs,y = rf.tournament_pairs(labels,'W',list(range(2013,2020)))
    x=rf.pair_features(base,pairs)
    reverse=pairs.rename(columns={'Team1ID':'Team2ID','Team2ID':'Team1ID'})
    flipped=rf.pair_features(base,reverse)
    a,b=sf.matchup_features(extra,pairs),sf.matchup_features(extra,reverse)
    x[RECORD],flipped[RECORD]=a[RECORD],b[RECORD]
    require(np.isfinite(x[ANCHOR+RECORD]).all().all(),'Nonfinite features')
    require(np.max(np.abs(x[ANCHOR+RECORD].to_numpy()+flipped[ANCHOR+RECORD].to_numpy()))<1e-12,'Feature swap failure')
    return pairs,y,x,flipped


def temporal_split(x,season):
    require(season in SEASONS,'Unsupported validation year')
    ti,vi=wf.split_indices(x,season)
    require(set(x.iloc[ti].Season)==set(range(2013,season)),'Temporal training boundary mismatch')
    require(set(x.iloc[vi].Season)=={season},'Validation boundary mismatch')
    return ti,vi


def checked_model(model,columns,season,n_train):
    require(model['columns']==columns,'Model columns differ from the frozen recipe')
    require(model['C']==.1 and model['fit_intercept'] is False,'Learner changed')
    require(model['train_seasons']==list(range(2013,season)),'Stored model training seasons differ')
    require(model['physical_train_games']==n_train,'Training game count mismatch')
    ids=model['active_indices']
    require(ids==sorted(set(ids)) and all(type(i) is int and 0<=i<len(columns) for i in ids),'Invalid model indices')
    require(len(ids)>0 and len(ids)==len(model['scales'])==len(model['coefficients']),'Model dimensions invalid')
    require(np.isfinite(model['scales']).all() and (np.asarray(model['scales'])>0).all()
            and np.isfinite(model['coefficients']).all(),'Invalid numeric model parameters')


def score_checkpoint(folder,season,recipe,columns,bundle,origin):
    require(verify_checkpoint(folder,['model.json','metrics.json','predictions.csv']),'Missing completed fit')
    pairs,y,x,flipped=bundle
    ti,vi=temporal_split(x,season)
    model=read_json(folder/'model.json');checked_model(model,columns,season,len(ti))
    p=wf.predict(model,x.iloc[vi]);r=wf.predict(model,flipped.iloc[vi])
    stored=read_csv(folder/'predictions.csv')
    require(stored[pairs.columns].reset_index(drop=True).equals(pairs.iloc[vi].reset_index(drop=True)), 'Prediction IDs/order differ')
    require(np.array_equal(stored.y.to_numpy(),y[vi]),'Prediction targets differ')
    require(np.max(np.abs(stored.probability.to_numpy()-p))<1e-12,'Saved model does not replay predictions')
    require(np.isfinite(p).all() and ((p>0)&(p<1)).all(),'Invalid predicted probabilities')
    brier=float(np.mean((p-y[vi])**2))
    metric=read_json(folder/'metrics.json')
    require(abs(metric['brier']-brier)<1e-12,'Cached Brier does not replay')
    swap=float(np.max(np.abs(p+r-1)))
    require(swap<1e-12,'Probability swap failure')
    metric={**metric,'Gender':'W','Season':season,'recipe':recipe,'games':len(vi),
            'train_games':len(ti),'train_last_season':season-1,'brier':brier,
            'log_loss':float(-np.mean(y[vi]*np.log(p)+(1-y[vi])*np.log1p(-p))),
            'feature_count':len(columns),'active_features':len(model['active_indices']),
            'source':origin,'evidence':'Exploratory historical main draw; not leaderboard',
            'swap_error':swap,'feature_swap_error':0.}
    return metric,stored,model


def obtain_fit(ctx,season,recipe,columns,bundle,old_folder=None):
    if old_folder is not None:
        return (*score_checkpoint(old_folder,season,recipe,columns,bundle,'upstream_replay'), 'upstream')
    folder=ctx['directory']/f'fits/W_{season}_{recipe}'
    if verify_checkpoint(folder,['model.json','metrics.json','predictions.csv']):
        return (*score_checkpoint(folder,season,recipe,columns,bundle,'checkpoint_replay'), 'reused')
    pairs,y,x,flipped=bundle;ti,vi=temporal_split(x,season)
    event('classifier_started',season=season,recipe=recipe)
    model=wf.fitted_model(x.iloc[ti],y[ti],columns);model['train_seasons']=list(range(2013,season))
    p=wf.predict(model,x.iloc[vi])
    require(np.isfinite(p).all() and ((p>0)&(p<1)).all(),'Invalid probability')
    pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=p;pred['squared_error']=(p-y[vi])**2
    metric={'brier':float(np.mean((p-y[vi])**2))}
    atomic_json(folder/'model.json',model);atomic_csv(folder/'predictions.csv',pred);atomic_json(folder/'metrics.json',metric)
    seal(folder,['model.json','metrics.json','predictions.csv'],fingerprint=ctx['fingerprint'])
    row,stored,model=score_checkpoint(folder,season,recipe,columns,bundle,'new_fit')
    event('classifier_saved',season=season,recipe=recipe,brier=row['brier'])
    return row,stored,model,'new'


def replication_gate(metrics):
    selected=metrics.loc[(metrics.recipe=='anchor_record')&metrics.Season.isin(REPLICATION)]
    require(len(selected)==3 and set(selected.Season)==set(REPLICATION),'Replication gate needs exactly three seasons')
    d=selected.delta_vs_anchor.to_numpy()
    require(np.isfinite(d).all(),'Invalid replication deltas')
    g=CONFIG['gate'];mean=float(d.mean());worst=float(d.max());improved=int((d<0).sum())
    passed=mean<=g['mean_delta_at_most'] and improved>=g['minimum_improved_seasons'] and worst<=g['worst_delta_at_most']
    return {'decision':'RUN_BOUNDED_ABLATIONS' if passed else 'STOP_EXPANSION',
            'proceed_to_ablation':bool(passed),'mean_delta_replication_only':mean,
            'improved_replication_seasons':improved,'replication_seasons':REPLICATION,
            'worst_replication_delta':worst,'discovery_2018_excluded':True,
            'thresholds':g,'statistical_significance_claim':False,'automatic_feature_promotion':False,
            'meaning':'Heuristic compute-allocation gate; NOT proof, final selection or significance'}


def replicate(ctx):
    require(verify_checkpoint(ctx['directory'],['prepare.json','feature_registry.csv']),'Prepare first')
    bundle=matrices(ctx);rows=[];preds=[];coefs=[];redundancy=[]
    counts={'new':0,'reused':0,'upstream':0}
    expected=read_csv(ctx['kit']/'evidence/metrics.csv')
    for season in SEASONS:
        ti,vi=temporal_split(bundle[2],season)
        correlations=bundle[2].iloc[ti][ANCHOR+RECORD].corr()
        for c in RECORD:
            corr=correlations.loc[c,ANCHOR].abs().dropna()
            redundancy.append({'Season':season,'feature':c,'max_abs_anchor_correlation':float(corr.max()) if len(corr) else 0.,
                               'most_correlated_anchor':str(corr.idxmax()) if len(corr) else '',
                               'train_last_season':season-1,'selection_changed':False})
        for recipe,columns in BASE_RECIPES.items():
            old=ctx['schedule']/f'fits/W_2018_{recipe}' if season==2018 else (
                 ctx['shooting']/'fits/W_2019_anchor' if season==2019 and recipe=='anchor' else None)
            row,pred,model,status=obtain_fit(ctx,season,recipe,columns,bundle,old)
            if season==2018:
                prior=float(expected.loc[(expected.Gender=='W')&(expected.recipe==recipe),'brier'].iloc[0])
                require(abs(row['brier']-prior)<1e-12,'Returned 2018 result mismatch')
            counts[status]+=1;require(counts['new']<=5,'Replication fit budget exceeded')
            rows.append(row);preds.append(pred.assign(recipe=recipe))
            if recipe=='anchor_record':
                coef=dict(zip([columns[i] for i in model['active_indices']],model['coefficients']))
                coefs.extend({'Season':season,'feature':c,'standardized_coefficient':coef.get(c,0.),
                              'training_supported':c in coef} for c in RECORD)
            event('replication_progress',completed=len(rows),total=8,new_fits=counts['new'],existing_fits=counts['upstream']+counts['reused'])
    metrics=pd.DataFrame(rows)
    controls=metrics.loc[metrics.recipe=='anchor',['Season','brier']].rename(columns={'brier':'anchor_brier'})
    metrics=metrics.merge(controls,on='Season',validate='many_to_one')
    metrics['delta_vs_anchor']=metrics.brier-metrics.anchor_brier
    metrics['role']=np.where(metrics.Season==2018,'discovery / selection','additional exploratory replication')
    out=ctx['directory']
    atomic_csv(out/'replication_metrics.csv',metrics);atomic_csv(out/'replication_predictions.csv',pd.concat(preds,ignore_index=True))
    atomic_csv(out/'training_redundancy.csv',pd.DataFrame(redundancy));atomic_csv(out/'record_coefficients.csv',pd.DataFrame(coefs))
    atomic_json(out/'gate.json',replication_gate(metrics))
    atomic_json(out/'replication_receipt.json',{'status':'COMPLETE','new_classifier_fits':counts['new'],
        'local_checkpoint_fits_reused':counts['reused'],'upstream_classifier_fits_replayed':counts['upstream'],
        'total_comparisons':8,'new_rating_fits':0})
    seal(out/'replication',[],metrics_sha256=sha(out/'replication_metrics.csv'),
         gate_sha256=sha(out/'gate.json'),predictions_sha256=sha(out/'replication_predictions.csv'))


def checked_replication(ctx):
    out=ctx['directory'];r=read_json(out/'replication/complete.json')
    for key,name in [('metrics_sha256','replication_metrics.csv'),('gate_sha256','gate.json'),('predictions_sha256','replication_predictions.csv')]:
        require(sha(safe_file(out,name))==r[key],'Replication output changed')
    require(read_json(out/'gate.json')==replication_gate(read_csv(out/'replication_metrics.csv')),'Gate does not match metrics')


def ablate(ctx):
    checked_replication(ctx)
    out=ctx['directory'];gate=read_json(out/'gate.json')
    columns=['Gender','Season','recipe','removed_feature','brier','delta_vs_full','delta_vs_anchor','games']
    if not gate['proceed_to_ablation']:
        atomic_csv(out/'ablation_metrics.csv',pd.DataFrame(columns=columns))
        atomic_json(out/'ablation_receipt.json',{'status':'SKIPPED_BY_GATE','new_classifier_fits':0,
                       'local_checkpoint_fits_reused':0,'reason':gate['decision']})
        event('ablations_skipped',reason=gate['decision']);return
    rows=[];counts={'new':0,'reused':0,'upstream':0};bundle=matrices(ctx)
    baselines=read_csv(out/'replication_metrics.csv').pivot(index='Season',columns='recipe',values='brier')
    for season in SEASONS:
        for recipe,cols in DROP_RECIPES.items():
            row,_,_,status=obtain_fit(ctx,season,recipe,cols,bundle)
            counts[status]+=1;require(counts['new']<=16,'Ablation fit budget exceeded')
            removed=list(set(RECORD)-set(cols));require(len(removed)==1,'Drop-one definition changed')
            rows.append({**row,'removed_feature':removed[0],
                         'delta_vs_full':row['brier']-float(baselines.loc[season,'anchor_record']),
                         'delta_vs_anchor':row['brier']-float(baselines.loc[season,'anchor'])})
            event('ablation_progress',completed=len(rows),total=16,new_fits=counts['new'])
    atomic_csv(out/'ablation_metrics.csv',pd.DataFrame(rows))
    atomic_json(out/'ablation_receipt.json',{'status':'COMPLETE','new_classifier_fits':counts['new'],
                                           'local_checkpoint_fits_reused':counts['reused'],'total_comparisons':16})


def report(ctx):
    from record_plots import make_report
    checked_replication(ctx)
    out=ctx['directory']
    require((out/'ablation_receipt.json').is_file(),'Run gated ablate stage before reporting')
    metrics=read_csv(out/'replication_metrics.csv');gate=read_json(out/'gate.json')
    records=metrics.loc[metrics.recipe=='anchor_record',['Season','delta_vs_anchor','games']]
    # Season-level sensitivity only; overlapping training sets and consumed years preclude independent-test claims.
    sensitivity=[]
    for s in SEASONS:
        subset=records.loc[records.Season!=s]
        sensitivity.append({'omitted_season':s,'remaining_mean_delta':float(subset.delta_vs_anchor.mean()),
                            'scope':'Descriptive leave-one-season-out summary; not independent resampling'})
    atomic_csv(out/'season_sensitivity.csv',pd.DataFrame(sensitivity))
    rep=read_json(out/'replication_receipt.json');abl=read_json(out/'ablation_receipt.json')
    summary={'status':'COMPLETE','phase':'womens_record_replication_and_gated_attribution','gender':'W',
             'validation_seasons':SEASONS,'replication_seasons':REPLICATION,'discovery_season':2018,
             'new_feature_definitions':0,'unchanged_record_features_tested':4,'new_rating_fits':0,
             'new_classifier_fits_this_execution':rep['new_classifier_fits']+abl['new_classifier_fits'],
             'upstream_classifier_replays':rep['upstream_classifier_fits_replayed'],
             'local_classifier_checkpoint_reuses':rep['local_checkpoint_fits_reused']+abl['local_checkpoint_fits_reused'],
             'gate':gate,'ablation_status':abl['status'],
             'all_four_seasons_mean_delta':float(records.delta_vs_anchor.mean()),
             'additional_three_seasons_mean_delta':gate['mean_delta_replication_only'],
             'automatic_feature_promotion':False,'new_leaderboard_score':None,
             'current_submitted_brier':.1222672,'research_target_brier':.1097454,
             'github_updated':False,'aws_resources_modified':False,'raw_modified':False,'upstream_modified':False,
             'uses_2020_2026_targets':False,'repository_source_imported':False,
             'notebook_edits_remain_preserved_unresolved':True,
             'next_step':('Review drop-one stability; then freeze a representation for stronger fixed-model transfer'
                          if gate['proceed_to_ablation'] else 'Do not expand this representation; inspect evidence and research a different signal'),
             'limitations':['Already-consumed historical seasons; selected after seeing 2018 result',
              'Record formulas are heuristic, not official NET/WAB or calibrated probabilities',
              'Four seasons and overlapping training sets do not support a reliable population confidence interval',
              'Drop-one effects are conditional predictive effects, not causal importance',
              'Women-only signal cannot explain or close the entire combined leaderboard gap',
              'An algorithm-control experiment, not reproduction of the final submitted model'],
             'fingerprint':ctx['fingerprint']}
    preservation(ctx)
    atomic_json(out/'summary.json',summary)
    html=make_report(out,ctx['kit']/'evidence')
    names=['summary.json','gate.json','replication_metrics.csv','replication_receipt.json','ablation_metrics.csv',
           'ablation_receipt.json','feature_registry.csv','record_coefficients.csv','training_redundancy.csv',
           'season_sensitivity.csv','prepare.json','preflight.json','manifest.json']
    reports=ctx['kit']/'reports';reports.mkdir(exist_ok=True)
    archive=reports/'milestone_05_return.zip';temporary=archive.with_suffix('.partial')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
        for n in names:z.write(out/n,n)
    os.replace(temporary,archive)
    atomic_json(reports/'latest_report.json',{'html':str(html),'return_zip':str(archive),
             'run_dir':str(out),'figures':read_json(out/'plot_manifest.json')['count']})
    event('report_complete',return_zip=str(archive),new_fits=summary['new_classifier_fits_this_execution'])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['prepare','replicate','ablate','report'])
    for name,env,default in [('repo','MARCH_REPO','march-machine-learning-mania-2026'),
                             ('schedule','MARCH_SCHEDULE_KIT','march_schedule_research'),
                             ('shooting','MARCH_SHOOTING_KIT','march_shooting_research')]:
        ap.add_argument('--'+name,type=Path,default=Path(os.getenv(env,str(Path.home()/default))))
    a=ap.parse_args()
    try:
        ctx=preflight(KIT,a.repo,a.schedule,a.shooting)
        globals()[a.stage](ctx)
        preservation(ctx)
        atomic_json(KIT/'reports'/f'{a.stage}_receipt.json',{'status':'PASS','stage':a.stage,'fingerprint':ctx['fingerprint'],
                       'elapsed_seconds':round(time.monotonic()-START,3)})
    except Exception as e:
        atomic_json(KIT/'reports/failure.json',{'status':'STOP','stage':a.stage,'exception':type(e).__name__,
                      'message':str(e),'checkpoints_preserved':True,'automatic_retry':False})
        raise

if __name__=='__main__':main()
