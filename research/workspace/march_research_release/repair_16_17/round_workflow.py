"""Independent rounds 16/17; read-only upstream reuse and bounded saved fits."""
from __future__ import annotations
import argparse, hashlib, io, json, os, shutil, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from research_io import (rf,sf,require,sha,event,read_json,read_csv,safe_file,output_dir,
  atomic_json,atomic_csv,environment,checkpoint,seal,stage_seal,stage_check,normalize_metric,FIT_FILES)
import consensus_reference as cf
import feature_rounds as fr

SOURCES=['feature_rounds.py','round_workflow.py','round_plots.py','run_round.py','research_io.py',
 'frozen/research_workflow.py','frozen/shot_features.py','frozen/consensus_reference.py']
SNAP_FILES=['matchups.csv','profiles.csv','coverage.csv','support.csv']
PREP_FILES=['prepare.json','coverage.csv','profiles.csv','feature_registry.csv','prior_replay.csv','label_audit.csv','rating_diagnostics.csv']
EVAL_FILES=['metrics.csv','predictions.csv','ablations.csv','decisions.json','coefficients.csv','calibration.csv',
 'training_overlap.csv','aggregate.csv','paired_loss_bins.csv','season_sensitivity.csv','support_diagnostics.csv',
 'evaluation_receipt.json','summary.json','season_bootstrap.json']

def config(round_id):
    require(round_id in fr.FEATURES,'Unknown round')
    return {'round':round_id,'validation_seasons':fr.VALIDATION,'snapshot_seasons':fr.YEARS,
       'recipes':fr.recipes(round_id),'parameters':fr.PARAMETERS[round_id],'C':.1,'fit_cap':20,'rating_fit_cap':24,
       'primary':'adjustment_given_rates','genders':['M'],'threads':2,'new_candidate_definitions':4,'unadjusted_rate_controls':4,
       'thresholds':{'mean_delta':-.0005,'improved_seasons':3,'worst_delta':.003},
       'duplicate_diagnostic_required_for_expansion':True,'automatic_promotion':False,
       'scope':'Previously used 2022-2025 played main draw; exploratory, not production or leaderboard',
       'excluded_seasons':[2020,2026]}


def inspect_archive(path,digest):
    require(sha(path)==digest,'Prior report changed; do not rerun completed work')
    with zipfile.ZipFile(path) as z:
        names=z.namelist();require(len(names)<=80 and len(names)==len(set(names)),'Invalid archive member list')
        for i in z.infolist():
            q=Path(i.filename);require(not q.is_absolute() and '..' not in q.parts and i.file_size<20_000_000,'Unsafe archive member')
        require(sum(i.file_size for i in z.infolist())<40_000_000,'Oversized report')
        pins=json.loads(z.read('return_integrity.json'))['sha256']
        require(set(names)==set(pins)|{'return_integrity.json'},'Incomplete archive integrity scope')
        for n,h in pins.items():require(hashlib.sha256(z.read(n)).hexdigest()==h,'Corrupt report: '+n)
        m=pd.read_csv(io.BytesIO(z.read('metrics.csv')),float_precision='round_trip')
        require(len(m)==8 and set(m.Season)==set(fr.VALIDATION) and not m.duplicated(['Season','recipe']).any(),'Wrong prior experiment')
        return m


