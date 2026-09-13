#!/usr/bin/env python3
"""March Mania manual milestone 0. No training, cloud writes, pushes, or user-file deletions.

Python 3.10+; synchronization/data auditing require only the standard library and Git.
The environment subcommand installs the repository's own locked dependencies.
"""
from __future__ import annotations
import argparse
import ast
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
import zipfile

EXPECTED = '84b8fb36644a6558beded6dad84f5645ea4405d3'
REMOTE = 'https://github.com/alvaromendizabal/march-machine-learning-mania-2026.git'
SLUG = 'alvaromendizabal/march-machine-learning-mania-2026'
KIT = Path(__file__).resolve().parent
PRIVATE = ('data', 'outputs', 'models', 'submissions', 'checkpoints', 'artifacts')
CORE = {f'{sex}{suffix}.csv' for sex in 'MW' for suffix in (
    'Teams', 'Seasons', 'RegularSeasonCompactResults', 'RegularSeasonDetailedResults',
    'NCAATourneyCompactResults', 'NCAATourneySeeds')}
OPTIONAL = {f'{sex}{suffix}.csv' for sex in 'MW' for suffix in (
    'NCAATourneyDetailedResults', 'TeamConferences', 'SecondaryTourneyCompactResults',
    'SecondaryTourneyTeams', 'RegularSeasonDetailedResults', 'GameCities')}
OPTIONAL |= {'MMasseyOrdinals.csv','MTeamCoaches.csv','MTeamSpellings.csv',
             'WTeamSpellings.csv','Cities.csv','Conferences.csv',
             'SampleSubmissionStage1.csv','SampleSubmissionStage2.csv'}
OFFICIAL = re.compile(r'^(?:[MW][A-Za-z0-9_]+|Cities|Conferences|SampleSubmissionStage[12])\.csv$')

class Stop(RuntimeError):
    """Fail-closed condition; preserve existing work rather than guessing."""

def utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')
    os.replace(tmp, path)

class Run:
    def __init__(self, out: Path, stage: str, seconds: int = 600):
        self.out, self.stage = out, stage
        self.started = time.monotonic()
        self.deadline = self.started + seconds
        self.directory = out / 'runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '_' + stage)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.heartbeat, daemon=True)
        self.thread.start()
        self.event('started', hard_limit_seconds=seconds)
    def check(self):
        if time.monotonic() >= self.deadline:
            raise Stop('STAGE_TIME_LIMIT: completed receipts are preserved; inspect before rerunning.')
    def event(self, event, **kw):
        row = {'utc': utc(), 'stage': self.stage, 'event': event,
               'elapsed_seconds': round(time.monotonic()-self.started, 2), **kw}
        with self.lock:
            with (self.directory / 'events.jsonl').open('a') as stream:
                stream.write(json.dumps(row) + '\n')
            print(json.dumps(row), flush=True)
    def heartbeat(self):
        while not self.stop_event.wait(15):
            self.event('heartbeat')
    def command(self, argv, cwd=None, limit=120, ok=(0,), label=None):
        self.check()
        seconds = min(limit, max(1, self.deadline-time.monotonic()))
        # Command output remains local. Never log environment variables or credential files.
        env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0',
                   PYTHONUNBUFFERED='1')
        self.event('command_started', command=label or Path(str(argv[0])).name,
                   command_limit_seconds=round(seconds, 1))
        with tempfile.TemporaryFile() as log:
            p = subprocess.Popen(list(map(str, argv)), cwd=cwd, env=env, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=(os.name=='posix'))
            try:
                p.wait(timeout=seconds)
            except BaseException:
                if p.poll() is None:
                    if os.name == 'posix':
                        os.killpg(p.pid, signal.SIGTERM)
                    else:
                        p.terminate()
                    try:
                        p.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        if os.name == 'posix':
                            os.killpg(p.pid, signal.SIGKILL)
                        else:
                            p.kill()
                        p.wait()
                raise
            log.seek(0)
            text = log.read().decode('utf-8', errors='replace')
        # Local diagnostics, not included in shareable summary.
        with (self.directory / 'commands.log').open('a') as stream:
            stream.write('\nCOMMAND: ' + (label or str(argv[0])) + '\n' + text)
        self.last_returncode = p.returncode
        if p.returncode not in ok:
            raise Stop(f'{label or argv[0]} exited {p.returncode}. See {self.directory / "commands.log"}; do not reset or delete files.')
        return text
    def finish(self, status, **kw):
        self.stop_event.set()
        self.thread.join(timeout=2)
        receipt = {'utc': utc(), 'stage': self.stage, 'status': status,
                   'elapsed_seconds': round(time.monotonic()-self.started, 2), **kw}
        save_json(self.directory/'receipt.json', receipt)
        save_json(self.out/f'{self.stage}.json', receipt)
        self.event(status)
        return receipt

