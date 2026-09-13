"""Prepare a private source snapshot; never publish or import project code.

The caller receives a receipt even when some source files are blocked. Known
build/type-check caches are excluded, not deleted. Unresolved source blockers
are NOT automatically waived. Original bytes are never edited.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import time
from collections import Counter
from pathlib import Path

ROOTS=['march-machine-learning-mania-2026','march_workspace_sync','march_feature_audit','march_feature_research',
 'march_shooting_research','march_schedule_research','march_record_validation','march_temporal_form',
 'march_temporal_validation','march_possession_research','march_bracket_context','march_win_strength',
 'march_win_strength_recovery','march_margin_research','march_ranking_matchups','march_consensus_validation',
 'march_feature_rounds_14_15','march_feature_rounds_16_17','march_research_release','march_next_steps']
HOME_FILES=['00_resume_milestone_10.ipynb','apply_notebook_update.py','apply_possession_update.py',
 'apply_win_strength_update.py','resume_milestone_10.py']
# Exact generated-directory names only: do not use a broad "cache" substring.
CACHE_DIRS={'.mypy_cache','.ruff_cache','.pytest_cache','.cache','.tox','.nox',
 '__pycache__','.ipynb_checkpoints','.eggs','__pypackages__','htmlcov','node_modules'}
SKIP={'.git','.venv','venv','env','data','private_runs','models','submissions','reports','outputs',
 'staging','checkouts','publish_plans','march_publication','public_portfolio','.github','work_current',
 'tests_output','build','dist',*CACHE_DIRS}
EXT={'.py','.ipynb','.md','.json','.yaml','.yml','.toml','.lock','.txt','.cfg','.cff','.sh','.csv'}
SENSITIVE=re.compile(r'(?:AKIA|ASIA)[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|X-Amz-Signature=[a-fA-F0-9]{32,}|["\x27](?:api_key|access_token|secret_key)["\x27]\s*[:=]\s*["\x27][A-Za-z0-9/+_=.-]{20,}')
CREDENTIAL_NAMES={'.env','kaggle.json','credentials','hosts.yml','id_rsa','id_ed25519'}
# scripts/bootstrap.py creates this exact directory with `python -m venv`.
# Do not exclude every directory named .tools: only this documented environment.
TOOL_ENVIRONMENT=('march-machine-learning-mania-2026', '.tools')

def documented_environment(path):
    rel=Path(path)
    return (not rel.is_absolute() and '..' not in rel.parts
            and rel.parts[:2] == TOOL_ENVIRONMENT)

LIMITS={'seconds':180,'files':10000,'bytes':250_000_000,'source_file_bytes':3_000_000,'notebook_read_bytes':30_000_000}

def sha(b): return hashlib.sha256(b).hexdigest()
def generated_dir(name):
    return name in SKIP or name.endswith('.egg-info') or name.endswith('.dist-info')

def normalized_notebook(raw):
    """Remove outputs and hidden execution/widget state from the private source copy."""
    n=json.loads(raw)
    if not isinstance(n,dict) or not isinstance(n.get('cells'),list):
        raise ValueError('Invalid notebook structure')
    for cell in n['cells']:
        if not isinstance(cell,dict) or cell.get('cell_type') not in {'code','markdown','raw'}:
            raise ValueError('Invalid notebook cell')
        cell['metadata']={}
        cell.pop('attachments',None)
        if cell['cell_type']=='code': cell['outputs']=[]; cell['execution_count']=None
    n['metadata']={k:v for k,v in n.get('metadata',{}).items() if k in {'kernelspec','language_info'}}
    return (json.dumps(n,indent=1,ensure_ascii=False)+'\n').encode()

def stage(home,destination):
    home=Path(home).expanduser().resolve(); dest=Path(destination).expanduser().absolute()
    if dest.exists(): raise ValueError('Destination exists; preserve the old snapshot')
    if any(dest.is_relative_to(home/n) for n in ROOTS): raise ValueError('Snapshot must be outside source trees')
    if any(p.is_symlink() for p in dest.parents): raise ValueError('Symlink destination refused')
    dest.mkdir(parents=True,mode=0o700)
    records=[]; blocked=[]; missing=[]; excluded=[]; counters=Counter(); total=0
    started=time.monotonic(); last=started; terminal_error=None
    def block(rel,reason,raw_sha256=None):
        row={'path':rel,'reason':reason}
        if raw_sha256 is not None: row['source_sha256']=raw_sha256
        blocked.append(row)
    def process(p,rel):
        nonlocal total,last
        now=time.monotonic()
        if now-started>LIMITS['seconds']: raise TimeoutError('Source snapshot exceeded its 180-second ceiling')
        if now-last>=15:
            print(json.dumps({'event':'source_snapshot_progress','files':len(records),'bytes':total,
                'blocked':len(blocked),'elapsed_seconds':round(now-started,1)}),flush=True); last=now
        if p.is_symlink(): block(rel,'symlink source omitted'); return
        if p.name in CREDENTIAL_NAMES or p.name.startswith('.env.'):
            excluded.append({'path':rel,'reason':'credential-container filename; never publish'}); return
        if p.suffix not in EXT and p.name not in {'LICENSE','.gitignore','.python-version','.gitattributes'}:
            counters['non_source_file']+=1; return
        if p.suffix=='.csv' and 'evidence' not in Path(rel).parts:
            counters['non_evidence_csv']+=1; return
        size=p.stat().st_size
        limit=LIMITS['notebook_read_bytes'] if p.suffix=='.ipynb' else LIMITS['source_file_bytes']
        if size>limit: block(rel,'source over review-size limit'); return
        raw=p.read_bytes()
        try: b=normalized_notebook(raw) if p.suffix=='.ipynb' else raw
        except (ValueError,TypeError,UnicodeError): block(rel,'invalid notebook JSON or schema',sha(raw)); return
        if len(b)>LIMITS['source_file_bytes']:
            block(rel,'staged source over 3 MB requires review',sha(raw)); return
        try: text=b.decode('utf-8')
        except UnicodeError: block(rel,'non-UTF-8 source requires review',sha(raw)); return
        if SENSITIVE.search(text):
            block(rel,'possible secret; matching contents are not printed',sha(raw)); return
        if total+len(b)>LIMITS['bytes'] or len(records)>=LIMITS['files']:
            raise ValueError('Source-review budget exceeded')
        if p.read_bytes()!=raw: raise ValueError('Source changed while reading: '+rel)
        target=dest/'research'/rel; target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(b); os.chmod(target,0o600); total+=len(b)
        records.append({'path':str(target.relative_to(dest)),'source_sha256':sha(raw),'staged_sha256':sha(b),
            'outputs_removed':p.suffix=='.ipynb','metadata_and_attachments_removed':p.suffix=='.ipynb'})
    try:
        for root_name in ROOTS:
            root=home/root_name
            if not root.exists(): missing.append(root_name); continue
            if root.is_symlink(): block(root_name,'symlink source root omitted'); continue
            for directory,dirs,names in os.walk(root,followlinks=False):
                keep=[]
                for name in sorted(dirs):
                    q=Path(directory)/name; rel=str(q.relative_to(home))
                    if documented_environment(rel):
                        excluded.append({'path':rel,'reason':'bootstrap Python environment; excluded without traversal; original preserved'})
                        counters['excluded_tool_environments']+=1
                    elif q.is_symlink(): block(rel,'symlink directory omitted')
                    elif generated_dir(name):
                        excluded.append({'path':rel,'reason':'documented generated/private directory; original preserved'})
                        counters['excluded_directories']+=1
                    else: keep.append(name)
                dirs[:]=keep
                for name in sorted(names):
                    p=Path(directory)/name; process(p,str(p.relative_to(home)))
        for name in HOME_FILES:
            if (home/name).is_file(): process(home/name,'home_helpers/'+name)
    except Exception as exc:
        terminal_error=type(exc).__name__+': '+str(exc)
        block('[snapshot]','Incomplete snapshot: '+terminal_error)
    status='REVIEW_BLOCKED' if blocked else 'SOURCE_SNAPSHOT_READY_FOR_PRIVATE_REVIEW'
    record={'status':status,'files':records,'blocked':blocked,'missing_known_roots':missing,
        'excluded_directories':sorted(SKIP),'exclusions':excluded,'exclusion_counts':dict(counters),
        'total_staged_bytes':total,'elapsed_seconds':round(time.monotonic()-started,3),
        'raw_models_and_original_executed_notebooks':'Preserved in original AWS locations; not Git content',
        'evidence':'Small supplied evidence tables only; not a complete artifact or Git-history backup',
        'git_writes':False,'secret_scan':'Heuristic, not comprehensive; manual review required',
        'terminal_error':terminal_error,'snapshot_policy':'private-source-tools-exclusion-20260912',
        'excluded_environment_paths':['/'.join(TOOL_ENVIRONMENT)]}
    (dest/'PRIVATE_SNAPSHOT.json').write_text(json.dumps(record,indent=2)+'\n')
    (dest/'README.md').write_text('# Private NCAA research source\n\nReviewed source snapshot. See PRIVATE_SNAPSHOT.json for exact file hashes, exclusions and unresolved blockers. Original raw data, full executed notebooks, model checkpoints, and Git history remain in their original locations. Continue scientific execution in the original AWS paths. This snapshot is not a claim of executed tests or a full workspace backup. Prior licenses remain applicable.\n')
    for n in ['PRIVATE_SNAPSHOT.json','README.md']: os.chmod(dest/n,0o600)
    print(json.dumps({'status':status,'files_staged':len(records),'blocked_files':len(blocked),'path':str(dest)},indent=2))
    # Deliberately return even when blocked: the planner must save the actual state.
    return dest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--home',default=str(Path.home()));parser.add_argument('--destination',required=True)
    args=parser.parse_args();out=stage(args.home,args.destination)
    if json.loads((out/'PRIVATE_SNAPSHOT.json').read_text())['blocked']: raise SystemExit(2)