def preflight(kit,repo,shooting,rankings,consensus,round_id):
    require(round_id in fr.FEATURES,'Unsupported round')
    paths={k:Path(v).expanduser().absolute() for k,v in {'kit':kit,'repo':repo,'shooting':shooting,'rankings':rankings,'consensus':consensus}.items()}
    for k,p in paths.items():require(p.is_dir() and not p.is_symlink() and not any(q.is_symlink() for q in p.parents),'Missing/unsafe '+k)
    for k,p in paths.items():
        for other,q in paths.items():
            if k!=other:require(not p.is_relative_to(q),'Keep repository and kits in separate sibling directories')
    kit,repo=paths['kit'],paths['repo'];c=read_json(safe_file(kit,'constraints.json'))
    pin=read_json(safe_file(kit,'MANIFEST.json'))['sha256']
    protected=SOURCES+['constraints.json','run_tests.py']+[n for n in ['original_source_hashes.json','reuse_2013.py'] if (kit/n).is_file()]+[str(p.relative_to(kit)) for p in (kit/'evidence').rglob('*') if p.is_file()]
    for n in protected:require(n in pin and sha(safe_file(kit,n))==pin[n],'Delivered source/evidence changed: '+n)
    for n,h in c['frozen_sources'].items():require(sha(safe_file(kit,n))==h,'Frozen source changed: '+n)
    test_record=read_json(safe_file(kit,'reports/test_receipt.json'))
    require(test_record.get('status')=='PASS','Run run_tests.py before scientific stages')
    require(test_record.get('source_sha256')=={n:sha(kit/n) for n in SOURCES},'Source changed since your tests; rerun the tests')
    suite={str(p.relative_to(kit)):sha(p) for p in sorted((kit/'tests').glob('*.py'))}
    require(test_record.get('suite_sha256')==suite,'Test suite changed since the recorded run')
    require(environment()==c['environment'],'Environment differs; report it, do not reinstall or change constraints')
    state=rf.repository_state(repo);require(state==c['state'],'Repository state changed; preserve edits')
    raw=repo/'data/kaggle/raw'
    for n,h in c['data'].items():require(sha(safe_file(raw,n))==h,'Raw input changed: '+n)
    roots={k:paths[k]/'private_runs'/v for k,v in c['fingerprints'].items()}
    tracked={}
    def remember(root,rel,pinned=None):
        h=sha(safe_file(roots[root],rel));require(pinned is None or h==pinned,'Changed upstream '+root+'/'+rel)
        tracked[root+'/'+rel]=h
    for key,h in c['prior_upstream_pins'].items():
        root,rel=key.split('/',1);remember(root,rel,h)
    remember('consensus','manifest.json',c['consensus_manifest_sha256'])
    for stage,h in c['consensus_stage_hashes'].items():
        remember('consensus',stage+'_hashes.json',h)
        for n,v in read_json(roots['consensus']/(stage+'_hashes.json')).items():remember('consensus',n,v)
    for s in fr.YEARS:
        roles=[('shooting' if s in cf.OLD_YEARS else 'consensus',
                f'snapshots/M_{s}' if s in cf.OLD_YEARS else f'base/M_{s}',
                ['teams.csv','coverage.json','opponent_exclusion_audit.csv'] if s in cf.OLD_YEARS else ['teams.csv','support.json']),
               ('rankings' if s in cf.OLD_YEARS else 'consensus',f'snapshots/M_{s}',
                ['matchups.csv','team_profiles.csv','pair_support.csv','support.json'] if s in cf.OLD_YEARS else ['matchups.csv','team_profiles.csv','support.json']),
               ('rankings' if s in cf.OLD_YEARS else 'consensus',f'panels/M_{s}',['panel.csv','panel_support.json'])]
        for root,rel,names in roles:
            require(checkpoint(roots[root]/rel,names),'Missing completed '+root+'/'+rel)
            for n in names+['complete.json']:remember(root,rel+'/'+n)
    for s in fr.VALIDATION:
        rel=f'fits/M_{s}_anchor_consensus'
        require(checkpoint(roots['consensus']/rel,FIT_FILES),'Missing completed consensus classifier')
        for n in FIT_FILES+['complete.json']:remember('consensus',rel+'/'+n)
    prior=safe_file(paths['consensus'],'reports/milestone_13_return.zip')
    prior_metrics=inspect_archive(prior,c['previous_report_sha256'])
    identity={'config':config(round_id),'data':c['data'],'environment':c['environment'],
       'source':{n:sha(kit/n) for n in SOURCES},'constraints_sha256':sha(kit/'constraints.json'),
       'upstream_fingerprints':c['fingerprints'],'upstream_files':tracked,'executed_tests':{'source_sha256':test_record['source_sha256'],'suite_sha256':test_record['suite_sha256']},
       'evidence':{n:sha(kit/n) for n in protected if n.startswith('evidence/')},
       'reference_commit':c['reference_commit'],'prior_report_sha256':sha(prior)}
    fp=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    out=kit/'private_runs'/('round'+round_id)/fp;output_dir(out)
    reports=kit/'reports'/('round'+round_id);output_dir(reports)
    require(shutil.disk_usage(out).free>=256*1024**2,'Under 256 MiB free; preserve existing data and checkpoints')
    manifest=dict(identity,fingerprint=fp)
    if (out/'manifest.json').exists():require(read_json(out/'manifest.json')==manifest,'Run identity conflict')
    else:atomic_json(out/'manifest.json',manifest)
    atomic_json(reports/'latest_run.json',{'run_dir':str(out),'fingerprint':fp})
    atomic_json(out/'preflight.json',{'status':'PASS','state':state,'snapshots_reused':12,'reference_fits_verified':4,
          'new_rating_fit_cap':24,'new_classifier_fit_cap':20,'source_repository_imported':False,'round':round_id})
    event('preflight_pass',round=round_id,snapshots=12,new_rating_fit_cap=24,new_classifier_fit_cap=20)
    return dict(kit=kit,repo=repo,raw=raw,directory=out,reports=reports,round=round_id,state=state,identity=identity,
          fingerprint=fp,prior_zip=prior,prior_metrics=prior_metrics,**roots)


