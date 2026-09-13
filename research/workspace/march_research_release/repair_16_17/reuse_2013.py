"""User-run provenance-bound migration; no model fitting and no changes to the old kit."""
from pathlib import Path
import ast,fcntl,hashlib,json,os,shutil
_kit=Path(__file__).resolve().parent
_pins=json.loads((_kit/'MANIFEST.json').read_text())['sha256']
for _name in ['reuse_2013.py','original_source_hashes.json']:
    if hashlib.sha256((_kit/_name).read_bytes()).hexdigest()!=_pins.get(_name):
        raise ValueError('Migration source changed: '+_name)
import round_workflow as w
import feature_rounds as f

def function_signature(path,names):
    tree=ast.parse(path.read_text())
    return {n:ast.dump(next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==n),include_attributes=False) for n in names}

def migrate(ctx,old):
    old=Path(old).expanduser().absolute();pins=w.read_json(ctx['kit']/'original_source_hashes.json')
    for name,h in pins.items():w.require(w.sha(w.safe_file(old,name))==h,'Original scientific source changed: '+name)
    w.require(function_signature(old/'feature_rounds.py',['fit_target','pair_tables'])==function_signature(ctx['kit']/'feature_rounds.py',['fit_target','pair_tables']),'Fitting or matchup mathematics changed')
    prior=w.read_json(w.safe_file(old,'reports/round16/latest_run.json'))
    run=Path(prior['run_dir']);w.require(run.is_relative_to(old/'private_runs/round16'),'Unexpected original run path')
    before=w.read_json(w.safe_file(run,'manifest.json'))
    for key in ['data','environment','upstream_files','upstream_fingerprints','reference_commit']:
        w.require(before[key]==ctx['identity'][key],'Original run input/provenance mismatch: '+key)
    w.require(before['source']==pins,'Original manifest source does not match reviewed version')
    c=w.read_csv(ctx['raw']/'MRegularSeasonCompactResults.csv');d=w.read_csv(ctx['raw']/'MRegularSeasonDetailedResults.csv')
    long=f.legal_long(c,d,2013,'16')
    w.require(long.attrs['turnover_quality']['excluded_physical_games']==0,'2013 would change under quality policy; no migration')
    copies=[]
    for rel,names in [(f'ratings/M_2013_{t}',w.RATING_FILES) for t in f.FAMILIES['16']]+[('snapshots/M_2013',w.SNAP_FILES)]:
        source=run/rel;dest=ctx['directory']/rel
        w.require(w.checkpoint(source,names),'Missing accepted 2013 checkpoint')
        for name in names+['complete.json']:
            src=w.safe_file(source,name);target=dest/name;w.output_dir(dest)
            if target.exists():w.require(w.sha(target)==w.sha(src),'Different destination checkpoint; stop')
            else:
                tmp=target.with_suffix(target.suffix+'.partial');w.require(not tmp.is_symlink(),'Unsafe partial')
                shutil.copy2(src,tmp);os.replace(tmp,target)
            w.require(w.sha(src)==w.sha(target),'Copied bytes changed');copies.append({'path':rel+'/'+name,'sha256':w.sha(src)})
        w.require(w.checkpoint(dest,names),'Migrated checkpoint check failed')
    record={'status':'MIGRATED_IDENTICAL_2013','ratings_reused':2,'snapshots_reused':1,'models_fitted':0,
        'original_fingerprint':prior['fingerprint'],'policy':f.QUARANTINE_POLICY,'copied':copies,'source_kit_modified':False}
    w.atomic_json(ctx['directory']/'migration.json',record);w.preservation(ctx);return record

if __name__=='__main__':
    home=Path.home();kit=Path(__file__).resolve().parent;w.output_dir(kit/'reports')
    with (kit/'reports/execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ctx=w.preflight(kit,home/'march-machine-learning-mania-2026',home/'march_shooting_research',home/'march_ranking_matchups',home/'march_consensus_validation','16')
        w.require(w.read_json(ctx['directory']/'quality_audit.json')['status']=='PASS','Audit all seasons before migrating')
        print(json.dumps(migrate(ctx,home/'march_feature_rounds_16_17'),indent=2))
