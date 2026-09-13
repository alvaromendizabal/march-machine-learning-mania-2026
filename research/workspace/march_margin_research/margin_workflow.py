"""Milestone 11: two margin feature hypotheses, frozen tournament classifier."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import margin_features as wf
from research_io import (rf, sf, require, sha, event, read_json, read_csv, safe_file,
    output_dir, atomic_json, atomic_csv, environment, checkpoint, seal, stage_seal,
    stage_check, validate_model, replay, FIT_FILES)

SEASONS = [2016, 2017, 2018, 2019]
YEARS = list(range(2013, 2020))
ORIGINS = {2016: ('possession', 'fits/M_2016_anchor'),
           2017: ('temporal', 'fits/M_2017_anchor'),
           2018: ('schedule', 'fits/M_2018_anchor'),
           2019: ('shooting', 'fits/M_2019_anchor')}
SOURCES = ['margin_features.py', 'margin_workflow.py', 'research_io.py',
           'margin_plots.py', 'run_round11.py',
           'frozen/research_workflow.py', 'frozen/shot_features.py']
CONFIG = {'round':'11-men-margin-robustness', 'genders':['M'], 'seasons':SEASONS,
    'train_first_season':2013,'recipes':wf.RECIPES,'parameters':wf.PARAMETERS,
    'C':.1,'threads':2,'fit_cap':12,'rating_fit_cap':14,
    'primary':'huber_given_anchor','secondary':'compression_given_huber',
    'thresholds':{'mean_delta':-.0005,'improved_seasons':3,'worst_delta':.003},
    'scope':'Repeatedly used 2016–2019 historical main draw; NOT untouched test or leaderboard',
    'automatic_promotion':False}
RATING_FILES = ['rating_model.json','iterations.csv']
PAIR_FILES = ['matchups.csv','team_profiles.csv','support.json']
PREP_FILES = ['prepare.json','coverage.csv','feature_registry.csv','prior_replay.csv',
              'rating_diagnostics.csv','team_profiles.csv','optimization_trace.csv','prior_results_check.json']
EVAL_FILES = ['metrics.csv','predictions.csv','ablations.csv','aggregate.csv','decisions.json',
    'coefficients.csv','training_overlap.csv','calibration.csv','evaluation_receipt.json','summary.json']


def read_previous_report(path, expected_sha):
    """Read only the bounded, digest-pinned scientific archive; never execute a pickle."""
    require(sha(path)==expected_sha,'Prior scientific report changed/missing; preserve and report it, do not retrain')
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        require(len(names)==len(set(names)) and len(names)<=80,'Duplicate/excess archive entries')
        for item in z.infolist():
            p=Path(item.filename)
            require(not p.is_absolute() and '..' not in p.parts and item.file_size<=10_000_000,'Unsafe archive entry')
        require(sum(i.file_size for i in z.infolist())<=30_000_000,'Oversized report')
        integrity=json.loads(z.read('return_integrity.json'))['sha256']
        require(set(names)==set(integrity)|{'return_integrity.json'},'Prior archive integrity scope mismatch')
        for n,h in integrity.items():require(hashlib.sha256(z.read(n)).hexdigest()==h,'Prior archive checksum mismatch')
        import io
        metrics=pd.read_csv(io.BytesIO(z.read('metrics.csv')),float_precision='round_trip')
        require(len(metrics)==12 and not metrics.duplicated(['Season','recipe']).any(),'Previous comparison grid invalid')
        require(set(metrics.Season)==set(SEASONS) and set(metrics.recipe)=={'anchor','anchor_bt','anchor_bt_uncertainty'},'Unexpected previous experiment')
        require(metrics.Gender.eq('M').all() and np.isfinite(metrics.brier).all(),'Invalid prior metrics')
        if 'source' in metrics:require(metrics.source.isin(['new_fit','upstream_replay','local_checkpoint']).all(),'Unexpected provenance')
        return metrics, json.loads(z.read('decisions.json')), integrity


def preflight(kit, repo, shooting, schedule, temporal, possession, win_strength):
    paths = {k: Path(v).expanduser() for k, v in locals().copy().items()}
    for k, p in paths.items():
        require(p.is_dir() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents), 'Missing/unsafe ' + k)
        paths[k] = p.resolve()
    values = list(paths.values())
    for i, a in enumerate(values):
        for b in values[i+1:]:
            require(not a.is_relative_to(b) and not b.is_relative_to(a), 'Kits must be sibling folders')
    kit, repo = paths['kit'], paths['repo']; c = read_json(safe_file(kit, 'constraints.json'))
    expected = read_json(safe_file(kit, 'MANIFEST.json'))['sha256']
    protected = SOURCES + ['constraints.json'] + [str(p.relative_to(kit)) for p in (kit/'evidence').rglob('*') if p.is_file()]
    for n in protected:
        require(n in expected and sha(safe_file(kit, n)) == expected[n], 'Delivered source/evidence changed: ' + n)
    for n, h in c['frozen_sources'].items(): require(sha(safe_file(kit, n)) == h, 'Frozen fitting source changed')
    require(environment() == c['environment'], 'Environment differs; preserve it and report rather than reinstall')
    state = rf.repository_state(repo)
    require(state == c['state'], 'Repository state differs from returned evidence; do not reset it')
    raw = repo/'data/kaggle/raw'
    for n, h in c['data'].items(): require(sha(safe_file(raw, n)) == h, 'Raw input changed: ' + n)
    roots = {k: paths[k]/'private_runs'/fp for k, fp in c['fingerprints'].items()}
    upstream = {}
    def remember(key, rel):
        name = key + '/' + rel; digest = sha(safe_file(roots[key], rel))
        require(name in c['upstream_pins'] and digest == c['upstream_pins'][name], 'Unpinned/changed upstream file: ' + name)
        upstream[name] = digest
    for k in roots:
        remember(k, 'manifest.json')
        require(read_json(roots[k]/'manifest.json')['fingerprint'] == c['fingerprints'][k], 'Upstream fingerprint mismatch')
    for s in YEARS:
        rel = f'snapshots/M_{s}'; names = ['teams.csv', 'coverage.json', 'opponent_exclusion_audit.csv']
        require(checkpoint(roots['shooting']/rel, names), 'Missing base snapshot: ' + rel)
        for n in names + ['complete.json']: remember('shooting', rel + '/' + n)
    for k, rel in ORIGINS.values():
        require(checkpoint(roots[k]/rel, FIT_FILES), 'Missing reference model: ' + rel)
        for n in FIT_FILES + ['complete.json']: remember(k, rel + '/' + n)
    prior_zip = safe_file(paths['win_strength'], 'reports/milestone_10_return.zip')
    prior_metrics, prior_decisions, prior_hashes = read_previous_report(prior_zip, c['previous_report_sha256'])
    observed = read_csv(kit/'evidence/round10/log_metrics.csv')
    left=prior_metrics.set_index(['Season','recipe']).sort_index().brier
    right=observed.set_index(['Season','recipe']).sort_index().brier
    require(left.index.equals(right.index) and np.max(abs(left.to_numpy()-right.to_numpy()))<1e-12,'Scientific scores differ from recovery log')
    evidence = {str(p.relative_to(kit)): sha(p) for p in sorted((kit/'evidence').rglob('*')) if p.is_file()}
    identity = {'config': CONFIG, 'source': {n: sha(kit/n) for n in SOURCES},
        'constraints_sha256': sha(kit/'constraints.json'), 'environment': environment(),
        'data': c['data'], 'upstream_files': upstream, 'evidence_sha256': evidence,
        'reference_commit': c['reference_commit'], 'upstream_fingerprints': c['fingerprints'],
        'prior_report_sha256': c['previous_report_sha256']}
    fp = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    out = kit/'private_runs'/fp; output_dir(out); output_dir(kit/'reports')
    require(shutil.disk_usage(out).free >= 128 * 1024**2, 'Under 128 MiB free; stop before fitting')
    m = dict(identity, fingerprint=fp)
    if (out/'manifest.json').exists(): require(read_json(out/'manifest.json') == m, 'Run identity mismatch')
    else: atomic_json(out/'manifest.json', m)
    atomic_json(kit/'reports/latest_run.json', {'run_dir': str(out), 'fingerprint': fp})
    atomic_json(out/'preflight.json', {'status': 'PASS', 'state': state, 'base_snapshots_verified': 7,
        'reference_models_verified': 4, 'raw_inputs_verified': len(c['data']), 'repository_source_imported': False})
    event('preflight_pass', base_snapshots=7, reference_classifiers=4, rating_fit_cap=14, prior_report_verified=True)
    return dict(kit=kit, repo=repo, raw=raw, directory=out, state=state, identity=identity, fingerprint=fp,
        prior_zip=prior_zip, prior_metrics=prior_metrics, prior_decisions=prior_decisions, **roots)


def preservation(ctx):
    require(rf.repository_state(ctx['repo']) == ctx['state'], 'Repository changed during stage')
    require(environment() == ctx['identity']['environment'], 'Environment changed during stage')
    for n, h in ctx['identity']['source'].items(): require(sha(safe_file(ctx['kit'], n)) == h, 'Kit code changed')
    require(sha(ctx['kit']/'constraints.json') == ctx['identity']['constraints_sha256'], 'Constraints changed')
    for n, h in ctx['identity']['data'].items(): require(sha(safe_file(ctx['raw'], n)) == h, 'Raw input changed')
    for n, h in ctx['identity']['upstream_files'].items():
        k, r = n.split('/', 1); require(sha(safe_file(ctx[k], r)) == h, 'Upstream artifact changed')
    for n, h in ctx['identity']['evidence_sha256'].items(): require(sha(safe_file(ctx['kit'], n)) == h, 'Evidence changed')
    require(sha(ctx['prior_zip'])==ctx['identity']['prior_report_sha256'],'Prior report changed during stage')
    event('preservation_pass', repository=True, raw=True, upstream=True)


def matrices(ctx):
    tables = []
    for s in YEARS:
        folder = ctx['directory']/f'snapshots/M_{s}'
        require(checkpoint(folder, PAIR_FILES), 'Incomplete new matchup table')
        tables.append(read_csv(folder/'matchups.csv'))
    allx = pd.concat(tables, ignore_index=True)
    labels = read_csv(ctx['raw']/'MNCAATourneyCompactResults.csv')
    pairs, y = sf.tournament_pairs(labels, 'M', YEARS)
    x = pairs.merge(allx, on=wf.KEYS, how='left', validate='one_to_one')
    require(len(x) == len(pairs) and np.isfinite(x[wf.ALL].to_numpy()).all(), 'Missing matchup features')
    reverse = x.copy(); reverse[wf.ALL] = -reverse[wf.ALL]
    return pairs, y, x, reverse, None


def prepare(ctx):
    out=ctx['directory']; raw=read_csv(ctx['raw']/'MRegularSeasonCompactResults.csv')
    new=0;reuse=0;built=0;pair_reuse=0;coverage=[];diagnostics=[];profiles=[];traces=[]
    for season in YEARS:
        models={}
        for kind in ['huber','compressed']:
            folder=out/f'ratings/M_{season}_{kind}'
            if checkpoint(folder,RATING_FILES):reuse+=1
            else:
                require(new<CONFIG['rating_fit_cap'],'Rating budget exhausted')
                event('rating_started',season=season,kind=kind,completed=new+reuse,total=14)
                model,trace=wf.fit_rating(raw,season,kind)
                atomic_json(folder/'rating_model.json',model);atomic_csv(folder/'iterations.csv',trace)
                seal(folder,RATING_FILES);new+=1
            model=read_json(folder/'rating_model.json');models[kind]=model
            diagnostics.append(model['diagnostics'])
            trace=read_csv(folder/'iterations.csv');trace['Season']=season;trace['kind']=kind;traces.append(trace)
        base=read_csv(ctx['shooting']/f'snapshots/M_{season}/teams.csv')
        folder=out/f'snapshots/M_{season}'
        if checkpoint(folder,PAIR_FILES):pair_reuse+=1
        else:
            pairs,profile,support=wf.build_matchups(base,models)
            atomic_csv(folder/'matchups.csv',pairs);atomic_csv(folder/'team_profiles.csv',profile)
            atomic_json(folder/'support.json',support);seal(folder,PAIR_FILES);built+=1
        profiles.append(read_csv(folder/'team_profiles.csv'));coverage.append(read_json(folder/'support.json'))
        event('season_features_complete',season=season,new_rating_fits=new,rating_reuses=reuse,completed=season-2012,total=7)
    bundle=matrices(ctx);records=[]
    scores=ctx['prior_metrics'].query("recipe=='anchor'").set_index('Season').brier.to_dict()
    for season in SEASONS:
        root,rel=ORIGINS[season];metric,_,_=replay(ctx[root]/rel,wf.BASE,season,bundle)
        require(abs(scores[season]-metric['brier'])<1e-12,'Reference Brier differs from previous completed experiment')
        records.append({'Gender':'M','Season':season,'brier':metric['brier'],'status':'VERIFIED_REPLAY'})
    for n,f in [('coverage.csv',pd.DataFrame(coverage)),('feature_registry.csv',wf.registry()),
        ('prior_replay.csv',pd.DataFrame(records)),('rating_diagnostics.csv',pd.DataFrame(diagnostics)),
        ('team_profiles.csv',pd.concat(profiles,ignore_index=True)),('optimization_trace.csv',pd.concat(traces,ignore_index=True))]:atomic_csv(out/n,f)
    atomic_json(out/'prior_results_check.json',{'status':'VERIFIED','full_scientific_report_sha256':ctx['identity']['prior_report_sha256'],
         'logged_scores_reproduced':12,'decisions':ctx['prior_decisions'],'new_models_fitted_for_review':0})
    atomic_json(out/'prepare.json',{'status':'COMPLETE','base_snapshots_reused':7,'reference_replays':4,
        'new_rating_fits':new,'rating_reuses':reuse,'new_matchup_tables':built,'matchup_table_reuses':pair_reuse,
        'new_candidate_features':2,'new_tournament_classifier_fits':0,'tournament_outcomes_used_for_feature_building':False})
    preservation(ctx);stage_seal(out,'prepare',PREP_FILES)


def obtain(ctx, season, recipe, bundle, budget):
    cols = wf.RECIPES[recipe]; pairs, y, x, rev, _ = bundle; ti, vi = rf.split_indices(x, season)
    if recipe == 'anchor':
        root, rel = ORIGINS[season]; metric, model, pred = replay(ctx[root]/rel, cols, season, bundle); origin='upstream_replay'
    else:
        folder = ctx['directory']/f'fits/M_{season}_{recipe}'
        if checkpoint(folder, FIT_FILES): metric, model, pred = replay(folder, cols, season, bundle); origin='local_checkpoint'
        else:
            require(budget > 0, 'Classifier budget exhausted')
            model = rf.fitted_model(x.iloc[ti], y[ti], cols); model['train_seasons'] = list(range(2013, season))
            validate_model(model, cols, season, len(ti)); p = rf.predict(model, x.iloc[vi]); q = rf.predict(model, rev.iloc[vi])
            require(np.isfinite(p).all() and ((p>0)&(p<1)).all() and np.max(abs(p+q-1))<1e-10, 'Invalid predictions')
            metric = {'Gender':'M', 'Season':season, 'recipe':recipe, 'games':len(vi),
                'brier':float(np.mean((p-y[vi])**2)), 'log_loss':float(-np.mean(y[vi]*np.log(p)+(1-y[vi])*np.log1p(-p)))}
            pred = pairs.iloc[vi].copy(); pred['y']=y[vi]; pred['probability']=p; pred['squared_error']=(p-y[vi])**2
            atomic_json(folder/'model.json', model); atomic_json(folder/'metrics.json', metric); atomic_csv(folder/'predictions.csv', pred)
            seal(folder, FIT_FILES); origin='new_fit'
    row = {k: metric[k] for k in ['Gender','Season','games','brier','log_loss']}
    row.update(recipe=recipe, train_games=len(ti), train_last_season=season-1,
        feature_count=len(cols), active_features=len(model['active_indices']), source=origin, evidence=CONFIG['scope'])
    pred=pred.copy();pred['recipe']=recipe;pred['squared_error']=(pred.probability-pred.y)**2
    return row, model, pred, origin


def effects(metrics):
    require(not metrics.duplicated(['Season','recipe']).any(), 'Duplicate metric grid')
    wide=metrics.pivot(index='Season', columns='recipe', values='brier')
    require(wide.index.tolist()==SEASONS and set(wide.columns)==set(wf.RECIPES) and np.isfinite(wide.to_numpy()).all(), 'Incomplete metric grid')
    return pd.DataFrame([{'Gender':'M','Season':int(s),'comparison':name,'delta_brier':float(r[a]-r[b])}
        for s,r in wide.iterrows() for name,a,b in [
          ('huber_given_anchor','anchor_huber','anchor'),
          ('compressed_given_anchor','anchor_compressed','anchor'),
          ('compression_given_huber','anchor_both','anchor_huber'),
          ('huber_given_compression','anchor_both','anchor_compressed'),
          ('both_given_anchor','anchor_both','anchor')]])


def decisions(eff):
    result=[];t=CONFIG['thresholds']
    for comparison in [CONFIG['primary'], CONFIG['secondary']]:
        d=eff.loc[eff.comparison.eq(comparison)].sort_values('Season')
        require(d.Season.tolist()==SEASONS and np.isfinite(d.delta_brier).all(), 'Incomplete decision evidence')
        v=d.delta_brier.to_numpy();ok=v.mean()<=t['mean_delta'] and (v<0).sum()>=t['improved_seasons'] and v.max()<=t['worst_delta']
        result.append({'Gender':'M','comparison':comparison,'primary':comparison==CONFIG['primary'],
            'mean_delta':float(v.mean()),'worst_delta':float(v.max()),'improved_seasons':int((v<0).sum()),
            'decision':'CONSIDER_UNCHANGED_LATER_ERA_TEST' if ok else 'DO_NOT_EXPAND_AUTOMATICALLY',
            'thresholds':t,'automatic_promotion':False,'significance_claim':False})
    return {'decisions':result,'primary_cannot_be_replaced_by_best_secondary':True}


def evaluate(ctx):
    out=ctx['directory'];stage_check(out,'prepare',PREP_FILES);bundle=matrices(ctx);pairs,y,x,_,_=bundle
    rows=[];preds=[];coeff=[];overlap=[];new=0;reuse=0;up=0
    for s in SEASONS:
        ti,vi=rf.split_indices(x,s);corr=x.iloc[ti][wf.ALL].corr()
        for f in wf.HUBER+wf.COMPRESSED:
            r=corr.loc[f,wf.BASE].dropna();name=r.abs().idxmax() if len(r) else 'training_constant'
            overlap.append({'Season':s,'feature':f,'closest_reference':name,'training_correlation':float(r[name]) if len(r) else np.nan})
        for recipe in wf.RECIPES:
            row,model,pred,origin=obtain(ctx,s,recipe,bundle,CONFIG['fit_cap']-new)
            new+=origin=='new_fit';reuse+=origin=='local_checkpoint';up+=origin=='upstream_replay';rows.append(row);preds.append(pred)
            for i,c in zip(model['active_indices'],model['coefficients']):
                coeff.append({'Season':s,'recipe':recipe,'feature':model['columns'][i],'standardized_coefficient':c})
            event('comparison_complete',season=s,recipe=recipe,brier=row['brier'],source=origin,completed=len(rows),total=16)
    metrics=pd.DataFrame(rows);a=metrics.query("recipe=='anchor'")[['Season','brier']].rename(columns={'brier':'anchor_brier'})
    metrics=metrics.merge(a,on='Season',validate='many_to_one');metrics['delta_vs_anchor']=metrics.brier-metrics.anchor_brier
    predictions=pd.concat(preds,ignore_index=True);eff=effects(metrics);decision=decisions(eff)
    calibration=predictions.copy();calibration['bin']=np.minimum((calibration.probability*10).astype(int),9)
    calibration=calibration.groupby(['recipe','bin']).agg(games=('y','size'),mean_probability=('probability','mean'),observed_fraction=('y','mean')).reset_index()
    aggregate=metrics.groupby('recipe',sort=False).agg(seasons=('Season','nunique'),games=('games','sum'),mean_brier=('brier','mean'),mean_delta=('delta_vs_anchor','mean')).reset_index()
    for n,f in [('metrics.csv',metrics),('predictions.csv',predictions),('ablations.csv',eff),('aggregate.csv',aggregate),
                ('coefficients.csv',pd.DataFrame(coeff)),('training_overlap.csv',pd.DataFrame(overlap)),('calibration.csv',calibration)]: atomic_csv(out/n,f)
    receipt={'new_classifier_fits':int(new),'upstream_replays':int(up),'local_reuses':int(reuse),'total_comparisons':16,'new_rating_fits_in_evaluation':0}
    atomic_json(out/'evaluation_receipt.json',receipt);atomic_json(out/'decisions.json',decision)
    atomic_json(out/'summary.json',dict(status='COMPLETE',phase='men_margin_robustness',fingerprint=ctx['fingerprint'],**receipt,
        new_candidates=2,decision=decision,current_submitted_brier=.1222672,research_target_brier=.1097454,new_leaderboard_score=None,
        github_updated=False,aws_resources_modified=False,repository_modified=False,raw_modified=False,upstream_modified=False,
        limitations=['Repeatedly-used 2016–2019 seasons; no untouched-test claim',
          'Fixed compact logistic is not the submitted production model',
          'Huber delta=15 points and tanh scale=15 points are predeclared heuristic choices, not tuned optima',
          'Large margins can be informative; compression may discard genuine signal',
          'An unusual residual is not proof of garbage time, injury, or bad data',
          'No date weighting, possession adjustment, personnel data, or new source added',
          'Research representation experiment, not a new statistical method']))
    preservation(ctx);stage_seal(out,'evaluation',EVAL_FILES)


def report(ctx):
    from margin_plots import render
    out=ctx['directory'];stage_check(out,'evaluation',EVAL_FILES);stage_check(out,'prepare',PREP_FILES)
    html=render(out,ctx['kit']/'evidence/round10');preservation(ctx)
    names=[n for n in EVAL_FILES if n!='predictions.csv']+[n for n in PREP_FILES if n not in ['team_profiles.csv']]+['preflight.json','manifest.json','prepare_hashes.json','evaluation_hashes.json']
    if (out/'cache_migration.json').is_file(): names.append('cache_migration.json')
    dest=ctx['kit']/'reports/milestone_11_return.zip';partial=dest.with_suffix('.zip.partial')
    require(not dest.is_symlink() and not partial.is_symlink(),'Unsafe report destination')
    with zipfile.ZipFile(partial,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for n in names:z.write(safe_file(out,n),n)
        z.write(ctx['prior_zip'],'prior_milestone_10_return.zip')
        z.writestr('return_integrity.json',json.dumps({'sha256':{**{n:sha(out/n) for n in names},
            'prior_milestone_10_return.zip':sha(ctx['prior_zip'])},
            'excluded':['raw rows','rating models/covariance','classifier models','individual predictions','private notebooks']},indent=2))
    os.replace(partial,dest)
    atomic_json(ctx['kit']/'reports/latest_report.json',{'status':'COMPLETE','return_zip':str(dest),'html':str(html),'plotly_figures':10,'return_sha256':sha(dest)})
    event('report_complete',return_zip=str(dest),plotly_figures=10)


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','evaluate','report']);args=p.parse_args()
    kit=Path(__file__).resolve().parent;home=Path.home()
    paths={'kit':kit,'repo':Path(os.environ.get('MARCH_REPO',str(home/'march-machine-learning-mania-2026'))),
        **{k:Path(os.environ.get('MARCH_'+k.upper()+'_KIT',str(home/name))) for k,name in
           [('shooting','march_shooting_research'),('schedule','march_schedule_research'),
            ('temporal','march_temporal_form'),('possession','march_possession_research'),('win_strength','march_win_strength')]}}
    event('stage_start',stage=args.stage)
    try:
        ctx=preflight(**paths);globals()[args.stage](ctx);event('stage_complete',stage=args.stage)
    except Exception as e:
        output_dir(kit/'reports');atomic_json(kit/'reports/failure.json',{'status':'STOP','stage':args.stage,'error_type':type(e).__name__,
            'error':str(e),'completed_checkpoints_preserved':True})
        raise
if __name__=='__main__':main()