def preservation(ctx):
    require(rf.repository_state(ctx['repo'])==ctx['state'],'Repository changed during stage')
    require(environment()==ctx['identity']['environment'],'Environment changed')
    for n,h in ctx['identity']['source'].items():require(sha(safe_file(ctx['kit'],n))==h,'Kit source changed')
    require(sha(ctx['kit']/'constraints.json')==ctx['identity']['constraints_sha256'],'Constraints changed')
    for n,h in ctx['identity']['data'].items():require(sha(safe_file(ctx['raw'],n))==h,'Raw input changed')
    for n,h in ctx['identity']['upstream_files'].items():
        root,rel=n.split('/',1);require(sha(safe_file(ctx[root],rel))==h,'Upstream changed: '+n)
    for n,h in ctx['identity']['evidence'].items():require(sha(safe_file(ctx['kit'],n))==h,'Evidence changed')
    require(sha(ctx['prior_zip'])==ctx['identity']['prior_report_sha256'],'Prior report changed')
    event('preservation_pass',round=ctx['round'],repository=True,raw=True,upstream=True)


def upstream_tables(ctx,s):
    root=ctx['rankings'] if s in cf.OLD_YEARS else ctx['consensus']
    basepath=ctx['shooting']/f'snapshots/M_{s}/teams.csv' if s in cf.OLD_YEARS else ctx['consensus']/f'base/M_{s}/teams.csv'
    base=read_csv(basepath);pairs=read_csv(root/f'snapshots/M_{s}/matchups.csv')[cf.KEYS+cf.ALL]
    panel=read_csv(root/f'panels/M_{s}/panel.csv')
    require(len(pairs)==2278 and not pairs.duplicated(cf.KEYS).any(),'Expected 68-team potential-pair table')
    return base,panel,pairs


def matrices(ctx):
    xall=pd.concat([read_csv(ctx['directory']/f'snapshots/M_{s}/matchups.csv') for s in fr.YEARS],ignore_index=True)
    pairs,y,audit=cf.tournament_labels(read_csv(ctx['raw']/'MNCAATourneyCompactResults.csv'),
        read_csv(ctx['raw']/'MNCAATourneySeeds.csv'),read_csv(ctx['raw']/'MTeams.csv'))
    x=pairs.merge(xall,on=cf.KEYS,how='left',validate='one_to_one')
    cols=fr.BASE+fr.CONTROLS[ctx['round']]+fr.FEATURES[ctx['round']]+fr.DUPLICATE
    require(len(x)==len(y) and np.isfinite(x[cols].to_numpy()).all(),'Feature/label alignment failure')
    return pairs,y,x,audit


def validate_model(m,cols,s,ntrain):
    require(m['columns']==cols and m['C']==.1 and m['fit_intercept'] is False,'Fitted recipe differs')
    require(m['physical_train_games']==ntrain and m['train_seasons']==[y for y in fr.YEARS if y<s],'Training-history mismatch')
    idx=m['active_indices'];require(idx and len(idx)==len(set(idx)) and all(isinstance(i,int) and 0<=i<len(cols) for i in idx),'Invalid active columns')
    require(len(idx)==len(m['coefficients'])==len(m['scales']),'Model dimension mismatch')
    require(np.isfinite(m['coefficients']).all() and np.isfinite(m['scales']).all() and (np.asarray(m['scales'])>0).all(),'Invalid model parameters')


