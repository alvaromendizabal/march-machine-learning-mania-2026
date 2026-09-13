"""Milestone 13: frozen consensus control tested in 2022-2025, never 2026.

Read-only upstream dependencies. Every expensive component has a sealed checkpoint.
No cloud, Git writes, source-package imports, pickle loading, or submission generation.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import zipfile
import numpy as np
import pandas as pd
import consensus_features as cf
from research_io import (rf,sf,require,sha,event,read_json,read_csv,safe_file,output_dir,
                        atomic_json,atomic_csv,environment,checkpoint,seal,
                        stage_seal,stage_check,normalize_metric,FIT_FILES)

SOURCES=['consensus_features.py','consensus_workflow.py','consensus_plots.py','research_io.py','run_round13.py',
         'frozen/research_workflow.py','frozen/shot_features.py','frozen/ranking_features_round12.py']
CONFIG={'round':'13-men-consensus-later-era','genders':['M'],'validation_seasons':cf.VALIDATION,
        'snapshot_years':cf.YEARS,'excluded_seasons':[2020,2026], 'recipes':cf.RECIPES,
        'parameters':cf.PARAMETERS,'support':cf.SUPPORT,'C':.1,'fit_cap':8,'rating_fit_cap':10,'threads':2,
        'primary':'consensus_given_anchor','thresholds':{'mean_delta':-.0005,'improved_seasons':3,'worst_delta':.003},
        'scope':'Exploratory later-era 2022-2025 played main draw; previously used project years, NOT untouched test or leaderboard',
        'label_selection':'Seed-stem First Four exclusion; explicit 2021 no-contest; 2020/2026 excluded',
        'new_feature_definitions':0,'automatic_promotion':False}
PAIR_FILES=['matchups.csv','team_profiles.csv','support.json']
PANEL_FILES=['panel.csv','panel_support.json']
BASE_FILES=['teams.csv','support.json']
PREP_FILES=['prepare.json','coverage.csv','panel_coverage.csv','team_profiles.csv','label_audit.csv',
            'feature_registry.csv','prior_replay.csv','upstream_data_identity.json']
EVAL_FILES=['metrics.csv','predictions.csv','ablations.csv','decisions.json','coefficients.csv',
            'calibration.csv','training_overlap.csv','aggregate.csv','season_sensitivity.csv',
            'paired_loss_bins.csv','evaluation_receipt.json','summary.json']


def archive_read(path, digest):
    require(sha(path)==digest,'Prior scientific archive differs; do not rerun completed work')
    with zipfile.ZipFile(path) as z:
        names=z.namelist();require(len(names)==len(set(names)) and len(names)<=80,'Invalid archive members')
        for i in z.infolist():
            q=Path(i.filename)
            require(not q.is_absolute() and '..' not in q.parts and i.file_size<15_000_000,'Unsafe archive member')
        require(sum(i.file_size for i in z.infolist())<40_000_000,'Oversized prior report')
        pin=json.loads(z.read('return_integrity.json'))['sha256']
        require(set(names)==set(pin)|{'return_integrity.json'},'Archive integrity scope mismatch')
        for n,h in pin.items():require(hashlib.sha256(z.read(n)).hexdigest()==h,'Prior archive corrupt: '+n)
        metrics=pd.read_csv(io.BytesIO(z.read('metrics.csv')),float_precision='round_trip')
        require(len(metrics)==20 and set(metrics.Season)=={2016,2017,2018,2019} and not metrics.duplicated(['Season','recipe']).any(),'Wrong previous experiment')
        return metrics,json.loads(z.read('decisions.json')),pin


def preflight(kit,repo,shooting,rankings):
    paths={k:Path(v).expanduser().absolute() for k,v in locals().copy().items()}
    for k,p in paths.items():require(p.is_dir() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents),'Missing/unsafe '+k)
    vals=list(paths.values())
    for i,a in enumerate(vals):
        for b in vals[i+1:]:require(not a.is_relative_to(b) and not b.is_relative_to(a),'Keep all kits and repo as sibling directories')
    kit,repo=paths['kit'],paths['repo'];c=read_json(safe_file(kit,'constraints.json'))
    manifest=read_json(safe_file(kit,'MANIFEST.json'))['sha256']
    protected=SOURCES+['constraints.json']+[str(p.relative_to(kit)) for p in (kit/'evidence').rglob('*') if p.is_file()]
    for n in protected:require(n in manifest and sha(safe_file(kit,n))==manifest[n],'Delivered source/evidence changed: '+n)
    for n,h in c['frozen_sources'].items():require(sha(safe_file(kit,n))==h,'Frozen formula/fitting source changed')
    require(environment()==c['environment'],'Environment differs from completed run; report it, do not reinstall')
    state=rf.repository_state(repo);require(state==c['state'],'Repository differs from last verified state; preserve edits')
    raw=repo/'data/kaggle/raw'
    for n,h in c['data'].items():require(sha(safe_file(raw,n))==h,'Raw input changed: '+n)
    roots={k:paths[k]/'private_runs'/v for k,v in c['fingerprints'].items()}
    tracked={}
    def remember(key,rel,pin=None):
        h=sha(safe_file(roots[key],rel));require(pin is None or h==pin,'Changed pinned upstream: '+key+'/'+rel)
        tracked[key+'/'+rel]=h
    for rel,h in c['shooting_pins'].items():remember('shooting',rel,h)
    remember('rankings','manifest.json',c['ranking_manifest_sha256'])
    remember('rankings','prepare_hashes.json',c['ranking_preparation_hashes_sha256'])
    remember('rankings','evaluation_hashes.json',c['ranking_evaluation_hashes_sha256'])
    for stage in ['prepare','evaluation']:
        for n,h in read_json(roots['rankings']/(stage+'_hashes.json')).items():remember('rankings',n,h)
    for s in cf.OLD_YEARS:
        for root,rel,names in [('shooting',f'snapshots/M_{s}',['teams.csv','coverage.json','opponent_exclusion_audit.csv']),
                              ('rankings',f'snapshots/M_{s}',['matchups.csv','team_profiles.csv','pair_support.csv','support.json']),
                              ('rankings',f'panels/M_{s}',PANEL_FILES)]:
            require(checkpoint(roots[root]/rel,names),'Missing completed '+root+'/'+rel)
            for n in names+['complete.json']:remember(root,rel+'/'+n)
    for s in [2016,2017,2018,2019]:
        rel=f'fits/M_{s}_anchor_consensus';require(checkpoint(roots['rankings']/rel,FIT_FILES),'Missing old consensus fit')
        for n in FIT_FILES+['complete.json']:remember('rankings',rel+'/'+n)
    prior=safe_file(paths['rankings'],'reports/milestone_12_return.zip')
    prior_metrics,prior_decisions,prior_hashes=archive_read(prior,c['previous_report_sha256'])
    require(sha(kit/'evidence/round12/metrics.csv')==prior_hashes['metrics.csv'],'Uploaded prior metrics differ')
    evidence={str(p.relative_to(kit)):sha(p) for p in (kit/'evidence').rglob('*') if p.is_file()}
    identity={'config':CONFIG,'source':{n:sha(kit/n) for n in SOURCES},'constraints_sha256':sha(kit/'constraints.json'),
              'data':c['data'],'environment':environment(),'upstream_files':tracked,'evidence':evidence,
              'upstream_fingerprints':c['fingerprints'],'reference_commit':c['reference_commit'],'prior_report_sha256':sha(prior)}
    fp=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest();out=kit/'private_runs'/fp
    output_dir(out);output_dir(kit/'reports');require(shutil.disk_usage(out).free>=256*1024**2,'Under 256 MiB free; do not delete private data')
    m=dict(identity,fingerprint=fp)
    if (out/'manifest.json').exists():require(read_json(out/'manifest.json')==m,'Run identity mismatch')
    else:atomic_json(out/'manifest.json',m)
    atomic_json(kit/'reports/latest_run.json',{'run_dir':str(out),'fingerprint':fp})
    atomic_json(out/'preflight.json',{'status':'PASS','state':state,'old_snapshots_verified':7,
                  'old_consensus_classifiers_verified':4,'raw_files_verified':len(c['data']),'project_source_imported':False})
    event('preflight_pass',old_snapshots=7,old_consensus_models=4,new_rating_fit_cap=10,new_classifier_fit_cap=8)
    return dict(kit=kit,repo=repo,raw=raw,directory=out,state=state,identity=identity,fingerprint=fp,
                prior_zip=prior,prior_metrics=prior_metrics,prior_decisions=prior_decisions,**roots)


def preservation(ctx):
    require(rf.repository_state(ctx['repo'])==ctx['state'],'Repository changed during stage')
    require(environment()==ctx['identity']['environment'],'Environment changed')
    for n,h in ctx['identity']['source'].items():require(sha(safe_file(ctx['kit'],n))==h,'Kit source changed')
    require(sha(ctx['kit']/'constraints.json')==ctx['identity']['constraints_sha256'],'Constraints changed')
    for n,h in ctx['identity']['data'].items():require(sha(safe_file(ctx['raw'],n))==h,'Raw input changed')
    for n,h in ctx['identity']['upstream_files'].items():
        root,rel=n.split('/',1);require(sha(safe_file(ctx[root],rel))==h,'Upstream artifact changed: '+n)
    for n,h in ctx['identity']['evidence'].items():require(sha(safe_file(ctx['kit'],n))==h,'Preserved evidence changed')
    require(sha(ctx['prior_zip'])==ctx['identity']['prior_report_sha256'],'Prior report changed')
    event('preservation_pass',repository=True,raw=True,upstream=True)


def matrices(ctx):
    frames=[]
    for s in cf.YEARS:
        root=ctx['rankings'] if s in cf.OLD_YEARS else ctx['directory']
        f=read_csv(root/f'snapshots/M_{s}/matchups.csv')
        require(set(cf.KEYS+cf.ALL)<=set(f),'Missing compact/consensus inputs')
        frames.append(f[cf.KEYS+cf.ALL])
    allx=pd.concat(frames,ignore_index=True)
    pairs,y,audit=cf.tournament_labels(read_csv(ctx['raw']/'MNCAATourneyCompactResults.csv'),
                                     read_csv(ctx['raw']/'MNCAATourneySeeds.csv'),read_csv(ctx['raw']/'MTeams.csv'))
    x=pairs.merge(allx,on=cf.KEYS,how='left',validate='one_to_one')
    require(len(x)==len(y) and np.isfinite(x[cf.ALL].to_numpy()).all(),'Target/feature alignment failure')
    return pairs,y,x,audit


def validate_model(m,cols,season,ntrain):
    require(m['columns']==cols and m['C']==.1 and m['fit_intercept'] is False,'Different fitted recipe')
    years=[s for s in cf.YEARS if s<season]
    require(m['physical_train_games']==ntrain and m['train_seasons']==years,'Training history mismatch (2020 must be absent)')
    idx=m['active_indices'];require(idx and len(idx)==len(set(idx)) and all(isinstance(i,int) and 0<=i<len(cols) for i in idx),'Bad active inputs')
    require(len(idx)==len(m['coefficients'])==len(m['scales']),'Model dimensions disagree')
    require(np.isfinite(m['coefficients']).all() and np.isfinite(m['scales']).all() and (np.asarray(m['scales'])>0).all(),'Bad fitted parameters')


def replay_fit(folder,cols,season,bundle):
    require(checkpoint(folder,FIT_FILES),'Incomplete model checkpoint')
    pairs,y,x,_=bundle;ti,vi=rf.split_indices(x,season)
    m=read_json(folder/'model.json');validate_model(m,cols,season,len(ti))
    p=rf.predict(m,x.iloc[vi]);saved=read_csv(folder/'predictions.csv')
    # Semantic identity checks allow lossless CSV integer/float inference only.
    require(saved.Gender.tolist()==pairs.iloc[vi].Gender.tolist(),'Prediction genders differ')
    require(np.array_equal(saved[cf.KEYS[1:]].to_numpy(),pairs.iloc[vi][cf.KEYS[1:]].to_numpy()),'Prediction keys/order differ')
    require(np.array_equal(saved.y.to_numpy(),y[vi]) and np.max(abs(saved.probability.to_numpy()-p))<1e-12,'Saved predictions differ')
    reverse=x.iloc[vi].copy();reverse[cols]=-reverse[cols]
    require(np.max(abs(p+rf.predict(m,reverse)-1))<1e-10,'Prediction swap failure')
    metric=normalize_metric(read_json(folder/'metrics.json'),y[vi],p,'M',season)
    return metric,m,saved


def prepare(ctx):
    out=ctx['directory'];compact=read_csv(ctx['raw']/'MRegularSeasonCompactResults.csv');detailed=read_csv(ctx['raw']/'MRegularSeasonDetailedResults.csv')
    seeds=read_csv(ctx['raw']/'MNCAATourneySeeds.csv');new_fits=0;reused_fits=0;new_bases=0;new_pairs=0
    missing=[s for s in cf.NEW_YEARS if not checkpoint(out/f'panels/M_{s}',PANEL_FILES)]
    if missing:
        legal=cf.read_rankings(ctx['raw']/'MMasseyOrdinals.csv',missing)
        for s in missing:
            panel,info=cf.publication_panel(legal,s);f=out/f'panels/M_{s}'
            atomic_csv(f/'panel.csv',panel);atomic_json(f/'panel_support.json',info);seal(f,PANEL_FILES)
            event('panel_complete',season=s,new_rating_fits=0)
    coverage=[];profiles=[];panels=[]
    for s in cf.OLD_YEARS:
        coverage.append(dict(read_json(ctx['rankings']/f'snapshots/M_{s}/support.json'),source='upstream_reuse'))
        profile=read_csv(ctx['rankings']/f'snapshots/M_{s}/team_profiles.csv');profiles.append(profile)
        panels.append(read_json(ctx['rankings']/f'panels/M_{s}/panel_support.json'))
    for i,s in enumerate(cf.NEW_YEARS):
        basefolder=out/f'base/M_{s}'
        if not checkpoint(basefolder,BASE_FILES):
            games,long=cf.reference_inputs(compact,detailed,s)
            blocks=[]
            for role,fn in [('margin',lambda:sf.compact_strength(games)),('efficiency',lambda:sf.standard_control(long))]:
                f=out/f'ratings/M_{s}_{role}'
                if checkpoint(f,['ratings.csv']):block=read_csv(f/'ratings.csv');reused_fits+=1
                else:
                    require(new_fits<CONFIG['rating_fit_cap'],'Rating fit cap exceeded');block=fn()
                    atomic_csv(f/'ratings.csv',block);seal(f,['ratings.csv']);new_fits+=1
                blocks.append(block);event('rating_component_complete',season=s,role=role,new_rating_fits=new_fits,reused_rating_components=reused_fits)
            base=cf.finish_reference(blocks[0],blocks[1],long,seeds,s)
            atomic_csv(basefolder/'teams.csv',base)
            atomic_json(basefolder/'support.json',{'Season':s,'regular_games':len(games),'day_cutoff':132,'rating_components':2,'tournament_labels_used':False})
            seal(basefolder,BASE_FILES);new_bases+=1
        else:
            for role in ['margin','efficiency']:require(checkpoint(out/f'ratings/M_{s}_{role}',['ratings.csv']),'Missing completed rating component')
            reused_fits+=2
        base=read_csv(basefolder/'teams.csv');panel=read_csv(out/f'panels/M_{s}/panel.csv')
        folder=out/f'snapshots/M_{s}'
        if not checkpoint(folder,PAIR_FILES):
            pairs,profile,info=cf.build_matchups(base,panel)
            atomic_csv(folder/'matchups.csv',pairs);atomic_csv(folder/'team_profiles.csv',profile);atomic_json(folder/'support.json',info)
            seal(folder,PAIR_FILES);new_pairs+=1
        coverage.append(dict(read_json(folder/'support.json'),source='later_era'))
        profiles.append(read_csv(folder/'team_profiles.csv'));panels.append(read_json(out/f'panels/M_{s}/panel_support.json'))
        event('season_snapshot_complete',season=s,completed=i+1,total=5)
    bundle=matrices(ctx);audit=bundle[3];replays=[]
    for s in [2016,2017,2018,2019]:
        metric,_,_=replay_fit(ctx['rankings']/f'fits/M_{s}_anchor_consensus',cf.ALL,s,bundle)
        target=ctx['prior_metrics'].query("Season==@s and recipe=='anchor_consensus'").brier.iloc[0]
        require(abs(metric['brier']-target)<1e-12,'Historical consensus replay differs')
        replays.append({'Season':s,'recipe':'anchor_consensus','brier':metric['brier'],'status':'VERIFIED_NO_REFIT'})
    for n,f in [('coverage.csv',pd.DataFrame(coverage)),('panel_coverage.csv',pd.DataFrame(panels)),('team_profiles.csv',pd.concat(profiles,ignore_index=True)),
                ('label_audit.csv',audit),('feature_registry.csv',cf.registry()),('prior_replay.csv',pd.DataFrame(replays))]:atomic_csv(out/n,f)
    atomic_json(out/'upstream_data_identity.json',{'prior_report_sha256':sha(ctx['prior_zip']),'prior_consensus_replays':4,
        'new_label_loader_old_years_compatible':True,'current_tournament_targets_excluded':[2020,2026]})
    atomic_json(out/'prepare.json',{'status':'COMPLETE','old_base_and_matchup_snapshots_reused':7,'old_consensus_models_replayed':4,
        'new_rating_fits':new_fits,'rating_component_reuses':reused_fits,'new_compact_snapshots':new_bases,'compact_snapshot_reuses':5-new_bases,
        'new_ranking_panels':len(missing),'ranking_panel_reuses':5-len(missing),'new_matchup_tables':new_pairs,'matchup_table_reuses':5-new_pairs,
        'new_tournament_classifier_fits':0,'new_feature_definitions':0,'early_years_not_refitted':True})
    preservation(ctx);stage_seal(out,'prepare',PREP_FILES)


def decision(effects):
    require(effects.Season.tolist()==cf.VALIDATION and np.isfinite(effects.delta_brier).all(),'Incomplete later-era comparison')
    v=effects.delta_brier.to_numpy();t=CONFIG['thresholds']
    ok=v.mean()<=t['mean_delta'] and (v<0).sum()>=t['improved_seasons'] and v.max()<=t['worst_delta']
    return {'comparison':CONFIG['primary'],'validation_seasons':cf.VALIDATION,'mean_delta':float(v.mean()),
            'worst_delta':float(v.max()),'improved_seasons':int((v<0).sum()),'thresholds':t,
            'decision':'CONSIDER_FIXED_PRODUCTION_RECIPE_TEST' if ok else 'DO_NOT_PROMOTE_TO_PRODUCTION',
            'automatic_promotion':False,'significance_claim':False,'discovery_years_excluded_from_gate':True}


def evaluate(ctx):
    out=ctx['directory'];stage_check(out,'prepare',PREP_FILES);bundle=matrices(ctx);pairs,y,x,_=bundle
    rows=[];preds=[];coefs=[];overlap=[];new=0;reuse=0
    for s in cf.VALIDATION:
        ti,vi=rf.split_indices(x,s);train_years=sorted(x.iloc[ti].Season.unique().tolist())
        require(train_years==[v for v in cf.YEARS if v<s],'Temporal split mismatch')
        corr=x.iloc[ti][cf.ALL].corr()[cf.CONSENSUS].reindex(cf.BASE).dropna()
        overlap.append({'Season':s,'feature':cf.CONSENSUS,'closest_reference':corr.abs().idxmax() if len(corr) else 'training_constant',
                        'training_correlation':float(corr.loc[corr.abs().idxmax()]) if len(corr) else 0.0})
        for recipe,cols in cf.RECIPES.items():
            folder=out/f'fits/M_{s}_{recipe}'
            if checkpoint(folder,FIT_FILES):metric,model,pred=replay_fit(folder,cols,s,bundle);origin='local_checkpoint';reuse+=1
            else:
                require(new<CONFIG['fit_cap'],'Classifier cap exhausted')
                model=rf.fitted_model(x.iloc[ti],y[ti],cols);model['train_seasons']=train_years;validate_model(model,cols,s,len(ti))
                p=rf.predict(model,x.iloc[vi]);reverse=x.iloc[vi].copy();reverse[cols]=-reverse[cols]
                require(np.isfinite(p).all() and ((p>0)&(p<1)).all() and np.max(abs(p+rf.predict(model,reverse)-1))<1e-10,'Invalid probability or swap check')
                metric={'Gender':'M','Season':s,'recipe':recipe,'games':len(vi),'brier':float(np.mean((p-y[vi])**2)),
                        'log_loss':float(-np.mean(y[vi]*np.log(p)+(1-y[vi])*np.log1p(-p)))}
                pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=p;pred['squared_error']=(p-y[vi])**2
                atomic_json(folder/'model.json',model);atomic_json(folder/'metrics.json',metric);atomic_csv(folder/'predictions.csv',pred);seal(folder,FIT_FILES)
                origin='new_fit';new+=1
            row={k:metric[k] for k in ['Gender','Season','games','brier','log_loss']}
            row.update(recipe=recipe,train_games=len(ti),train_last_season=s-1,feature_count=len(cols),active_features=len(model['active_indices']),source=origin,evidence=CONFIG['scope'])
            rows.append(row);pred=pred.copy();pred['recipe']=recipe;pred['squared_error']=(pred.probability-pred.y)**2;preds.append(pred)
            for i,v in zip(model['active_indices'],model['coefficients']):coefs.append({'Season':s,'recipe':recipe,'feature':cols[i],'standardized_coefficient':v})
            event('comparison_complete',season=s,recipe=recipe,brier=metric['brier'],source=origin,completed=len(rows),total=8)
    m=pd.DataFrame(rows);m=m.merge(m.query("recipe=='anchor'")[['Season','brier']].rename(columns={'brier':'anchor_brier'}),on='Season',validate='many_to_one')
    m['delta_vs_anchor']=m.brier-m.anchor_brier
    wide=m.pivot(index='Season',columns='recipe',values='brier').sort_index()
    eff=pd.DataFrame({'Season':wide.index,'comparison':CONFIG['primary'],'delta_brier':wide.anchor_consensus-wide.anchor}).reset_index(drop=True)
    d=decision(eff);p=pd.concat(preds,ignore_index=True)
    cal=p.copy();cal['bin']=np.minimum((cal.probability*10).astype(int),9)
    cal=cal.groupby(['recipe','bin']).agg(games=('y','size'),mean_probability=('probability','mean'),observed_fraction=('y','mean')).reset_index()
    ag=m.groupby('recipe').agg(seasons=('Season','nunique'),games=('games','sum'),mean_brier=('brier','mean'),mean_log_loss=('log_loss','mean'),mean_delta=('delta_vs_anchor','mean')).reset_index()
    ag['game_weighted_brier']=[np.average(m.loc[m.recipe.eq(r),'brier'],weights=m.loc[m.recipe.eq(r),'games']) for r in ag.recipe]
    sens=pd.DataFrame([{'omitted_season':s,'remaining_mean_delta':float(eff.loc[eff.Season.ne(s),'delta_brier'].mean())} for s in cf.VALIDATION])
    pa=p.query("recipe=='anchor'").copy();pc=p.query("recipe=='anchor_consensus'")
    paired=pa.merge(pc[cf.KEYS+['probability','squared_error']],on=cf.KEYS,validate='one_to_one',suffixes=('_anchor','_consensus'))
    paired['confidence_bin']=np.minimum((paired.probability_anchor*10).astype(int),9)
    paired['delta']=paired.squared_error_consensus-paired.squared_error_anchor
    bins=paired.groupby('confidence_bin').agg(games=('y','size'),mean_delta=('delta','mean'),total_delta=('delta','sum')).reset_index()
    for n,f in [('metrics.csv',m),('predictions.csv',p),('ablations.csv',eff),('aggregate.csv',ag),('coefficients.csv',pd.DataFrame(coefs)),
                ('training_overlap.csv',pd.DataFrame(overlap)),('calibration.csv',cal),('season_sensitivity.csv',sens),('paired_loss_bins.csv',bins)]:atomic_csv(out/n,f)
    receipt={'new_classifier_fits':new,'local_reuses':reuse,'total_comparisons':8,'new_rating_fits_in_evaluation':0,'validation_seasons':cf.VALIDATION}
    atomic_json(out/'evaluation_receipt.json',receipt);atomic_json(out/'decisions.json',d)
    atomic_json(out/'summary.json',dict(status='COMPLETE',fingerprint=ctx['fingerprint'],phase='later-era consensus feature validation',
        **receipt,decision=d,new_feature_definitions=0,current_submitted_brier=.1222672,research_target_brier=.1097454,
        new_leaderboard_score=None,github_updated=False,repository_modified=False,raw_modified=False,upstream_modified=False,aws_resources_modified=False,
        limitations=['2022-2025 were already used elsewhere in the project; not untouched tests',
        'Consensus already existed; this is replication, not novel feature discovery',
        'Fixed compact logistic is not the final pooled XGBoost production recipe',
        'Main draw excludes First Four and administrative no-contest; not the full competition evaluation',
        '2020 and 2026 excluded; 2021 main-draw targets selected by seeds, not day>=136',
        'Different years can publish different sets of ordinal systems; no claim they are independent',
        'No transfer into the submitted model until a separate fixed-recipe test']))
    preservation(ctx);stage_seal(out,'evaluation',EVAL_FILES)


def report(ctx):
    from consensus_plots import render
    out=ctx['directory'];stage_check(out,'prepare',PREP_FILES);stage_check(out,'evaluation',EVAL_FILES)
    html=render(out,ctx['kit']/'evidence/round12');preservation(ctx)
    names=[n for n in EVAL_FILES if n!='predictions.csv']+[n for n in PREP_FILES if n!='team_profiles.csv']+['preflight.json','manifest.json','prepare_hashes.json','evaluation_hashes.json']
    dest=ctx['kit']/'reports/milestone_13_return.zip';tmp=dest.with_suffix('.zip.partial')
    require(not dest.is_symlink() and not tmp.is_symlink(),'Unsafe report output')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for n in names:z.write(safe_file(out,n),n)
        z.write(ctx['prior_zip'],'prior_milestone_12_return.zip')
        z.writestr('return_integrity.json',json.dumps({'sha256':{**{n:sha(out/n) for n in names},'prior_milestone_12_return.zip':sha(ctx['prior_zip'])},
            'excluded':['raw rows','fitted models','per-game predictions','team-level feature rows','private notebooks']},indent=2))
    os.replace(tmp,dest)
    atomic_json(ctx['kit']/'reports/latest_report.json',{'status':'COMPLETE','return_zip':str(dest),'return_sha256':sha(dest),'html':str(html),'plotly_figures':10})
    event('report_complete',return_zip=str(dest),plotly_figures=10)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','evaluate','report']);args=parser.parse_args()
    kit=Path(__file__).resolve().parent;home=Path.home()
    paths={'kit':kit,'repo':Path(os.environ.get('MARCH_REPO',home/'march-machine-learning-mania-2026')),
           'shooting':Path(os.environ.get('MARCH_SHOOTING_KIT',home/'march_shooting_research')),
           'rankings':Path(os.environ.get('MARCH_RANKINGS_KIT',home/'march_ranking_matchups'))}
    event('stage_start',stage=args.stage)
    try:ctx=preflight(**paths);globals()[args.stage](ctx);event('stage_complete',stage=args.stage)
    except Exception as e:
        output_dir(kit/'reports');atomic_json(kit/'reports/failure.json',{'status':'STOP','stage':args.stage,'error_type':type(e).__name__,'error':str(e),'completed_checkpoints_preserved':True})
        raise

if __name__=='__main__':main()
