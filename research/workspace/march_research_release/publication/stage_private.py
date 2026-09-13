"""User-run private source snapshot, not a public export or a project runner."""
from pathlib import Path
import argparse,json,hashlib,os,re,time
ROOTS=['march-machine-learning-mania-2026','march_workspace_sync','march_feature_audit','march_feature_research',
 'march_shooting_research','march_schedule_research','march_record_validation','march_temporal_form',
 'march_temporal_validation','march_possession_research','march_bracket_context','march_win_strength',
 'march_win_strength_recovery','march_margin_research','march_ranking_matchups','march_consensus_validation',
 'march_feature_rounds_14_15','march_feature_rounds_16_17','march_research_release']
SKIP={'.git','.venv','__pycache__','.ipynb_checkpoints','data','private_runs','models','submissions',
 'reports','staging','public_portfolio','node_modules','.github','work_current','tests_output'}
EXT={'.py','.ipynb','.md','.json','.yaml','.yml','.toml','.lock','.txt','.cfg','.cff','.sh','.csv'}
SENSITIVE=re.compile(r'(?:AKIA|ASIA)[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|X-Amz-Signature=[a-fA-F0-9]{32,}|["\x27](?:api_key|access_token|secret_key)["\x27]\s*[:=]\s*["\x27][A-Za-z0-9/+_=.-]{20,}')
def sha(b):return hashlib.sha256(b).hexdigest()
def stage(home,destination):
    home=Path(home).expanduser().resolve();dest=Path(destination).expanduser().absolute()
    if dest.exists():raise ValueError('Destination exists. Preserve it and use a new timestamped snapshot.')
    if any(dest.is_relative_to(home/n) for n in ROOTS):raise ValueError('Snapshot must be outside every source tree')
    if any(p.is_symlink() for p in dest.parents):raise ValueError('Symlink destination refused')
    dest.mkdir(parents=True,mode=0o700);records=[];blocked=[];missing=[];total=0;started=time.monotonic();last=started
    for root_name in ROOTS:
        root=home/root_name
        if not root.exists():missing.append(root_name);continue
        if root.is_symlink():raise ValueError('Symlink source refused')
        for directory,dirs,files in os.walk(root,followlinks=False):
            dirs[:]=[d for d in dirs if d not in SKIP and not (Path(directory)/d).is_symlink()]
            for name in sorted(files):
                now=time.monotonic()
                if now-started>180:raise TimeoutError('Snapshot limit 180 seconds; original sources unchanged; do not publish incomplete snapshot')
                if now-last>=15:
                    print(json.dumps({'event':'source_snapshot_progress','files':len(records),'bytes':total,'elapsed_seconds':round(now-started,1)}),flush=True);last=now
                p=Path(directory)/name;rel=p.relative_to(root)
                if p.is_symlink():blocked.append({'path':str(Path(root_name)/rel),'reason':'symlink omitted'});continue
                if p.suffix not in EXT and p.name not in {'LICENSE','.gitignore','.python-version','.gitattributes'}:continue
                # CSV copying is restricted to supplied/evidential tables, not arbitrary data exports.
                if p.suffix=='.csv' and 'evidence' not in rel.parts:continue
                if p.stat().st_size>(30_000_000 if p.suffix=='.ipynb' else 3_000_000):blocked.append({'path':str(Path(root_name)/rel),'reason':'source over review-size limit'});continue
                raw=p.read_bytes();b=raw
                if p.suffix=='.ipynb':
                    n=json.loads(raw)
                    for cell in n.get('cells',[]):
                        if cell.get('cell_type')=='code':cell['outputs']=[];cell['execution_count']=None
                    b=(json.dumps(n,indent=1)+'\n').encode()
                if len(b)>3_000_000:blocked.append({'path':str(Path(root_name)/rel),'reason':'staged source over 3 MB requires review'});continue
                if SENSITIVE.search(b.decode('utf-8',errors='replace')) or p.name in {'.env','kaggle.json','credentials'}:
                    blocked.append({'path':str(Path(root_name)/rel),'reason':'possible secret; content omitted; review locally'});continue
                total+=len(b)
                if total>250_000_000 or len(records)>=10000:raise ValueError('Private source-review budget exceeded; no Git operation was run')
                target=dest/'research'/root_name/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
                records.append({'path':str(target.relative_to(dest)),'source_sha256':sha(raw),'staged_sha256':sha(b),'outputs_removed':p.suffix=='.ipynb'})
    status='REVIEW_BLOCKED' if blocked else 'SOURCE_SNAPSHOT_READY_FOR_PRIVATE_REVIEW'
    receipt={'status':status,'files':records,'blocked':blocked,'missing_known_roots':missing,
        'excluded_directories':sorted(SKIP),'raw_models_and_original_executed_notebooks':'Preserved in original AWS locations; not Git content',
        'evidence':'Small already-supplied evidence tables may be included; not a complete experiment-artifact backup',
        'git_writes':False,'secret_scan':'Heuristic, not comprehensive; manual review required'}
    (dest/'PRIVATE_SNAPSHOT.json').write_text(json.dumps(receipt,indent=2))
    (dest/'README.md').write_text('# Private NCAA research source\n\nSource, tests, configurations, protocols and small evidence tables. Original datasets, models, executed notebook outputs and complete old Git history remain in their protected original locations. See PRIVATE_SNAPSHOT.json for exclusions and hashes. The snapshots are for versioning; continue scientific execution in the original AWS layout until path/manifest migration is explicitly designed. Original MIT licenses and third-party notices remain applicable.\n')
    print(json.dumps({'status':status,'files_staged':len(records),'blocked_files':len(blocked),'path':str(dest)},indent=2))
    if blocked:raise SystemExit('STOP: review PRIVATE_SNAPSHOT.json. Do not push yet.')
    return dest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--home',default=str(Path.home()));p.add_argument('--destination',required=True);a=p.parse_args();stage(a.home,a.destination)