def replay(folder,cols,s,bundle):
    require(checkpoint(folder,FIT_FILES),'Incomplete fit checkpoint')
    pairs,y,x,_=bundle;ti,vi=rf.split_indices(x,s);m=read_json(folder/'model.json')
    validate_model(m,cols,s,len(ti));p=rf.predict(m,x.iloc[vi]);saved=read_csv(folder/'predictions.csv')
    require(saved.Gender.tolist()==pairs.iloc[vi].Gender.tolist(),'Replay gender changed')
    require(np.array_equal(saved[cf.KEYS[1:]].to_numpy(),pairs.iloc[vi][cf.KEYS[1:]].to_numpy()),'Replay identity/order changed')
    require(np.array_equal(saved.y.to_numpy(),y[vi]) and np.max(abs(saved.probability.to_numpy()-p))<1e-12,'Replay prediction changed')
    rev=x.iloc[vi].copy();rev[cols]=-rev[cols]
    require(np.max(abs(p+rf.predict(m,rev)-1))<1e-10,'Probability swap failure')
    metric=normalize_metric(read_json(folder/'metrics.json'),y[vi],p,'M',s)
    return metric,m,saved


RATING_FILES=['teams.csv','model.json','diagnostics.json']



def audit(ctx):
    compact=read_csv(ctx['raw']/'MRegularSeasonCompactResults.csv')
    detailed=read_csv(ctx['raw']/'MRegularSeasonDetailedResults.csv')
    rows=[];team_rows=[];bad_rows=[];errors=[]
    for season in fr.YEARS:
        d=detailed.loc[detailed.Season.eq(season)&detailed.DayNum.le(132)].copy()
        bad,teams,excluded,summary=fr.turnover_quality(d)
        _,_,pairs=upstream_tables(ctx,season)
        seeded=sorted(set(pairs.Team1ID)|set(pairs.Team2ID))
        teams['Season']=season;teams['seeded']=teams.TeamID.isin(seeded)
        summary.update(Season=season,maximum_seeded_exclusion=float(teams.loc[teams.seeded,'excluded_fraction'].max()))
        try:
            long=fr.legal_long(compact,detailed,season,'16');fr.seeded_quality_gate(long,seeded)
            summary['status']='PASS_REVISED_POLICY'
        except ValueError as exc:
            summary['status']='STOP';summary['error']=str(exc);errors.append({'Season':season,'error':str(exc)})
        rows.append(summary);team_rows.append(teams);bad_rows.append(excluded)
        event('quality_audit_season',season=season,**{k:v for k,v in summary.items() if k!='Season'})
    out=ctx['directory'];atomic_csv(out/'data_quality.csv',pd.DataFrame(rows))
    atomic_csv(out/'data_quality_teams_private.csv',pd.concat(team_rows,ignore_index=True))
    atomic_csv(out/'excluded_games_private.csv',pd.concat(bad_rows,ignore_index=True))
    atomic_json(out/'quality_audit.json',{'status':'PASS' if not errors else 'STOP','errors':errors,
        'policy':fr.QUARANTINE_POLICY,'fingerprint':ctx['fingerprint'],'audit_sha256':sha(out/'data_quality.csv'),'project_models_fitted':0,'source_scope':'regular-season detailed only'})
    preservation(ctx)
    require(not errors,'Revised quality-policy gate failed; no models fitted. Inspect data_quality.csv')


