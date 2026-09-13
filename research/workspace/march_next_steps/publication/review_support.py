"""Publication-only receipts, redacted blocker inspection and a process lock."""
from __future__ import annotations
import contextlib
import hashlib
import json
import os
import time
import zipfile
from pathlib import Path
from publication.stage_private import SENSITIVE, generated_dir, documented_environment

UPDATE_ID='publication-tools-environment-20260912'

def safe_path(p):
    p=Path(p)
    if p.is_symlink() or any(q.is_symlink() for q in p.parents): raise ValueError('Symlink refused: '+p.name)
    return p

def atomic(path,obj):
    path=safe_path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=safe_path(path.with_name(path.name+'.partial'))
    temporary.write_text(json.dumps(obj,indent=2)+'\n');os.chmod(temporary,0o600);temporary.replace(path)

def clean(value): return SENSITIVE.sub('[REDACTED]',str(value))

def inspect_previous(home):
    """Metadata only. Never reads the contents of a flagged source file."""
    home=Path(home);root=safe_path(home/'march_publication/plans')
    candidates=sorted(root.glob('*/private_source/PRIVATE_SNAPSHOT.json')) if root.exists() else []
    records=[]
    for p in candidates[-12:]:
        safe_path(p)
        if p.stat().st_size>20_000_000: raise ValueError('Snapshot metadata too large to inspect safely')
        raw=json.loads(p.read_text());blockers=[]
        for row in raw.get('blocked',[]):
            name=str(row.get('path',''));rel=Path(name)
            category='ACTIVE_SOURCE_REVIEW_REQUIRED'
            if not rel.is_absolute() and '..' not in rel.parts and (documented_environment(rel) or any(generated_dir(v) for v in rel.parts[:-1])):
                category='EXCLUDED_BY_DOCUMENTED_DIRECTORY_POLICY'
            blockers.append({'path':clean(name),'reason':clean(row.get('reason','not recorded')),
                'classification':category})
        records.append({'plan':p.parent.parent.name,'status':raw.get('status'),'staged_files':len(raw.get('files',[])),
            'blocked_files':len(blockers),'blockers':blockers})
    return {'update_id':UPDATE_ID,'status':'FOUND' if records else 'NO_LOCAL_PLAN_FOUND',
        'plans':records,'source_contents_read':False,'remote_calls':0}

def show_inspection(home):
    obj=inspect_previous(home)
    print(json.dumps(obj,indent=2));atomic(Path(home)/'march_publication/blocker_review.json',obj)
    return obj

def diagnostic(home,extra=None):
    """Small return bundle; excludes source, token config and terminal transcripts."""
    home=Path(home);root=safe_path(home/'march_publication');root.mkdir(exist_ok=True,mode=0o700)
    payload=inspect_previous(home)
    if extra: payload['operation']={k:clean(v) for k,v in extra.items()}
    atomic(root/'publication_diagnostic.json',payload)
    output=safe_path(root/'publication_diagnostic.zip');tmp=safe_path(output.with_name(output.name+'.partial'))
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        z.write(root/'publication_diagnostic.json','publication_diagnostic.json')
        for n in ['publication_test_receipt.json','publication_update.json']:
            p=root/n
            if p.is_file() and not p.is_symlink() and p.stat().st_size<2_000_000:z.write(p,n)
    os.chmod(tmp,0o600);tmp.replace(output)
    print('DIAGNOSTIC:',output)
    return output

@contextlib.contextmanager
def lock(home):
    import fcntl
    root=safe_path(Path(home)/'march_publication');root.mkdir(exist_ok=True,mode=0o700)
    p=safe_path(root/'publication.lock')
    with p.open('a') as f:
        try: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise RuntimeError('Another publication command is running; no changes made')
        try: yield
        finally: fcntl.flock(f,fcntl.LOCK_UN)

def public_test_fingerprints(root):
    root=Path(root);names=['github_publish.py','publication/stage_private.py','publication/review_support.py',
        'run_publication_tests.py','PUBLIC_MANIFEST.json']
    names += [str(p.relative_to(root)) for p in sorted((root/'tests').glob('test*.py'))]
    return {n:hashlib.sha256(safe_path(root/n).read_bytes()).hexdigest() for n in names}

def require_test_receipt(root,home):
    p=safe_path(Path(home)/'march_publication/publication_test_receipt.json')
    if not p.is_file(): raise ValueError('Run python3 run_publication_tests.py first; no remote write attempted')
    r=json.loads(p.read_text())
    if r.get('status')!='PASS' or r.get('source_sha256')!=public_test_fingerprints(root):
        raise ValueError('Publication tests are absent, failed, or stale; run run_publication_tests.py')