def git(run, root, *args, ok=(0,)):
    # Disable checkout/merge hooks during the sync; no repository hooks are executed.
    return run.command(['git','-c','core.hooksPath=/dev/null',*args], cwd=root,
                       ok=ok, label='git ' + args[0]).strip()

def sha(path, run=None):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            if run:
                run.check()
            h.update(chunk)
    return h.hexdigest()

def recognized_origin(value):
    return value.rstrip('/') in (REMOTE, REMOTE[:-4],
           'git@github.com:' + SLUG + '.git', 'git@github.com:' + SLUG,
           'ssh://git@github.com/' + SLUG + '.git')

def repo_check(run, root, test_remote=None):
    if not root.exists():
        raise Stop(f'REPOSITORY_NOT_FOUND: {root}. Use clone only after confirming this is the correct Studio space.')
    top = git(run, root, 'rev-parse','--show-toplevel')
    if Path(top).resolve() != root.resolve():
        raise Stop('REPOSITORY_ROOT_MISMATCH: stop; the requested directory is not the repository root.')
    origin = git(run, root, 'remote','get-url','origin')
    if not (recognized_origin(origin) or (test_remote is not None and origin==str(test_remote))):
        raise Stop('UNEXPECTED_ORIGIN: no changes made. Inspect origin privately; expected ' + SLUG)
    for name in ('MERGE_HEAD','CHERRY_PICK_HEAD','REVERT_HEAD','rebase-merge','rebase-apply','BISECT_LOG'):
        p = Path(git(run, root, 'rev-parse','--git-path',name))
        if not p.is_absolute():
            p = root / p
        if p.exists():
            raise Stop('IN_PROGRESS_GIT_OPERATION: resolve the existing operation first.')
    flags = git(run, root, 'ls-files', '-v').splitlines()
    if any(line and (line[0].islower() or line[0] == 'S') for line in flags):
        raise Stop('HIDDEN_INDEX_FLAGS: assume-unchanged/skip-worktree entries can hide edits. Inspect before synchronization.')
    return {'head':git(run,root,'rev-parse','HEAD'),
            'branch':git(run,root,'branch','--show-current'),
            'tracked_changes':git(run,root,'diff','--name-only','HEAD'),
            'untracked_files':git(run,root,'ls-files','--others','--exclude-standard'),
            'stashes':git(run,root,'stash','list','--format=%gd %H')}

def raw_candidates(root):
    candidates=[]
    for base in (root/'data/kaggle/raw',root/'data/kaggle',root/'data/raw',root/'data',root):
        if base.is_dir() and (base/'MTeams.csv').is_file():
            candidates.append(base.resolve())
    data = root/'data'
    if data.exists():
        for p in data.glob('**/MTeams.csv'):
            if len(p.relative_to(data).parts)<=5:
                candidates.append(p.parent.resolve())
    return sorted(set(candidates),key=str)

def choose_raw(root):
    canonical = root/'data/kaggle/raw'
    if (canonical/'MTeams.csv').is_file():
        return canonical
    candidates=raw_candidates(root)
    if len(candidates)==1:
        return candidates[0]
    if not candidates:
        raise Stop('RAW_DATA_MISSING: upload the official competition ZIP and run restore-data. No training permitted.')
    raise Stop('MULTIPLE_RAW_SNAPSHOTS: specify the desired folder with restore-data --source; do not merge snapshots blindly.')

def files_under(root, run=None):
    """Do not traverse directory symlinks or enumerate .git/environments."""
    if not root.exists():
        return
    for base, dirs, files in os.walk(root, followlinks=False):
        if run:
            run.check()
        dirs.sort(); files.sort()
        for name in list(dirs):
            p=Path(base)/name
            if p.is_symlink():
                yield p
                dirs.remove(name)
        for name in files:
            yield Path(base)/name