def build_seasons(ctx, seasons):
    out=ctx['directory'];rid=ctx['round']
    if rid=='16':
        audit_record=read_json(safe_file(out,'quality_audit.json'))
        require(audit_record['status']=='PASS' and audit_record['fingerprint']==ctx['fingerprint'] and audit_record['audit_sha256']==sha(out/'data_quality.csv'),'Run/verify the all-season audit first')
    new_ratings=0;reused_ratings=0;new_snapshots=0
    compact=read_csv(ctx['raw']/'MRegularSeasonCompactResults.csv')
    detailed=read_csv(ctx['raw']/'MRegularSeasonDetailedResults.csv')
    for i,s in enumerate(seasons):
        folder=out/f'snapshots/M_{s}'
        if not checkpoint(folder,SNAP_FILES):
            base,_,pairs=upstream_tables(ctx,s)
            seeded=sorted(set(pairs.Team1ID)|set(pairs.Team2ID))
            long=fr.legal_long(compact,detailed,s,rid)
            fr.seeded_quality_gate(long,seeded)
            tables=[]
            for target in fr.FAMILIES[rid]:
                dest=out/f'ratings/M_{s}_{target}'
                if checkpoint(dest,RATING_FILES):
                    table=read_csv(dest/'teams.csv');reused_ratings+=1
                else:
                    require(new_ratings<config(rid)['rating_fit_cap'],'Rating fit cap reached')
                    event('rating_fit_started',round=rid,season=s,target=target,completed=new_ratings+reused_ratings,total=2*len(seasons))
                    table,model,diagnostic=fr.fit_target(long,target,seeded)
                    atomic_csv(dest/'teams.csv',table);atomic_json(dest/'model.json',model)
                    atomic_json(dest/'diagnostics.json',diagnostic);seal(dest,RATING_FILES);new_ratings+=1
                tables.append(table)
            built,prof,cov,support=fr.pair_tables(base,pairs,tables,rid)
            for n,f in [('matchups.csv',built),('profiles.csv',prof),('coverage.csv',cov),('support.csv',support)]:atomic_csv(folder/n,f)
            seal(folder,SNAP_FILES);new_snapshots+=1
        else:
            for target in fr.FAMILIES[rid]:
                require(checkpoint(out/f'ratings/M_{s}_{target}',RATING_FILES),'Missing accepted rate model')
                reused_ratings+=1
        event('snapshot_complete',round=rid,season=s,completed=i+1,total=len(seasons),new_snapshots=new_snapshots,
              new_rating_fits=new_ratings,rating_reuses=reused_ratings)
    return {'new_rating_fits':new_ratings,'rating_reuses':reused_ratings,'new_feature_snapshots':new_snapshots,
            'feature_snapshot_reuses':len(seasons)-new_snapshots}


def smoke(ctx):
    # Only the earliest training season: fails before a complete research run.
    counts=build_seasons(ctx,[2013]);preservation(ctx)
    atomic_json(ctx['directory']/'smoke.json',dict(status='PASS_TECHNICAL_SMOKE',round=ctx['round'],
        season=2013,new_classifier_fits=0,quality_improvement_claim=False,**counts))


def prepare(ctx):
    out=ctx['directory'];rid=ctx['round']
    require(read_json(safe_file(out,'smoke.json')).get('status')=='PASS_TECHNICAL_SMOKE','Run the one-season smoke stage first')
    counts=build_seasons(ctx,fr.YEARS)
    bundle=matrices(ctx);replays=[]
    for s in fr.VALIDATION:
        metric,_,_=replay(ctx['consensus']/f'fits/M_{s}_anchor_consensus',fr.BASE,s,bundle)
        target=ctx['prior_metrics'].query("Season==@s and recipe=='anchor_consensus'").brier.iloc[0]
        require(abs(metric['brier']-target)<1e-12,'Published consensus replay differs')
        replays.append({'Season':s,'recipe':'reference','brier':metric['brier'],'status':'VERIFIED_NO_REFIT'})
    profiles=pd.concat([read_csv(out/f'snapshots/M_{s}/profiles.csv') for s in fr.YEARS],ignore_index=True)
    coverage=pd.concat([read_csv(out/f'snapshots/M_{s}/coverage.csv') for s in fr.YEARS],ignore_index=True)
    diagnostics=pd.DataFrame([read_json(out/f'ratings/M_{s}_{t}/diagnostics.json') for s in fr.YEARS for t in fr.FAMILIES[rid]])
    for n,f in [('coverage.csv',coverage),('profiles.csv',profiles),('feature_registry.csv',fr.registry(rid)),
                ('prior_replay.csv',pd.DataFrame(replays)),('label_audit.csv',bundle[3]),('rating_diagnostics.csv',diagnostics)]:atomic_csv(out/n,f)
    atomic_json(out/'prepare.json',dict(status='COMPLETE',round=rid,base_snapshots_reused=12,
        reference_models_replayed=4,new_candidate_definitions=4,unadjusted_rate_controls=4,
        new_classifier_fits=0,smoke_work_included_in_reuses=True,**counts))
    preservation(ctx);stage_seal(out,'prepare',PREP_FILES)


