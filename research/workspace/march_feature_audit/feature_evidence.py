#!/usr/bin/env python3
"""March Mania milestone 1: read-only worktree diagnosis and published feature evidence.

No repository writes, training, pickle loading, networking, dependency installs,
Git pushes, archive restoration, or cloud calls. Outputs live beside the repo.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import html
import io
import json
import os
from pathlib import Path, PurePosixPath
import queue
import re
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone

EXPECTED = '84b8fb36644a6558beded6dad84f5645ea4405d3'
SLUG = 'alvaromendizabal/march-machine-learning-mania-2026'
KIT = Path(__file__).resolve().parent
REPORT_FILES = ('feature_registry.csv', 'feature_usage.csv', 'screening_summary.csv', 'metrics_by_season.csv')
LIMIT_FILE = 32 * 1024**2
LIMIT_TOTAL = 128 * 1024**2
KEY = ['Gender', 'Season', 'block', 'model']

class Stop(RuntimeError):
    pass

def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def save_json(path, value):
    atomic_bytes(Path(path), (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode())

def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.'+path.name+'.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)  # Only our temporary output; never a repository/user file.

def safe_relative(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '.git' in p.parts:
        raise Stop('UNSAFE_RELATIVE_PATH')
    return p

def sha_file(path, run=None):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024*1024), b''):
            if run: run.check()
            h.update(part)
    return h.hexdigest()

class Budget:
    def __init__(self, out, seconds=300):
        self.out = Path(out)
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.directory = self.out/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        self.directory.mkdir(parents=True, exist_ok=False)
        self.closed = threading.Event()
        self.lock = threading.Lock()
        self.worker = threading.Thread(target=self.heartbeat, daemon=True)
        self.worker.start()
        self.event('started', hard_limit_seconds=seconds)
    def check(self):
        if time.monotonic() >= self.deadline:
            raise Stop('TIME_LIMIT: completed checkpoints remain; inspect the summary before retrying.')
    def event(self, event, **kw):
        row = dict(utc=utc(), event=event, elapsed_seconds=round(time.monotonic()-self.started, 3), **kw)
        with self.lock:
            with (self.directory/'events.jsonl').open('a') as f: f.write(json.dumps(row)+'\n')
            print(json.dumps(row), flush=True)
    def heartbeat(self):
        while not self.closed.wait(15): self.event('heartbeat')
    def close(self):
        self.closed.set()
        self.worker.join(timeout=2)
    def command(self, argv, cwd=None, ok=(0,), max_bytes=LIMIT_FILE):
        self.check()
        env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0', GIT_PAGER='cat', PAGER='cat')
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            p = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                                 start_new_session=(os.name=='posix'))
            try:
                p.wait(timeout=min(45, max(0.1, self.deadline-time.monotonic())))
            except BaseException:
                terminate(p)
                raise
            if p.returncode not in ok:
                # Do not print arbitrary stderr/URLs/credentials into shareable output.
                raise Stop('GIT_READ_FAILED: command exited '+str(p.returncode))
            size = stdout.tell()
            if size > max_bytes: raise Stop('READ_SIZE_LIMIT: source preserved; no retry with a larger limit automatically.')
            stdout.seek(0)
            return stdout.read()

def terminate(p):
    if p.poll() is not None: return
    try:
        if os.name=='posix': os.killpg(p.pid, signal.SIGTERM)
        else: p.terminate()
        p.wait(timeout=3)
    except subprocess.TimeoutExpired:
        if os.name=='posix': os.killpg(p.pid, signal.SIGKILL)
        else: p.kill()
        p.wait(timeout=3)
    except ProcessLookupError:
        pass

def git(run, repo, *args, **kwargs):
    return run.command(['git','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false',*args],cwd=repo,**kwargs)

def text(data):
    return data.decode('utf-8', errors='surrogateescape').strip()

def origin_ok(value):
    return value.rstrip('/') in {f'https://github.com/{SLUG}',f'https://github.com/{SLUG}.git',
        f'git@github.com:{SLUG}',f'git@github.com:{SLUG}.git',f'ssh://git@github.com/{SLUG}.git'}

def paths0(data):
    return [x.decode('utf-8',errors='surrogateescape') for x in data.split(b'\0') if x]

def notebook_structure(raw):
    """Strip ONLY runtime outputs/counts/timing; preserve source, tags and other metadata."""
    obj = json.loads(raw)
    if not isinstance(obj,dict) or not isinstance(obj.get('cells'),list):
        raise ValueError('Invalid notebook')
    obj = copy.deepcopy(obj)
    for c in obj['cells']:
        if c.get('cell_type')=='code':
            c.pop('outputs',None)
            c.pop('execution_count',None)
            meta = c.get('metadata',{})
            meta.pop('execution',None)  # Jupyter execution timestamps only.
    return obj

def classify(name, head, index, work, mode_changed=False):
    if head is None or index is None or work is None: return 'added_deleted_or_type_change'
    if head == index == work:
        return 'mode_only' if mode_changed else 'git_metadata_or_filter_change'
    if name.endswith('.ipynb'):
        try:
            if notebook_structure(head)==notebook_structure(index)==notebook_structure(work):
                return 'notebook_outputs_or_execution_only'
        except (ValueError,TypeError,KeyError):
            return 'notebook_requires_review'
        return 'notebook_source_or_metadata_change'
    if name in {'uv.lock','pyproject.toml','.python-version'}: return 'environment_definition_change'
    if name.startswith(('src/','scripts/','tests/','configs/','.github/')): return 'code_or_config_change'
    if name.startswith('reports/'): return 'published_report_change'
    return 'other_tracked_change'

def inspect_worktree(run, repo, expected, backup=True):
    top = text(git(run,repo,'rev-parse','--show-toplevel'))
    if Path(top).resolve()!=repo: raise Stop('REPOSITORY_ROOT_MISMATCH')
    head = text(git(run,repo,'rev-parse','HEAD'))
    if head != expected: raise Stop('REFERENCE_COMMIT_CHANGED: no pull, reset or checkout was performed.')
    if not origin_ok(text(git(run,repo,'remote','get-url','origin'))): raise Stop('UNEXPECTED_ORIGIN')
    operations = []
    for op in ['MERGE_HEAD','CHERRY_PICK_HEAD','REVERT_HEAD','rebase-merge','rebase-apply','BISECT_LOG']:
        p = Path(text(git(run,repo,'rev-parse','--git-path',op)))
        if not p.is_absolute(): p=repo/p
        if p.exists(): operations.append(op)
    flags = [v for v in paths0(git(run,repo,'ls-files','-v','-z')) if v and (v[0].islower() or v[0]=='S')]
    diff_options = ['--no-ext-diff','--no-textconv','--no-renames','--name-only','-z']
    cached = set(paths0(git(run,repo,'diff','--cached',*diff_options,'HEAD','--')))
    workdiff = set(paths0(git(run,repo,'diff',*diff_options,'--')))
    net = set(paths0(git(run,repo,'diff',*diff_options,'HEAD','--')))
    changed = sorted(cached | workdiff | net)
    if len(changed)>500: raise Stop('TOO_MANY_TRACKED_CHANGES: read-only stop; no files modified.')
    rows, preserved = [], []
    saved_bytes=0
    backup_root = run.out.parent/'private_backups'/run.directory.name
    for i,name in enumerate(changed,1):
        run.check(); safe_relative(name)
        mode_changed=False
        htree=paths0(git(run,repo,'ls-tree','-z','HEAD','--',name))
        idx=paths0(git(run,repo,'ls-files','--stage','-z','--',name))
        def read_blob(entry, tree=False):
            if not entry: return None, None
            info=entry[0].split('\t',1)[0].split()
            mode=info[0]; obj=info[2] if tree else info[1]
            if mode not in ('100644','100755'): return None, mode
            size=int(text(git(run,repo,'cat-file','-s',obj)))
            if size>LIMIT_FILE: raise Stop('CHANGED_FILE_TOO_LARGE: nothing overwritten.')
            return git(run,repo,'cat-file','blob',obj), mode
        head_bytes, head_mode = read_blob(htree,True)
        index_bytes, index_mode = read_blob(idx)
        p=repo/name
        symlink=p.is_symlink()
        work_bytes=None; work_mode=None
        if p.exists() and not symlink:
            if not p.resolve().is_relative_to(repo): raise Stop('CHANGED_PATH_ESCAPES_REPOSITORY')
            if p.is_file():
                if p.stat().st_size>LIMIT_FILE: raise Stop('CHANGED_FILE_TOO_LARGE: nothing overwritten.')
                work_bytes=p.read_bytes()
                work_mode='100755' if (p.stat().st_mode & stat.S_IXUSR) else '100644'
        mode_changed = bool(head_mode and (head_mode!=index_mode or head_mode!=work_mode))
        row=dict(path=name, classification='symlink_or_type_change' if symlink else classify(name,head_bytes,index_bytes,work_bytes,mode_changed),
                 staged=name in cached, unstaged=name in workdiff, head_sha256=digest(head_bytes) if head_bytes is not None else None,
                 index_sha256=digest(index_bytes) if index_bytes is not None else None,
                 worktree_sha256=digest(work_bytes) if work_bytes is not None else None,
                 head_mode=head_mode,index_mode=index_mode,worktree_mode=work_mode,symlink=symlink)
        if backup:
            for label,buf in [('worktree',work_bytes),('index',index_bytes)]:
                if buf is None: continue
                saved_bytes+=len(buf)
                if saved_bytes>LIMIT_TOTAL: raise Stop('BACKUP_SIZE_LIMIT: existing files untouched; partial backups remain.')
                dest=backup_root/label/name
                atomic_bytes(dest,buf)
                if sha_file(dest,run)!=digest(buf): raise Stop('BACKUP_CHECKSUM_MISMATCH')
                preserved.append(dict(path=name,version=label,sha256=digest(buf),bytes=len(buf)))
        rows.append(row)
        if i%20==0: run.event('tracked_changes_inspected',completed=i,total=len(changed))
    if backup and rows: save_json(backup_root/'manifest.json',dict(head=head,files=preserved,changes=rows,
            note='Private local backups only. No repository file, index, branch or stash was altered.'))
    state=dict(head=head, branch=text(git(run,repo,'branch','--show-current')),
               changed_files=rows, tracked_change_count=len(rows), hidden_index_flag_count=len(flags),
               in_progress_git_operations=operations, tracked_clean=not rows and not flags and not operations,
               untracked_file_count=len(paths0(git(run,repo,'ls-files','--others','--exclude-standard','-z'))),
               remote_contacted=False, backups_created=bool(backup and rows), backup_file_versions=len(preserved))
    if backup and rows: state['private_backup_directory']=str(backup_root)
    return state

def revalidate_data(run,repo,prior):
    p=prior/'milestone_summary.json'
    if not p.is_file(): raise Stop('PRIOR_SUMMARY_MISSING: keep the original sync kit and reports.')
    summary=json.loads(p.read_text())
    checks={
        'previous_head_matches':summary.get('head')==text(git(run,repo,'rev-parse','HEAD')),
        'canonical_path_ready':summary.get('canonical_path_ready') is True,
        'no_missing_core_files':summary.get('core_files_missing')==[],
        'no_schema_errors':summary.get('schema_errors')=={},
        'no_modeled_season_gaps':summary.get('modeled_season_coverage_gaps')=={},
    }
    rows=[]
    fingerprints=summary.get('raw_fingerprints',[])
    names=[x['file'] for x in fingerprints]
    if not names or len(names)!=len(set(names)): raise Stop('PRIOR_FINGERPRINTS_MISSING_OR_DUPLICATED')
    raw=repo/'data/kaggle/raw'
    for i,item in enumerate(fingerprints,1):
        name=item['file']; safe_relative(name)
        if Path(name).name!=name: raise Stop('UNEXPECTED_RAW_FILENAME')
        f=raw/name
        present=f.is_file() and f.resolve().is_relative_to(repo)
        actual=sha_file(f,run) if present else None
        rows.append(dict(file=name,expected_sha256=item['sha256'],actual_sha256=actual,
                         matches=present and actual==item['sha256']))
        if i%10==0 or i==len(fingerprints): run.event('raw_hash_progress',completed=i,total=len(fingerprints))
    checks['raw_hashes_match']=all(x['matches'] for x in rows)
    result=dict(checks=checks,passed=all(checks.values()),raw_table_count=len(rows),files=rows,
                scope='Revalidates prior table-level audit by byte identity, not a new per-team completeness/leakage proof.')
    save_json(run.out/'data_revalidation.json',result)
    return result

def collect_reports(run,repo,expected):
    base='reports/feature_store/'
    run_raw=git(run,repo,'show',expected+':'+base+'run.json')
    manifest=json.loads(run_raw)
    outputs={}
    provenance=[]
    for filename in REPORT_FILES:
        rel=base+filename
        expected_hash=manifest.get('sha256',{}).get(filename)
        if not isinstance(expected_hash,str): raise Stop('MISSING_PUBLISHED_REPORT_HASH: '+filename)
        cached=run.out/'cache'/expected_hash/filename
        if cached.is_file() and sha_file(cached,run)==expected_hash:
            raw=cached.read_bytes(); reused=True
        else:
            raw=git(run,repo,'show',expected+':'+rel); reused=False
            if digest(raw)!=expected_hash: raise Stop('PUBLISHED_REPORT_HASH_MISMATCH: '+filename)
            atomic_bytes(cached,raw)
        outputs[filename]=raw
        provenance.append(dict(path=rel,sha256=digest(raw),hash_verified=True,reused=reused))
        run.event('published_report_verified',file=filename,reused=reused)
    source_comparisons=[]
    for rel,expected_hash in manifest.get('manifest',{}).get('inputs',{}).get('source',{}).items():
        safe_relative(rel)
        try:
            current=git(run,repo,'show',expected+':'+rel)
            match=digest(current)==expected_hash
        except Stop:
            match=False
        source_comparisons.append(dict(path=rel,matches_historical_source=match))
    save_json(run.out/'report_provenance.json',dict(reference=expected,files=provenance,
               historical_source_comparisons=source_comparisons,
               study_scope=manifest.get('manifest',{}).get('evidence_status'),
               note='Reading published reports from Git objects, not edited worktree CSVs. Historical source differences do not invalidate historical results; they block claiming exact current-code reproduction.'))
    return outputs,manifest,source_comparisons

def parse_csv(raw,required,name):
    import pandas as pd
    frame=pd.read_csv(io.BytesIO(raw))
    missing=set(required)-set(frame.columns)
    if missing: raise Stop('REPORT_SCHEMA: '+name+' missing '+','.join(sorted(missing)))
    return frame

def bool_series(series):
    values=series.astype(str).str.lower().map({'true':True,'false':False})
    if values.isna().any(): raise Stop('REPORT_BOOLEAN_VALUES_INVALID')
    return values

def summarize_reports(raws):
    import pandas as pd
    import numpy as np
    registry=parse_csv(raws['feature_registry.csv'],['feature','family'],'registry')
    usage=parse_csv(raws['feature_usage.csv'],KEY+['feature','fitted','train_nonmissing','validation_nonmissing','train_games','validation_games'],'usage')
    screen=parse_csv(raws['screening_summary.csv'],KEY+['candidate_count','retained_count','rejected_count'],'screen')
    metrics=parse_csv(raws['metrics_by_season.csv'],KEY+['games','brier'],'metrics')
    if registry['feature'].isna().any() or registry['family'].isna().any() or registry['feature'].duplicated().any():
        raise Stop('REGISTRY_FEATURE_ID_NOT_UNIQUE')
    for name,df in [('usage',usage),('screen',screen),('metrics',metrics)]:
        if df[KEY].isna().any().any(): raise Stop('MISSING_REPORT_KEYS: '+name)
        if not set(df.Gender).issubset({'M','W'}): raise Stop('UNEXPECTED_POPULATION')
        df['Season']=pd.to_numeric(df.Season,errors='raise').astype(int)
        if ((df.Season<1900)|(df.Season>=2026)).any(): raise Stop('UNEXPECTED_STUDY_SEASON')
    if usage.duplicated(KEY+['feature']).any(): raise Stop('DUPLICATE_USAGE_ROWS')
    for name,df in [('screen',screen),('metrics',metrics)]:
        if df.duplicated(KEY).any(): raise Stop('DUPLICATE_FIT_ROWS: '+name)
    usage['fitted']=bool_series(usage.fitted)
    if not usage['fitted'].all() or not usage.block.eq('full').all():
        raise Stop('PUBLIC_USAGE_SCOPE_CHANGED: expected retained full-block view only.')
    for col in ['candidate_count','retained_count','rejected_count']:
        screen[col]=pd.to_numeric(screen[col],errors='raise')
        if (~np.isfinite(screen[col])|(screen[col]<0)|(screen[col]%1!=0)).any(): raise Stop('INVALID_SCREEN_COUNT')
    if not (screen.candidate_count==screen.retained_count+screen.rejected_count).all(): raise Stop('SCREEN_COUNTS_DO_NOT_RECONCILE')
    # Reason columns can evolve; verify all numeric reason columns reconcile before plotting.
    reasons=[c for c in screen.columns if c not in KEY+['candidate_count','retained_count','rejected_count']]
    for c in reasons:
        screen[c]=pd.to_numeric(screen[c],errors='raise')
        if (~np.isfinite(screen[c])|(screen[c]<0)|(screen[c]%1!=0)).any(): raise Stop('INVALID_REASON_COUNT')
    if reasons and not np.allclose(screen[reasons].sum(axis=1),screen.candidate_count): raise Stop('SCREEN_REASON_COUNTS_DO_NOT_RECONCILE')
    metrics['brier']=pd.to_numeric(metrics.brier,errors='raise')
    metrics['games']=pd.to_numeric(metrics.games,errors='raise')
    if (~np.isfinite(metrics.brier)|~metrics.brier.between(0,1)|~np.isfinite(metrics.games)|(metrics.games<=0)|(metrics.games%1!=0)).any():
        raise Stop('INVALID_RECORDED_METRICS')
    full=screen[screen.block.eq('full')].copy()
    if full.empty: raise Stop('FULL_BLOCK_SCREENING_MISSING')
    actual=usage.groupby(KEY).size().rename('observed_retained').reset_index()
    check=full.merge(actual,on=KEY,how='outer',validate='one_to_one',indicator=True)
    if (check._merge!='both').any() or not (check.retained_count==check.observed_retained).all():
        raise Stop('PUBLIC_RETAINED_COUNTS_MISMATCH')
    usage=usage.merge(registry[['feature','family']],on='feature',how='left',validate='many_to_one')
    if usage.family.isna().any(): raise Stop('RETAINED_FEATURE_MISSING_FROM_REGISTRY')
    for col in ['train_nonmissing','validation_nonmissing','train_games','validation_games']:
        usage[col]=pd.to_numeric(usage[col],errors='raise')
    if (usage.train_nonmissing<0).any() or (usage.validation_nonmissing<0).any() or (usage.train_games<=0).any() or (usage.validation_games<=0).any():
        raise Stop('INVALID_COVERAGE_COUNTS')
    if (usage.train_nonmissing>usage.train_games).any() or (usage.validation_nonmissing>usage.validation_games).any(): raise Stop('COVERAGE_COUNTS_EXCEED_GAMES')
    usage['train_coverage']=usage.train_nonmissing/usage.train_games
    usage['validation_coverage']=usage.validation_nonmissing/usage.validation_games
    usage['route']=usage.Gender+'/'+usage.model
    full['route']=full.Gender+'/'+full.model
    metrics['route']=metrics.Gender+'/'+metrics.model
    families=sorted(registry.family.unique())
    family_rows=[]
    for _,fit in full.iterrows():
        chosen=usage[(usage.Gender==fit.Gender)&(usage.Season==fit.Season)&(usage.model==fit.model)]
        counts=chosen.groupby('family').size().to_dict()
        for family in families:
            family_rows.append(dict(Gender=fit.Gender,model=fit.model,Season=int(fit.Season),route=fit.route,
                                    family=family,retained=int(counts.get(family,0))))
    family_by_fit=pd.DataFrame(family_rows)
    family_summary=family_by_fit.groupby(['route','family'],as_index=False).agg(mean_retained=('retained','mean'),
                     min_retained=('retained','min'),max_retained=('retained','max'),folds=('Season','nunique'))
    selection_rows=[]
    for route,r in usage.groupby('route'):
        seasons=sorted(full.loc[full.route==route,'Season'].unique())
        for (feature,family),g in r.groupby(['feature','family']):
            chosen=set(g.Season)
            for year in seasons: selection_rows.append(dict(route=route,feature=feature,family=family,Season=int(year),retained=int(year in chosen)))
    selection=pd.DataFrame(selection_rows)
    usage_summary=usage.groupby('route',as_index=False).agg(distinct_retained=('feature','nunique'),
        fits=('Season','nunique'),mean_train_coverage=('train_coverage','mean'),min_train_coverage=('train_coverage','min'),
        mean_validation_coverage=('validation_coverage','mean'),min_validation_coverage=('validation_coverage','min'))
    summary_rows=[]
    for keys,g in metrics.groupby(['Gender','model','block']):
        summary_rows.append(dict(zip(['Gender','model','block'],keys),
            mean_season_brier=float(g.brier.mean()),game_weighted_brier=float(np.average(g.brier,weights=g.games)),
            seasons=int(g.Season.nunique()),games=int(g.games.sum())))
    metric_summary=pd.DataFrame(summary_rows)
    baseline=metrics.loc[metrics.block.eq('full'),['Gender','Season','model','games','brier']].rename(columns={'games':'full_games','brier':'full_brier'})
    ablations=metrics[metrics.block.str.startswith('without_')].merge(baseline,on=['Gender','Season','model'],how='left',validate='many_to_one')
    ablations['comparable_counts']=ablations.games.eq(ablations.full_games)&ablations.full_brier.notna()
    ablations['delta_without_minus_full']=np.where(ablations.comparable_counts,ablations.brier-ablations.full_brier,np.nan)
    ablations['omitted_family']=ablations.block.str.removeprefix('without_')
    return dict(registry=registry,usage=usage,screening=screen,full_screening=full,family_by_fit=family_by_fit,
        family_summary=family_summary,selection=selection,usage_summary=usage_summary,
        metrics=metrics,metric_summary=metric_summary,ablations=ablations)

def make_figures(tables):
    import plotly.express as px
    figures=[]
    sizes=tables['registry'].groupby('family').size().rename('catalog_features').sort_values().reset_index()
    figures.append(('catalog',px.bar(sizes,x='catalog_features',y='family',orientation='h',
        title='Registered candidates by family · catalog, not fitted inputs')))
    matrix=tables['family_summary'].pivot(index='family',columns='route',values='mean_retained').fillna(0)
    figures.append(('family_retention',px.imshow(matrix,aspect='auto',text_auto='.1f',
        labels={'x':'Population / model','y':'Registered family','color':'Mean inputs retained'},
        title='Full-bank fits · mean retained inputs per family (all observed folds)')))
    for route in sorted(tables['full_screening'].route.unique()):
        full=tables['full_screening'].query('route == @route')
        reasons=[c for c in full if c not in KEY+['route','candidate_count','retained_count','rejected_count']]
        if reasons:
            long=full.melt(id_vars=['Season'],value_vars=reasons,var_name='reason',value_name='decisions')
            figures.append((route.replace('/','_')+'_screening',px.bar(long,x='Season',y='decisions',color='reason',
                title=route+' · full-bank candidate decisions by season')))
        sel=tables['selection'].query('route == @route')
        top=sel.groupby('feature').retained.mean().sort_values(ascending=False,kind='stable').head(30).index
        mat=sel[sel.feature.isin(top)].pivot(index='feature',columns='Season',values='retained').reindex(top)
        figures.append((route.replace('/','_')+'_stability',px.imshow(mat,aspect='auto',zmin=0,zmax=1,
            labels={'color':'Observed retained'},title=route+' · 30 most consistently retained inputs')))
        met=tables['metrics'].query('route == @route')
        met=met[met.block.isin(['strength','baseline_124','full','rankings','conference'])].sort_values('Season')
        if not met.empty:
            figures.append((route.replace('/','_')+'_brier',px.line(met,x='Season',y='brier',color='block',markers=True,
                title=route+' · recorded historical Brier, not the 2026 leaderboard')))
        abl=tables['ablations'].query('route == @route and comparable_counts').copy()
        if not abl.empty:
            abl['Season']=abl.Season.astype(str)
            fig=px.strip(abl,x='delta_without_minus_full',y='omitted_family',color='Season',
                title=route+' · omission + re-selection effect (without − full)')
            fig.add_vline(x=0,line_dash='dash')
            figures.append((route.replace('/','_')+'_ablations',fig))
    for _,fig in figures:
        fig.update_layout(height=max(430,fig.layout.height or 0),margin=dict(l=30,r=30,t=75,b=45))
    return figures

def html_report(tables,summary,figures):
    import plotly.io as pio
    css='body{font:16px/1.6 system-ui;max-width:1250px;margin:40px auto;padding:0 24px}h1{font-size:36px;line-height:1.2}table{border-collapse:collapse;width:100%}td,th{padding:8px;text-align:left;border-bottom:1px solid #ddd}pre{white-space:pre-wrap;font-size:13px}.cards{display:flex;gap:15px;flex-wrap:wrap;margin:25px 0}.card{border:1px solid #ddd;border-radius:8px;padding:18px;min-width:140px}.number{font-size:28px;font-weight:650}details{margin:25px 0}summary{cursor:pointer;font-weight:600}section{margin:35px 0}'
    chunks=['<!doctype html><html><head><meta charset="utf-8"><title>March Mania · Feature evidence</title><style>'+css+'</style></head><body>',
        '<h1>March Mania · Workspace diagnosis & feature evidence</h1>',
        '<p>Read-only milestone. No new models or leaderboard score. Published feature-store results are retrospective, not a fitted-column audit of the final submitted model.</p>',
        '<div class="cards">'+''.join('<div class="card"><div class="number">'+html.escape(str(summary[k]))+'</div><div>'+label+'</div></div>' for k,label in [('tracked_change_count','Tracked changes'),('catalog_features','Registered candidates'),('retained_per_full_fit_max','Maximum inputs / full fit'),('new_models_fitted','New model fits')])+'</div>',
        '<p><strong>Status: '+html.escape(summary['status'])+'</strong> · '+html.escape(summary['utc'])+'</p>',
        '<details><summary>Exact status, hashes and scope</summary><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre></details>',
        '<h2>Interpretation limits</h2><p>Public usage exposes retained full-block inputs only. Absence is not a known rejection reason. Omission deltas include re-selection of other inputs. Equal game counts do not establish paired row identities. Mean-season and game-weighted Brier are distinct aggregates. These already-examined seasons are exploratory evidence, not an untouched test set.</p>']
    for i,(name,fig) in enumerate(figures):
        chunks.append('<section id="'+html.escape(name)+'">'+pio.to_html(fig,full_html=False,include_plotlyjs=True if i==0 else False)+'</section>')
    chunks.extend(['<details><summary>All recorded aggregates · historical results only</summary>',tables['metric_summary'].to_html(index=False,escape=True),'</details></body></html>'])
    return '\n'.join(chunks)

def run_audit(run,repo,prior,expected):
    run.event('stage_started',stage='worktree_diagnosis')
    state=inspect_worktree(run,repo,expected,backup=True)
    save_json(run.out/'worktree_diagnosis.json',state)
    import pandas as pd
    columns=['path','classification','staged','unstaged','head_sha256','index_sha256','worktree_sha256','head_mode','index_mode','worktree_mode','symlink']
    pd.DataFrame(state['changed_files'],columns=columns).to_csv(run.out/'tracked_changes.csv',index=False)
    run.event('stage_completed',stage='worktree_diagnosis',tracked_changes=state['tracked_change_count'])
    run.event('stage_started',stage='data_revalidation')
    data=revalidate_data(run,repo,prior)
    run.event('stage_completed',stage='data_revalidation',passed=data['passed'])
    run.event('stage_started',stage='published_feature_evidence')
    raws,manifest,source_comparisons=collect_reports(run,repo,expected)
    tables=summarize_reports(raws)
    historical_data=manifest.get('manifest',{}).get('inputs',{}).get('data',{})
    current={x['file']:x['actual_sha256'] for x in data['files']}
    input_comparison=[dict(file=k,matches=current.get(k)==v) for k,v in historical_data.items()]
    for name,frame in tables.items():
        run.check()
        frame.to_csv(run.out/(name+'.csv'),index=False)
    figures=make_figures(tables)
    for name,fig in figures:
        run.check()
        atomic_bytes(run.out/'figures'/(name+'.json'),fig.to_json().encode())
    after=inspect_worktree(run,repo,expected,backup=False)
    same=all(state[k]==after[k] for k in ['head','branch','changed_files','hidden_index_flag_count','in_progress_git_operations','untracked_file_count'])
    if not same: raise Stop('WORKTREE_CHANGED_DURING_AUDIT: preserve reports and close other writers before another run.')
    summary=dict(utc=utc(),milestone='01-workspace-diagnosis-and-published-feature-evidence',
        status='PASS_DIAGNOSTIC' if state['tracked_clean'] and data['passed'] else 'REVIEW_REQUIRED',
        expected_commit=expected,head=state['head'],branch=state['branch'],tracked_clean=state['tracked_clean'],
        tracked_change_count=state['tracked_change_count'],tracked_changes=[{k:v for k,v in r.items() if k in ('path','classification','staged','unstaged')} for r in state['changed_files']],
        hidden_index_flag_count=state['hidden_index_flag_count'],in_progress_git_operations=state['in_progress_git_operations'],
        repository_state_unchanged=same,private_backup_file_versions=state['backup_file_versions'],
        raw_tables_rechecked=data['raw_table_count'],raw_data_unchanged=data['checks']['raw_hashes_match'],
        data_preflight_revalidated=data['passed'],historical_data_hashes_compared=len(input_comparison),
        historical_data_hashes_matched=sum(x['matches'] for x in input_comparison),
        historical_input_mismatches=[x['file'] for x in input_comparison if not x['matches']],
        computational_source_files_compared=len(source_comparisons),computational_source_files_changed=sum(not x['matches_historical_source'] for x in source_comparisons),
        public_study_scope='retained full-block feature-store fits, not final submitted-model inputs',
        catalog_features=int(len(tables['registry'])),full_block_fits=int(len(tables['full_screening'])),
        retained_per_full_fit_min=int(tables['full_screening'].retained_count.min()),
        retained_per_full_fit_max=int(tables['full_screening'].retained_count.max()),
        distinct_retained_full_block=int(tables['usage'].feature.nunique()),
        historical_seasons=sorted(map(int,tables['metrics'].Season.unique())),
        historical_recorded_fit_rows=int(len(tables['metrics'])),plotly_figures=len(figures),
        aggregate_scope='Mean season and game-weighted Brier saved separately. Omission effects are conditional pipeline effects, not controlled single-family effects.',
        source_ready_for_next_design=bool(state['tracked_clean'] and data['passed']),
        current_submitted_brier=0.1222672,research_target_brier=0.1097454,new_models_fitted=0,new_leaderboard_score=None,
        training_authorized=False,github_updated=False,cloud_resources_modified=False,archive_downloaded=False,
        next_step='Review exact tracked changes; then trace final-model inputs and specify one frozen-anchor feature test. No automatic full-bank rebuild.')
    save_json(run.out/'milestone_01_summary.json',summary)
    atomic_bytes(run.out/'feature_evidence.html',html_report(tables,summary,figures).encode())
    # Shareable bundle deliberately excludes backups, raw data, models, logs and arbitrary local files.
    import zipfile
    allowed=['milestone_01_summary.json','tracked_changes.csv','family_summary.csv','usage_summary.csv','metric_summary.csv','ablations.csv','report_provenance.json']
    fd,tmp=tempfile.mkstemp(dir=run.out,prefix='.milestone_01.',suffix='.zip'); os.close(fd)
    try:
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
            for name in allowed: z.write(run.out/name,arcname=name)
        os.replace(tmp,run.out/'milestone_01_return.zip')
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    run.event('stage_completed',stage='published_feature_evidence',figures=len(figures),status=summary['status'])
    return summary

def run_from_notebook(repo,prior,out,expected=EXPECTED,seconds=300):
    """Streaming child runner with a wall-clock watchdog independent of notebook output."""
    argv=[sys.executable,str(Path(__file__).resolve()),'run','--repo',str(repo),'--prior-reports',str(prior),
          '--out',str(out),'--expected-commit',expected,'--max-seconds',str(seconds)]
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,env=env,start_new_session=(os.name=='posix'))
    q=queue.Queue()
    def drain():
        try:
            for line in p.stdout: q.put(line)
        finally: q.put(None)
    thread=threading.Thread(target=drain,daemon=True); thread.start()
    deadline=time.monotonic()+seconds+10
    try:
        ended=False
        while not ended:
            if time.monotonic()>deadline: raise Stop('NOTEBOOK_WALL_CLOCK_LIMIT: child terminated; completed outputs remain.')
            try:
                line=q.get(timeout=.25)
                if line is None: ended=True
                else: print(line.rstrip(),flush=True)
            except queue.Empty:
                if p.poll() is not None and not thread.is_alive(): ended=True
        code=p.wait(timeout=5)
    except BaseException:
        terminate(p)
        raise
    if code not in (0,2): raise Stop('DIAGNOSTIC_FAILED: read reports/failure.json. Do not reset, reinstall or train.')
    return json.loads((Path(out)/'milestone_01_summary.json').read_text())

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['run'])
    p.add_argument('--repo',type=Path,default=Path.home()/'march-machine-learning-mania-2026')
    p.add_argument('--prior-reports',type=Path,default=Path.home()/'march_workspace_sync/reports')
    p.add_argument('--out',type=Path,default=KIT/'reports')
    p.add_argument('--expected-commit',default=EXPECTED)
    p.add_argument('--max-seconds',type=int,default=300)
    a=p.parse_args(argv)
    if not 1<=a.max_seconds<=600: p.error('Budget must be 1–600 seconds; do not silently increase limits.')
    if not re.fullmatch('[0-9a-f]{40}',a.expected_commit): p.error('Expected commit must be a full SHA.')
    repo=a.repo.expanduser().resolve(); out=a.out.expanduser().resolve();prior=a.prior_reports.expanduser().resolve()
    if out==repo or out.is_relative_to(repo) or out==prior or out.is_relative_to(prior): p.error('Keep outputs separate from repo and previous receipts.')
    os.umask(0o077)
    run=Budget(out,a.max_seconds)
    old_alarm=None
    def timed_out(*_): raise Stop('HARD_TIME_LIMIT: completed checkpoints preserved.')
    try:
        if os.name=='posix':
            old_alarm=signal.signal(signal.SIGALRM,timed_out); signal.setitimer(signal.ITIMER_REAL,a.max_seconds)
            signal.signal(signal.SIGTERM,timed_out)
        summary=run_audit(run,repo,prior,a.expected_commit)
        save_json(run.directory/'receipt.json',summary)
        print('RETURN FILE: '+str(out/'milestone_01_return.zip'),flush=True)
        print('GATE: '+summary['status']+'; no training.',flush=True)
        return 0 if summary['status']=='PASS_DIAGNOSTIC' else 2
    except Exception as exc:
        error=dict(utc=utc(),status='STOP',error_type=type(exc).__name__,reason=str(exc),
                   new_models_fitted=0,github_updated=False,repository_writes=False)
        save_json(out/'failure.json',error);save_json(run.directory/'failure.json',error)
        print(json.dumps(error),flush=True)
        return 1
    finally:
        if os.name=='posix':
            signal.setitimer(signal.ITIMER_REAL,0)
            if old_alarm is not None:signal.signal(signal.SIGALRM,old_alarm)
        run.close()

if __name__=='__main__':
    raise SystemExit(main())