def private_manifest(root, run):
    result={}
    for prefix in PRIVATE:
        for p in files_under(root/prefix, run) or []:
            if p.name == '.gitkeep':
                continue
            key=str(p.relative_to(root))
            if p.is_symlink():
                result[key]={'symlink':os.readlink(p)}
            else:
                stat=p.stat()
                result[key]={'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns}
    return result

def raw_hashes(root, run):
    values={}
    total=0
    for directory in raw_candidates(root):
        for p in sorted(directory.glob('*.csv')):
            if OFFICIAL.fullmatch(p.name):
                total+=p.stat().st_size
                if total>4*1024**3:
                    raise Stop('RAW_HASH_BUDGET: more than 4 GiB discovered. Nothing deleted; inspect snapshot duplication.')
                values[str(p.resolve())]={'bytes':p.stat().st_size,'sha256':sha(p,run)}
    return values

def incoming_safe(run, root):
    current=set(git(run,root,'ls-files','-z').split('\0'))-{''}
    incoming=set(git(run,root,'ls-tree','-r','--name-only','-z','origin/main').split('\0'))-{''}
    for rel in incoming:
        run.check()
        p=root/rel
        if PurePosixPath(rel).parts[0] in PRIVATE and p.name!='.gitkeep':
            raise Stop('PRIVATE_PATH_TRACKED_UPSTREAM: refusing to touch raw data or model directories.')
        if (p.exists() or p.is_symlink()) and rel not in current:
            raise Stop('UNTRACKED_COLLISION: '+rel+' would overlap upstream. It was not removed.')
        for parent in p.parents:
            if parent==root:
                break
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise Stop('UNSAFE_CHECKOUT_PARENT: '+str(parent))
    # Git can otherwise overwrite ignored data. Explicit collision checks above prevent it.

def is_ancestor(run,root,a,b):
    run.command(['git','merge-base','--is-ancestor',a,b],cwd=root,
                ok=(0,1),label='git ancestor check')
    return run.last_returncode==0


def inventory(run, root, test_remote=None):
    state=repo_check(run,root,test_remote)
    priv=private_manifest(root,run)
    hashes=raw_hashes(root,run)
    save_json(run.directory/'private_manifest.json',priv)
    save_json(run.directory/'raw_hashes.json',hashes)
    state.update(repo=str(root),raw_directories=[str(p) for p in raw_candidates(root)],
                 private_file_count=len(priv),private_bytes=sum(v.get('bytes',0) for v in priv.values()),
                 raw_file_count=len(hashes),free_bytes=shutil.disk_usage(root).free)
    save_json(run.directory/'inventory.json',state)
    return state

def sync(run, root, expected, test_remote=None):
    before=inventory(run,root,test_remote)
    if shutil.disk_usage(root).free<512*1024**2:
        raise Stop('LOW_DISK: keep at least 512 MiB free before synchronizing. Do not delete private artifacts.')
    git(run,root,'fetch','--no-tags','origin','+refs/heads/*:refs/remotes/origin/*')
    remote=git(run,root,'rev-parse','origin/main')
    if remote!=expected:
        raise Stop('REMOTE_MAIN_CHANGED: audited '+expected+' but fetched '+remote+'. Stop to review the new commit/CI; no checkout changes made.')
    if not is_ancestor(run,root,'HEAD','origin/main'):
        raise Stop('UNMERGED_LOCAL_COMMITS: current HEAD is not an ancestor of origin/main. Existing branch remains intact; do not reset it.')
    existing_main=git(run,root,'show-ref','--verify','refs/heads/main',ok=(0,1))
    if existing_main and not is_ancestor(run,root,'main','origin/main'):
        raise Stop('LOCAL_MAIN_DIVERGED: local main contains unpublished/divergent history. No stash or checkout attempted.')
    if git(run,root,'ls-files','-u'):
        raise Stop('UNRESOLVED_CONFLICTS: no checkout changes made.')
    incoming_safe(run,root)
    for rel in git(run,root,'ls-files','-z').split('\0'):
        if rel and PurePosixPath(rel).parts[0] in PRIVATE and Path(rel).name!='.gitkeep':
            raise Stop('PRIVATE_DATA_TRACKED_LOCALLY: manual inspection required before stashing.')
    # A local bundle preserves commits and all prior stash refs; patches preserve index/working edits.
    recovery=run.directory/'recovery'
    recovery.mkdir()
    for name,args in [('working.patch',('diff','--binary')),('index.patch',('diff','--cached','--binary'))]:
        text=run.command(['git',*args],cwd=root,label='save local patch')
        (recovery/name).write_text(text)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    ref='recovery/manual-sync-'+stamp
    git(run,root,'branch',ref,'HEAD')
    stash=None
    if before['tracked_changes']:
        git(run,root,'stash','push','-m','Manual workspace sync '+stamp)
        stash=git(run,root,'rev-parse','refs/stash')
    # No -u or -a: untracked/ignored inputs remain exactly where they are.
    save_json(recovery/'recovery.json',{'original_head':before['head'],
        'original_branch':before['branch'],'recovery_branch':ref,'stash_commit':stash})
    git(run,root,'bundle','create',str(recovery/'history.bundle'),'--all')
    if existing_main:
        git(run,root,'switch','main')
    else:
        git(run,root,'switch','--track','-c','main','origin/main')
    git(run,root,'merge','--ff-only','origin/main')
    if git(run,root,'rev-parse','HEAD')!=remote or git(run,root,'diff','--name-only','HEAD'):
        raise Stop('POST_SYNC_TRACKED_MISMATCH: recovery bundle and stash are preserved.')
    priv_after=private_manifest(root,run)
    raw_after=raw_hashes(root,run)
    priv_before=json.loads((run.directory/'private_manifest.json').read_text())
    raw_before=json.loads((run.directory/'raw_hashes.json').read_text())
    if priv_after!=priv_before or raw_after!=raw_before:
        raise Stop('PRIVATE_DATA_CHANGED_DURING_SYNC: stop any other running kernels and inspect; no deletion was requested by this kit.')
    return {'repo':str(root),'head':remote,'branch':'main','tracked_matches_origin_main':True,
            'private_metadata_unchanged':True,'raw_sha256_unchanged':True,
            'raw_files_hashed':len(raw_after),'raw_data_present':bool(raw_after),
            'recovery_directory':str(recovery),'stash_commit':stash,
            'untracked_files_preserved':before['untracked_files'].splitlines(),
            'github_writes':False,'training_started':False}

def safe_zip_members(zf):
    members={}
    total=0
    for info in zf.infolist():
        rel=PurePosixPath(info.filename)
        mode=(info.external_attr>>16)&0o170000
        if rel.is_absolute() or '..' in rel.parts or '\\' in info.filename or mode==0o120000:
            raise Stop('UNSAFE_ZIP_MEMBER: traversal/absolute/symlink member rejected.')
        if info.is_dir():
            continue
        if not OFFICIAL.fullmatch(rel.name):
            continue
        if rel.name in members:
            raise Stop('DUPLICATE_ZIP_BASENAME: '+rel.name)
        total+=info.file_size
        if total>4*1024**3 or len(members)>=400:
            raise Stop('ZIP_SIZE_LIMIT: more than 4 GiB or 400 official CSV files.')
        members[rel.name]=info
    if not CORE.issubset(members):
        raise Stop('INCOMPLETE_OFFICIAL_ARCHIVE: missing '+', '.join(sorted(CORE-set(members))))
    return members,total

def restore_data(run, root, source):
    repo_check(run,root)
    target=root/'data/kaggle/raw'
    if source.is_file() and zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as z:
            members,total=safe_zip_members(z)
            if shutil.disk_usage(root).free<2*total+256*1024**2:
                raise Stop('INSUFFICIENT_DISK_FOR_SAFE_EXTRACTION: original inputs remain untouched.')
            with tempfile.TemporaryDirectory(prefix='march_data_',dir=root.parent) as temp:
                stage=Path(temp)
                for name,info in members.items():
                    run.check()
                    with z.open(info) as src,(stage/name).open('xb') as dst:
                        while True:
                            run.check(); chunk=src.read(1024*1024)
                            if not chunk: break
                            dst.write(chunk)
                return copy_csvs(run,stage,target,root)
    if source.is_dir():
        return copy_csvs(run,source,target,root)
    raise Stop('SOURCE_NOT_FOUND: use the official ZIP or the exact existing folder containing MTeams.csv.')

def copy_csvs(run, source, target, root):
    files={p.name:p for p in source.glob('*.csv') if OFFICIAL.fullmatch(p.name)}
    if not CORE.issubset(files):
        raise Stop('INCOMPLETE_RAW_FOLDER: missing '+', '.join(sorted(CORE-set(files))))
    # Check every conflict before writing any destination file. Never overwrite divergent input bytes.
    hashes={name:sha(p,run) for name,p in files.items()}
    for name,p in files.items():
        dest=target/name
        if dest.exists() and sha(dest,run)!=hashes[name]:
            raise Stop('RAW_SNAPSHOT_CONFLICT: '+name+' differs. Original file preserved; do not combine dates/snapshots.')
    needed=sum(p.stat().st_size for name,p in files.items() if not (target/name).exists())
    if shutil.disk_usage(root).free<needed+256*1024**2:
        raise Stop('LOW_DISK_FOR_COPY: no raw files overwritten.')
    target.mkdir(parents=True,exist_ok=True)
    copied=0
    for name,p in sorted(files.items()):
        run.check()
        dest=target/name
        if dest.exists(): continue
        tmp=target/(name+'.part')
        with p.open('rb') as src,tmp.open('wb') as dst:
            while True:
                run.check(); data=src.read(1024*1024)
                if not data: break
                dst.write(data)
        if sha(tmp,run)!=hashes[name]:
            raise Stop('COPY_HASH_MISMATCH: incomplete .part preserved; source untouched.')
        # Link publication refuses a race that creates a destination after preflight.
        os.link(tmp,dest); tmp.unlink()
        copied+=1
        run.event('raw_file_ready',file=name,completed=copied,total=len(files))
    return {'canonical_raw':str(target),'files_copied':copied,'files_verified':len(files),
            'original_source_preserved':True,'raw_files_overwritten':0,'training_started':False}

def required_columns(name):
    if 'DetailedResults' in name:
        return {'Season','DayNum','WTeamID','LTeamID','WScore','LScore','WFGA','LFGA','WFGM','LFGM',
                'WFGM3','LFGM3','WFGA3','LFGA3','WFTA','LFTA','WFTM','LFTM','WOR','LOR','WDR','LDR','WTO','LTO'}
    if 'CompactResults' in name:
        return {'Season','DayNum','WTeamID','LTeamID','WScore','LScore'}
    if name.endswith('Teams.csv') and 'Tourney' not in name:
        return {'TeamID','TeamName'}
    if name.endswith('Seasons.csv'): return {'Season','DayZero'}
    if name.endswith('Seeds.csv'): return {'Season','Seed','TeamID'}
    if name=='MMasseyOrdinals.csv': return {'Season','RankingDayNum','SystemName','TeamID','OrdinalRank'}
    if 'SampleSubmission' in name: return {'ID','Pred'}
    if name=='MTeamCoaches.csv': return {'Season','TeamID','FirstDayNum','LastDayNum','CoachName'}
    if name.endswith('TeamConferences.csv'): return {'Season','TeamID','ConfAbbrev'}
    return set()

def audit_file(run, path, cache):
    digest=sha(path,run)
    cachefile=cache/(path.name+'.json')
    if cachefile.exists():
        prior=json.loads(cachefile.read_text())
        if prior.get('sha256')==digest and prior.get('audit_version')==1:
            run.event('file_audit_reused',file=path.name)
            return prior
    rows=0; seasons={}; error=None; bad=0; recent_labels=0
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        cols=reader.fieldnames or []
        missing=sorted(required_columns(path.name)-set(cols))
        if missing:
            error='Missing columns: '+', '.join(missing)
        else:
            for row in reader:
                rows+=1
                if rows%10000==0: run.check()
                if None in row or any(v is None for v in row.values()): bad+=1
                s=row.get('Season')
                if s:
                    try: year=int(s)
                    except (ValueError,TypeError): bad+=1; continue
                    stat=seasons.setdefault(str(year),{'rows':0,'max_day':None,'pre132_rows':0,'systems_pre132':set()})
                    stat['rows']+=1
                    day=row.get('RankingDayNum',row.get('DayNum'))
                    if day:
                        try: d=int(day)
                        except (ValueError,TypeError): bad+=1; continue
                        stat['max_day']=d if stat['max_day'] is None else max(d,stat['max_day'])
                        if d<=132:
                            stat['pre132_rows']+=1
                            if row.get('SystemName'):stat['systems_pre132'].add(row['SystemName'])
                    if year==2026 and 'NCAATourney' in path.name and 'Results' in path.name:
                        recent_labels+=1
    for s in seasons.values():s['systems_pre132']=sorted(s['systems_pre132'])
    if not rows and error is None:error='Empty table'
    if bad:error=f'{bad} malformed rows'
    result={'file':path.name,'bytes':path.stat().st_size,'sha256':digest,'rows':rows,
            'columns':cols,'seasons':seasons,'error':error,'audit_version':1,
            'has_2026_tournament_labels':recent_labels>0,'2026_tournament_label_rows':recent_labels}
    save_json(cachefile,result)
    run.event('file_audited',file=path.name,rows=rows,error=error)
    return result

def audit(run,root,expected):
    state=repo_check(run,root)
    raw=choose_raw(root)
    files={p.name:p for p in raw.glob('*.csv') if OFFICIAL.fullmatch(p.name)}
    missing=sorted(CORE-set(files))
    cache=run.out/'file_audit_checkpoints';cache.mkdir(exist_ok=True)
    tables=[]
    for i,p in enumerate(sorted(files.values()),1):
        run.event('file_started',file=p.name,completed=i-1,total=len(files))
        tables.append(audit_file(run,p,cache))
    errors={t['file']:t['error'] for t in tables if t['error']}
    coverage_gaps={}
    modeled=[str(y) for y in range(2013,2027) if y!=2020]
    for t in tables:
        if 'RegularSeason' in t['file'] or t['file'].endswith('NCAATourneySeeds.csv'):
            gaps=sorted(set(modeled)-set(t['seasons']))
            if gaps:coverage_gaps[t['file']]=gaps
    canonical=raw.resolve()==(root/'data/kaggle/raw').resolve()
    ready=not missing and not errors and not coverage_gaps and canonical and state['head']==expected and not state['tracked_changes']
    result={'repo':str(root),'head':state['head'],'expected_commit':expected,
        'tracked_clean':not state['tracked_changes'],'canonical_raw':str(raw),'canonical_path_ready':canonical,
        'core_files_missing':missing,'optional_files_missing':sorted(OPTIONAL-set(files)),
        'schema_errors':errors,'modeled_season_coverage_gaps':coverage_gaps,'tables':tables,
        'ready_for_next_feature_milestone':ready,
        'training_authorized_by_this_report':False,
        'warning':'2022–2025 historical benchmarks and 2026 leaderboard are already consumed. 2026 tournament labels, where present, are diagnostic only, never feature/training inputs for a 2026 forecast.',
        'availability_scope':'Table-level preflight, not per-team completeness, a leakage proof, or an experiment result.'}
    save_json(run.out/'data_audit.json',result)
    with (run.out/'data_coverage.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['file','season','rows','max_day','pre132_rows','ranking_systems_pre132'])
        writer.writeheader()
        for t in tables:
            for season,s in t['seasons'].items():
                writer.writerow({'file':t['file'],'season':season,'rows':s['rows'],'max_day':s['max_day'],
                                 'pre132_rows':s['pre132_rows'],'ranking_systems_pre132':len(s['systems_pre132'])})
    # Shareable: no raw rows, patches, auth tokens, fitted models, or full disk listings.
    summary={k:v for k,v in result.items() if k!='tables'}
    summary['raw_table_count']=len(tables)
    summary['raw_fingerprints']=[{k:t[k] for k in ('file','sha256','rows')} for t in tables]
    summary['current_submitted_brier']=0.1222672;summary['research_target_brier']=0.1097454
    summary['metric_source']='User report and published repository release; not a new measured score.'
    summary['new_experiments_run']=0;summary['github_updated_by_kit']=False
    save_json(run.out/'milestone_summary.json',summary)
    return {k:v for k,v in result.items() if k!='tables'}

def environment(run,root,expected):
    state=repo_check(run,root)
    if state['head']!=expected or state['tracked_changes']:
        raise Stop('ENVIRONMENT_REQUIRES_VERIFIED_CLEAN_COMMIT: synchronize before installing dependencies.')
    text=(root/'scripts/bootstrap.py').read_text()
    version=None
    for node in ast.parse(text).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='UV_VERSION' for t in node.targets):
            version=ast.literal_eval(node.value)
    if not isinstance(version,str) or not re.fullmatch(r'\d+\.\d+\.\d+',version):
        raise Stop('Cannot read pinned uv version from scripts/bootstrap.py.')
    pyversion=(root/'.python-version').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+',pyversion):raise Stop('Unexpected .python-version format.')
    tools=root/'.tools'; exe=tools/'bin/python';uv=tools/'bin/uv'
    if not exe.exists():run.command([sys.executable,'-m','venv',str(tools)],limit=120,label='create isolated tools environment')
    run.command([exe,'-m','pip','--disable-pip-version-check','install','--timeout','30','--retries','1','uv=='+version],limit=180,label='install pinned uv')
    run.command([uv,'sync','--locked','--group','dev','--python',pyversion],cwd=root,limit=600,label='install repository lockfile')
    run.command([uv,'run','--locked','--no-sync','python','-m','ipykernel','install','--user',
        '--name','march-mania','--display-name','Python (March Mania)'],cwd=root,limit=60,label='register March Mania kernel')
    text=run.command([root/'.venv/bin/python','-c',
        'import json,pandas,plotly,sklearn,march_mania; print(json.dumps({"pandas":pandas.__version__,"plotly":plotly.__version__,"sklearn":sklearn.__version__}))'],
        cwd=root,limit=60,label='import smoke test')
    return {'head':state['head'],'uv_version':version,'python_version':pyversion,
            'uv_lock_sha256':sha(root/'uv.lock',run),'imports':text.strip(),
            'kernel':'Python (March Mania)','quality_gate_run':False,'training_started':False}

def clone(run,root,expected):
    if root.exists():raise Stop('CLONE_TARGET_EXISTS: this command never replaces a directory.')
    root.parent.mkdir(parents=True,exist_ok=True)
    staging=root.with_name(root.name+'.incoming-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S'))
    run.command(['git','clone','--branch','main','--single-branch',REMOTE,str(staging)],limit=180,label='clone public source')
    head=git(run,staging,'rev-parse','HEAD')
    if head!=expected:raise Stop('REMOTE_MAIN_CHANGED: source left in '+str(staging)+'; review before use.')
    staging.rename(root)
    return {'repo':str(root),'head':head,'raw_data_present':False,'training_started':False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['inventory','sync','restore-data','environment','audit','clone'])
    parser.add_argument('--repo',type=Path,default=Path.home()/'march-machine-learning-mania-2026')
    parser.add_argument('--out',type=Path,default=KIT/'reports')
    parser.add_argument('--expected-commit',default=EXPECTED)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--max-seconds',type=int,default=600)
    args=parser.parse_args(argv)
    if args.max_seconds<1 or args.max_seconds>1800:parser.error('--max-seconds must be 1–1800')
    if not re.fullmatch('[0-9a-f]{40}',args.expected_commit):parser.error('expected commit must be a full 40-character SHA')
    root=args.repo.expanduser().resolve();out=args.out.expanduser().resolve()
    if out==root or root in out.parents:parser.error('Keep kit reports outside the Git repository.')
    if args.stage=='restore-data' and not args.source:parser.error('restore-data requires --source')
    # Tight permissions apply only to newly created kit receipts/recovery files, never existing raw data.
    os.umask(0o077)
    run=Run(out,args.stage,args.max_seconds)
    if os.name=='posix':
        signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        if args.stage=='inventory':result=inventory(run,root)
        elif args.stage=='sync':result=sync(run,root,args.expected_commit)
        elif args.stage=='restore-data':result=restore_data(run,root,args.source.expanduser().resolve())
        elif args.stage=='environment':result=environment(run,root,args.expected_commit)
        elif args.stage=='audit':result=audit(run,root,args.expected_commit)
        else:result=clone(run,root,args.expected_commit)
        run.finish('PASS',**result)
        print('RECEIPT: '+str(out/(args.stage+'.json')),flush=True)
        if args.stage=='audit' and not result['ready_for_next_feature_milestone']:
            print('STOP: preflight gaps remain. See milestone_summary.json; do not train.',flush=True)
            return 2
        return 0
    except (Exception,KeyboardInterrupt) as error:
        run.finish('STOP',reason=f'{type(error).__name__}: {error}')
        print('STOP. No reset, clean, forced push, or deletion is needed. Inspect the saved receipt.',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