def effects_table(metrics,rid):
    wide=metrics.pivot(index='Season',columns='recipe',values='brier').sort_index();a,b=fr.FAMILIES[rid]
    comparisons={'adjustment_given_rates':('both','rates'),'rates_given_reference':('rates','reference'),
        a+'_given_rates':(a,'rates'),b+'_given_rates':(b,'rates'),
        a+'_given_'+b:('both',b),b+'_given_'+a:('both',a),
        'both_given_duplicate':('both','duplicate_control'),'duplicate_given_rates':('duplicate_control','rates'),
        'both_given_reference':('both','reference')}
    return pd.DataFrame([{'Season':int(s),'comparison':n,'delta_brier':float(wide.loc[s,l]-wide.loc[s,r])}
                        for n,(l,r) in comparisons.items() for s in wide.index])


def decision(effects,rid):
    t=config(rid)['thresholds'];v=effects.query("comparison=='adjustment_given_rates'").sort_values('Season')
    require(v.Season.tolist()==fr.VALIDATION and np.isfinite(v.delta_brier).all(),'Incomplete primary comparison')
    d=v.delta_brier.to_numpy();dup=effects.query("comparison=='both_given_duplicate'").delta_brier.to_numpy()
    require(len(dup)==4 and np.isfinite(dup).all(),'Missing duplicate-input comparison')
    ok=d.mean()<=t['mean_delta'] and (d<0).sum()>=t['improved_seasons'] and d.max()<=t['worst_delta']
    return {'comparison':'adjustment_given_rates','mean_delta':float(d.mean()),'improved_seasons':int((d<0).sum()),
        'worst_delta':float(d.max()),'thresholds':t,'mean_delta_vs_duplicate':float(dup.mean()),
        'duplication_sensitivity_pass':bool(dup.mean()<0),
        'decision':'CONSIDER_PRODUCTION_TRANSFER' if ok and dup.mean()<0 else 'DO_NOT_PROMOTE',
        'automatic_promotion':False,'significance_claim':False,'validation_seasons':fr.VALIDATION}



def evaluate(ctx):
    out=ctx['directory'];rid=ctx['round'];stage_check(out,'prepare',PREP_FILES)
    for s in fr.YEARS:require(checkpoint(out/f'snapshots/M_{s}',SNAP_FILES),'Incomplete feature table')
    bundle=matrices(ctx);pairs,y,x,_=bundle;rows=[];preds=[];coefs=[];overlap=[];new=0;reuse=0
    rc=fr.recipes(rid)
    for s in fr.VALIDATION:
        ti,vi=rf.split_indices(x,s)
        for recipe,cols in rc.items():
            folder=out/f'fits/M_{s}_{recipe}'
            if recipe=='reference':
                metric,m,pred=replay(ctx['consensus']/f'fits/M_{s}_anchor_consensus',cols,s,bundle);origin='upstream_replay'
            elif checkpoint(folder,FIT_FILES):
                metric,m,pred=replay(folder,cols,s,bundle);reuse+=1;origin='local_reuse'
            else:
                require(new<config(rid)['fit_cap'],'New-fit cap reached')
                m=rf.fitted_model(x.iloc[ti],y[ti],cols);m['train_seasons']=[z for z in fr.YEARS if z<s]
                p=rf.predict(m,x.iloc[vi]);require(((p>0)&(p<1)).all(),'Non-interior probabilities')
                metric={'Gender':'M','Season':s,'games':len(vi),'brier':float(np.mean((p-y[vi])**2)),
                        'log_loss':float(-np.mean(y[vi]*np.log(p)+(1-y[vi])*np.log1p(-p)))}
                pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=p
                atomic_json(folder/'model.json',m);atomic_json(folder/'metrics.json',metric);atomic_csv(folder/'predictions.csv',pred)
                seal(folder,FIT_FILES);new+=1;origin='new_fit'
                metric,m,pred=replay(folder,cols,s,bundle)
            row={k:metric[k] for k in ['Gender','Season','games','brier','log_loss']}
            rows.append(dict(row,recipe=recipe,train_games=len(ti),train_last_season=int(x.iloc[ti].Season.max()),
                feature_count=len(cols),active_features=len(m['active_indices']),source=origin,evidence=config(rid)['scope']))
            pred=pred.copy();pred['recipe']=recipe;pred['squared_error']=(pred.probability-pred.y)**2;preds.append(pred)
            for i,j in enumerate(m['active_indices']):
                coefs.append({'Season':s,'recipe':recipe,'feature':cols[j],'coefficient':m['coefficients'][i]})
            event('comparison_complete',round=rid,season=s,recipe=recipe,brier=row['brier'],source=origin,completed=len(rows),total=24)
        control_cols=fr.BASE+fr.CONTROLS[rid]
        corr=x.iloc[ti][control_cols+fr.FEATURES[rid]].corr()
        for f in fr.FEATURES[rid]:
            c=corr.loc[f,control_cols].abs().dropna();best=c.idxmax() if len(c) else ''
            overlap.append({'Season':s,'feature':f,'closest_reference_or_rate':best,'abs_correlation':float(c.max()) if len(c) else 0.,
                            'training_games':len(ti),'training_nonzero':int((x.iloc[ti][f].abs()>1e-12).sum())})
    m=pd.DataFrame(rows);m=m.merge(m.query("recipe=='reference'")[['Season','brier']].rename(columns={'brier':'anchor_brier'}),on='Season',validate='many_to_one')
    m['delta_vs_anchor']=m.brier-m.anchor_brier;effects=effects_table(m,rid);d=decision(effects,rid);p=pd.concat(preds,ignore_index=True)
    cal=p.copy();cal['bin']=np.minimum((cal.probability*10).astype(int),9)
    cal=cal.groupby(['recipe','bin']).agg(games=('y','size'),mean_probability=('probability','mean'),observed_fraction=('y','mean')).reset_index()
    ag=m.groupby('recipe').agg(seasons=('Season','nunique'),games=('games','sum'),mean_brier=('brier','mean'),mean_log_loss=('log_loss','mean'),mean_delta=('delta_vs_anchor','mean')).reset_index()
    ag['game_weighted_brier']=[np.average(m.loc[m.recipe.eq(r),'brier'],weights=m.loc[m.recipe.eq(r),'games']) for r in ag.recipe]
    primary=effects.query("comparison=='adjustment_given_rates'")
    sens=pd.DataFrame([{'omitted_season':s,'remaining_mean_delta':float(primary.loc[primary.Season.ne(s),'delta_brier'].mean())} for s in fr.VALIDATION])
    ref=p.query("recipe=='rates'").copy();both=p.query("recipe=='both'")
    paired=ref.merge(both[cf.KEYS+['probability','squared_error']],on=cf.KEYS,validate='one_to_one',suffixes=('_ref','_both'))
    paired['confidence_bin']=np.minimum((paired.probability_ref*10).astype(int),9)
    paired['loss_delta']=paired.squared_error_both-paired.squared_error_ref
    bins=paired.groupby('confidence_bin').agg(games=('y','size'),mean_delta=('loss_delta','mean'),total_delta=('loss_delta','sum')).reset_index()
    support=pd.concat([read_csv(out/f'snapshots/M_{s}/support.csv') for s in fr.VALIDATION],ignore_index=True)
    diagnosed=paired.merge(support,on=cf.KEYS,validate='one_to_one');col='minimum_exposure'
    diagnosed['support_bin']=pd.cut(diagnosed[col],bins=[-1,50,500,1000,2000,np.inf],labels=['below 50','50-500','500-1000','1000-2000','2000+'],include_lowest=True)
    diag=diagnosed.groupby('support_bin',observed=True).agg(games=('y','size'),mean_delta=('loss_delta','mean')).reset_index()
    for n,f in [('metrics.csv',m),('predictions.csv',p),('ablations.csv',effects),('coefficients.csv',pd.DataFrame(coefs)),
       ('calibration.csv',cal),('training_overlap.csv',pd.DataFrame(overlap)),('aggregate.csv',ag),('season_sensitivity.csv',sens),
       ('paired_loss_bins.csv',bins),('support_diagnostics.csv',diag)]:atomic_csv(out/n,f)
    receipt={'round':rid,'new_classifier_fits':new,'local_reuses':reuse,'reference_replays':4,'total_comparisons':24,
        'new_rating_fits':0,'validation_seasons':fr.VALIDATION}
    rng=np.random.default_rng(20260912)
    delta=primary.sort_values('Season').delta_brier.to_numpy(dtype=float)
    boots=delta[rng.integers(0,len(delta),size=(2000,len(delta)))].mean(axis=1)
    atomic_json(out/'season_bootstrap.json',{'resampling_unit':'season','seasons':4,'replicates':2000,
        'mean_delta':float(delta.mean()),'percentile_interval_95':np.quantile(boots,[.025,.975]).tolist(),
        'interpretation':'Exploratory four-season bootstrap; reused data, small cluster count, no multiple-testing correction'})
    atomic_json(out/'evaluation_receipt.json',receipt);atomic_json(out/'decisions.json',d)
    atomic_json(out/'summary.json',dict(status='COMPLETE',fingerprint=ctx['fingerprint'],**receipt,decision=d,
        current_submitted_brier=.1222672,research_target_brier=.1097454,new_candidate_definitions=4,new_leaderboard_score=None,
        github_updated=False,repository_modified=False,aws_resources_modified=False,
        limitations=['Previously used later-era history, not untouched holdout','Men-only main draw, not full competition evaluation',
        'Fixed compact logistic, not the final pooled 128-input XGBoost recipe','Four unadjusted controls and four duplicated controls are not novel candidate definitions',
        'Rounds 16 and 17 are independent; no cross-round selection or ensemble',
        'Correlations and duplicated-input control do not establish causal or independent predictive information']))
    preservation(ctx);stage_seal(out,'evaluation',EVAL_FILES)


def report(ctx):
    from round_plots import render
    out=ctx['directory'];stage_check(out,'prepare',PREP_FILES);stage_check(out,'evaluation',EVAL_FILES)
    html=render(out,ctx['round'],ctx['kit']/'evidence');preservation(ctx)
    atomic_json(out/'executed_tests.json',read_json(ctx['kit']/'reports/test_receipt.json'))
    stats=ctx['reports']/'stage_telemetry.json'
    atomic_json(out/'execution_telemetry.json',{'stages_before_report_finished':read_json(stats) if stats.is_file() else {},
        'scope':'Supervisor telemetry available at report start; no invented measurements for direct test calls'})
    quality_names=(['migration.json'] if (out/'migration.json').is_file() else [])+['data_quality.csv','quality_audit.json'] if ctx['round']=='16' else []
    names=quality_names+[n for n in EVAL_FILES if n!='predictions.csv']+[n for n in PREP_FILES if n!='profiles.csv']+['preflight.json','manifest.json','prepare_hashes.json','evaluation_hashes.json','executed_tests.json','execution_telemetry.json']
    dest=ctx['reports']/f"milestone_{ctx['round']}_return.zip";tmp=dest.with_suffix('.zip.partial')
    require(not dest.is_symlink() and not tmp.is_symlink(),'Unsafe report output')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for n in names:z.write(safe_file(out,n),n)
        z.writestr('return_integrity.json',json.dumps({'sha256':{n:sha(out/n) for n in names},
             'excluded':['raw rows','fitted models','per-game predictions','team profiles','private edited notebooks']},indent=2))
    os.replace(tmp,dest)
    atomic_json(ctx['reports']/'latest_report.json',{'status':'COMPLETE','return_zip':str(dest),'return_sha256':sha(dest),'html':str(html),'plotly_figures':10})
    event('report_complete',round=ctx['round'],return_zip=str(dest),plotly_figures=10)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('round',choices=['16','17']);parser.add_argument('stage',choices=['audit','smoke','prepare','evaluate','report']);a=parser.parse_args()
    kit=Path(__file__).resolve().parent;home=Path.home()
    paths={'kit':kit,'repo':Path(os.environ.get('MARCH_REPO',home/'march-machine-learning-mania-2026')),
      'shooting':Path(os.environ.get('MARCH_SHOOTING_KIT',home/'march_shooting_research')),
      'rankings':Path(os.environ.get('MARCH_RANKINGS_KIT',home/'march_ranking_matchups')),
      'consensus':Path(os.environ.get('MARCH_CONSENSUS_KIT',home/'march_consensus_validation')),'round_id':a.round}
    event('stage_start',round=a.round,stage=a.stage)
    try:ctx=preflight(**paths);globals()[a.stage](ctx);event('stage_complete',round=a.round,stage=a.stage)
    except Exception as e:
        reports=kit/'reports'/('round'+a.round);output_dir(reports)
        atomic_json(reports/'failure.json',{'status':'STOP','round':a.round,'stage':a.stage,'error_type':type(e).__name__,'error':str(e),'completed_checkpoints_preserved':True})
        raise
if __name__=='__main__':main()
