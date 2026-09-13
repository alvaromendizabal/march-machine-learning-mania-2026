#!/usr/bin/env python3
"""Consolidate the two published snapshots into the ORIGINAL repository only.

No GitHub repository creation. No scientific imports, fits, notebook execution,
credential printing, source-checkout changes, force pushes, or CI bypasses.
Deletion is limited to two literal retired names, after verified migration and
independent local Git-history backups. Run with the existing authorized gh CLI.
"""
from __future__ import annotations
import argparse
import contextlib
import csv
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

OWNER = 'alvaromendizabal'
TARGET = OWNER + '/march-machine-learning-mania-2026'
TARGET_ID = 1350962196
EXTRAS = (OWNER + '/march-mania-research', OWNER + '/march-mania-portfolio')
VERSION = 'march-single-repository-20260912'
ROOT = Path(__file__).resolve().parent
RECEIPT_SHA256 = 'd592633a2a964df578ce9e080a30c56b2df8fcd3956bd7ee05e925527edb36d6'
REQUIRED_CHECKS = {'quality', 'notebook-publication'}
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 300 * 1024 * 1024
SECRET = re.compile(r'(?:AKIA|ASIA)[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|X-Amz-Signature=[a-fA-F0-9]{32,}')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def safe_relative(value):
    require(isinstance(value, str) and value, 'Empty/non-string repository path')
    p = PurePosixPath(value)
    require(not p.is_absolute() and '..' not in p.parts and '.' not in p.parts,
            'Unsafe relative repository path')
    require(not any(c in value for c in '\x00\r\n\\\t') and '.git' not in p.parts,
            'Unsafe repository path characters')
    return p.as_posix()


def no_links(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in [path, *path.parents]), 'Symbolic output path refused: ' + str(path))
    return path


def atomic(path, value):
    path = no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, bytes) else (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    fd, name = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def event(name, **fields):
    print(json.dumps({'utc': stamp(), 'event': name, **fields}), flush=True)


def redacted(text):
    text = SECRET.sub('[REDACTED]', str(text))
    text = re.sub(r'https://[^\s/@]+:[^\s/@]+@', 'https://[REDACTED]@', text)
    return text[-2500:]


def check_source_bytes(path, raw):
    safe_relative(path)
    require(len(raw) <= MAX_FILE, 'Source file exceeds review limit: ' + path)
    require(not raw.startswith(b'version https://git-lfs.github.com/spec/v1'), 'Git LFS content needs separate preservation: ' + path)
    try: text = raw.decode('utf-8')
    except UnicodeError: raise RuntimeError('Non-text snapshot source requires review: ' + path)
    require(not SECRET.search(text), 'Possible credential in source; values not printed: ' + path)
    parts = PurePosixPath(path).parts
    require(not any(n in {'.env', 'kaggle.json', 'hosts.yml', 'credentials', 'id_rsa', 'id_ed25519'} for n in parts), 'Credential container refused: ' + path)
    if path.endswith('.ipynb'):
        n = json.loads(raw)
        require(isinstance(n.get('cells'), list), 'Malformed notebook: ' + path)
        require(not any(c.get('outputs') for c in n['cells'] if c.get('cell_type') == 'code'),
                'Unexpected executed outputs in the source snapshot: ' + path)
    return raw


def mapped_path(role, path):
    path = safe_relative(path)
    if role == 'private':
        parts = PurePosixPath(path).parts
        require(len(parts) >= 3 and parts[0] == 'snapshots', 'Unexpected private snapshot layout')
        suffix = '/'.join(parts[2:])
        if suffix.startswith('research/'):
            return 'research/workspace/' + suffix[len('research/'):]
        require(suffix in {'README.md', 'PRIVATE_SNAPSHOT.json'}, 'Unexpected snapshot root file: ' + suffix)
        return 'research/provenance/' + {'README.md':'ORIGINAL_SNAPSHOT_README.md', 'PRIVATE_SNAPSHOT.json':'SOURCE_SNAPSHOT.json'}[suffix]
    require(role == 'public', 'Unexpected source role')
    return 'research/publication_archive/' + path


def build_payload(source_contents, source_receipt):
    """Pure transformation: preserves EVERY receipt-listed file byte-for-byte."""
    files, mapping = {}, []
    for role in ['private', 'public']:
        record = source_receipt[role]
        for path, expected in sorted(record['published_files'].items()):
            raw = source_contents[role][path]
            require(sha(raw) == expected, 'Snapshot byte mismatch: ' + path)
            target = mapped_path(role, path)
            require(target not in files, 'Duplicate mapped destination')
            files[target] = check_source_bytes(target, raw)
            mapping.append({'source_repository':record['repository'], 'source_commit':record['merge_commit'],
                            'source_path':path, 'destination_path':target, 'sha256':expected})
    require(sum(map(len, files.values())) <= MAX_TOTAL, 'Snapshot exceeds publication byte budget')
    return files, mapping


def read_archive(path):
    result = {}
    with tarfile.open(path, 'r') as t:
        for entry in t:
            if entry.isdir(): continue
            require(entry.isfile(), 'Non-regular source Git entry: ' + entry.name)
            name = safe_relative(entry.name)
            require(name not in result and entry.size <= MAX_FILE, 'Duplicate/oversize Git archive entry')
            result[name] = t.extractfile(entry).read()
    return result


def git_blob_sha(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def receipt_load(path=ROOT/'publication_receipt.json'):
    raw = Path(path).read_bytes()
    require(sha(raw) == RECEIPT_SHA256, 'The supplied publication receipt changed')
    value = json.loads(raw)
    require(set(value) == {'private','public'}, 'Unexpected source receipt roles')
    for role, name in zip(['private','public'], EXTRAS):
        r = value[role]
        require(r['repository'] == name and r.get('merged') is True, 'Source receipt identity or completion mismatch')
        require(re.fullmatch('[a-f0-9]{40}', r['merge_commit']) is not None, 'Invalid source SHA')
    return value


def notebook_bytes():
    import uuid
    def cell(kind, text):
        d={'cell_type':kind,'id':uuid.uuid5(uuid.NAMESPACE_URL, text).hex[:8], 'metadata':{}, 'source':text.splitlines(True)}
        if kind=='code':d.update(execution_count=None,outputs=[])
        return d
    cells=[cell('markdown', '# Research evidence review\n\nReport-only notebook: reads recorded aggregate validation results. It never trains a model or submits predictions. Historical validation is not the 2026 leaderboard. Run from this repository with the existing Python (March Mania) kernel. The implementation archives and protocols are linked in `research/README.md`.\n'),
    cell('code', "from pathlib import Path\nimport pandas as pd\nimport plotly.express as px\nimport plotly.io as pio\nfrom IPython.display import display\npio.renderers.default = 'plotly_mimetype'\nbase = Path.cwd().resolve()\nrepo = next((p for p in [base, *base.parents] if (p/'portfolio/validation_metrics.csv').is_file()), None)\nassert repo is not None, 'Open this notebook inside the original repository clone.'\ndf = pd.read_csv(repo/'portfolio/validation_metrics.csv', dtype={'round':str})\nassert df['brier'].between(0,1).all()\ndisplay(df.head(10))\n"),
    cell('markdown','## Within-round comparisons\nArms are historical labels, not rankings across different validation populations. Compare each arm only with its matching reference.\n'),
    cell('code',"avg=df.groupby(['round','population','arm'],as_index=False)['brier'].mean()\nfig=px.scatter(avg,x='round',y='brier',color='population',symbol='arm',hover_data=['arm'],title='Exploratory mean-season Brier by research round',labels={'brier':'Mean-season Brier (lower is better)','round':'Research round'})\nfig.show()\nrefs=df[df.arm=='Reference'][['round','population','season','brier']].rename(columns={'brier':'reference_brier'})\npaired=df.merge(refs,on=['round','population','season'],validate='many_to_one')\npaired['delta']=paired.brier-paired.reference_brier\nfig=px.box(paired[paired.arm!='Reference'],x='round',y='delta',color='population',points='all',hover_data=['season','arm'],title='Within-round Brier changes by season',labels={'delta':'Brier change vs matching reference','round':'Research round'})\nfig.add_hline(y=0)\nfig.show()\n"),
    cell('markdown','## Evaluation coverage\nMore comparisons are not proof of better predictions. Seasons are reused exploratory history; no untouched test is claimed.\n'),
    cell('code',"coverage=df.groupby(['round','population'],as_index=False).agg(seasons=('season','nunique'),comparisons=('arm','size'))\nfig=px.bar(coverage,x='round',y='comparisons',color='population',barmode='group',hover_data=['seasons'],title='Reported comparisons and season coverage',labels={'comparisons':'Recorded comparison rows','round':'Research round'})\nfig.show()\ndisplay(coverage)\n")]
    return (json.dumps({'cells':cells,'metadata':{'kernelspec':{'display_name':'Python (March Mania)','language':'python','name':'march-mania'}},'nbformat':4,'nbformat_minor':5},indent=1)+'\n').encode()


def front_matter(mapping, receipt):
    kit_counts = {}
    for m in mapping:
        p=m['destination_path']
        if p.startswith('research/workspace/'):
            k=p.split('/')[2];kit_counts[k]=kit_counts.get(k,0)+1
    readme='''# NCAA Tournament Probability Forecasting

**Feature-first research · point-in-time validation · reproducible ML engineering**

A notebook-led investigation of NCAA men's and women's tournament win probabilities,
with basketball-informed features, whole-season validation, controlled ablations,
calibration diagnostics, and restartable experiments.

| Reported result | Interpretation |
|---|---|
| **0.1222672 Brier** | Best previously recorded late, retrospective Kaggle submission; not a prospective rank |
| **0.1097454 target** | Historical research target, not an achieved score or guarantee |
| **Feature research remains open** | Negative results are retained; additional features require measured value |

## Start here

- [Two-minute employer walkthrough](docs/employer_walkthrough.md)
- [Scored release and model lineage](reports/final_results/README.md)
- [Research index: implementation, notebooks, protocols, and evidence](research/README.md)
- [Report-only Plotly notebook](portfolio/research_results.ipynb)
- [Consolidation provenance and file hashes](research/provenance/MIGRATION.json)

![Previously observed submission scores](reports/final_results/leaders.png)

## What this project demonstrates

**Domain representation.** Team strength, opponent/context adjustments, shooting,
turnovers, rebounding, ranking systems, temporal changes, and conditional matchups.
Features are evaluated through fixed-reference comparisons, family ablations and
season-level stability; column count alone is not evidence of quality.

**Validation and engineering.** Pre-tournament information cutoffs, earlier-season
training, train-only transformations, game identity checks, team-swap symmetry,
content-addressed checkpoints, explicit stop conditions and UTC progress records.

**Transparent results.** The original scored release is preserved. The research
extension includes both useful and unsuccessful hypotheses and distinguishes
prepared code, user-executed experiments, historical validation, and Kaggle scores.
Previously explored 2022–2025 seasons are not described as untouched tests.

## Read the notebooks

The original executed review notebooks remain in [notebooks/](notebooks/).
Source copies of the AWS research notebooks are indexed in [research/](research/).
These imported source snapshots intentionally omit execution outputs; they are
not claimed to be executed copies. Run their documented workflow in the existing
workspace to generate inline Plotly results and checkpointed evidence.

## One repository

**This is the project's sole publication destination:**
`alvaromendizabal/march-machine-learning-mania-2026`.

Research implementation is now intentionally public at the owner's request.
Earlier split-repository/privacy instructions survive only in historical source
archives and are superseded by [the repository policy](docs/REPOSITORY_POLICY.md).
No new private or portfolio repository should be created by the current workflow.

Raw competition data, credentials, environments and fitted-model binaries are not
Git source. They remain in their original storage. The AWS experiment checkout is
not destructively reset by publication. See [workspace execution](research/EXECUTION.md).

## Limitations and next work

Local Brier scores concern different games and cannot be equated with the Kaggle
score. Repeated experimentation can overfit reused validation seasons. A promising
compact-reference gain still needs assessment against the stronger released recipe.
The next prepared pair is **round 20 (pace/variance context)** and **round 21
(opponent-style responses)**; no new result for either is asserted by this migration.

Existing MIT license and third-party notices remain in place. Competition data is
subject to its own terms. Publication is not a competition submission.
'''
    index=['# Research implementation and evidence','','This index consolidates the already-published AWS source snapshot into the original repository.','No training is run by migration. Source snapshots preserve filenames, formulas and completion receipts.','','| Workspace component | Source files | Browse |','|---|---:|---|']
    for name,count in sorted(kit_counts.items()): index.append(f'| `{name}` | {count} | [Files](workspace/{name}/) |')
    index += ['', '## Next two prepared rounds', '',
              '[Round 20 notebook](workspace/march_next_steps/rounds_20_21/20_pace_and_variance.ipynb) · [Protocol](workspace/march_next_steps/rounds_20_21/ROUND_20_PROTOCOL.md)',
              '', '[Round 21 notebook](workspace/march_next_steps/rounds_20_21/21_opponent_style_responses.ipynb) · [Protocol](workspace/march_next_steps/rounds_20_21/ROUND_21_PROTOCOL.md)',
              '', 'Each retains four candidates, two families, four controls, six fixed configurations, a smoke/reuse gate, four reference replays, at most 20 new classifiers, zero new rating fits and ten planned inline Plotly figures.',
              '', 'Do not run historical publication helpers that create extra repositories. Use the single-destination consolidator only. Research modules are not imported or executed by the migration.',
              '', '## Evidence and reproducibility', '',
              '[Original public presentation snapshot](publication_archive/) · [Complete source mapping](provenance/MIGRATION.json) · [Workspace instructions](EXECUTION.md)',
              '', 'Imported notebooks have source but no scientific execution outputs. The original six review notebooks retain their existing published outputs. Report-only plots can be reproduced from the supplied aggregate tables without private data.']
    migration={'schema':1,'destination':TARGET,'version':VERSION,'source_files':mapping,
               'source_commits':{v['repository']:v['merge_commit'] for v in receipt.values()},
               'scientific_work_executed':False,'execution_scope':'Publication and preservation only',
               'authorization':'Owner explicitly requested public-source consolidation into the original repository and deletion of the two extra repositories after preservation.'}
    return {'README.md':readme.encode(), 'research/README.md':('\n'.join(index)+'\n').encode(),
            'research/provenance/MIGRATION.json':(json.dumps(migration,indent=2)+'\n').encode(),
            'docs/REPOSITORY_POLICY.md':('''# Repository publication policy

Sole target: `alvaromendizabal/march-machine-learning-mania-2026` (public).
The owner superseded the private-source/public-portfolio split. Do not recreate
`march-mania-research` or `march-mania-portfolio`. Their snapshots are consolidated
here with file hashes; local history backups precede their deletion.

Do not publish credentials, environment directories, raw restricted data or
unreviewed binary models. A request to publish source is not permission to expose
credentials or overwrite the research workspace. Never use force push or bypass
required checks. Any historical scripts in archived directories describing two
publication destinations are obsolete instructions, retained only for provenance.

Scientific execution remains separate from publication. No unexecuted notebook or
prepared test is described as completed. Existing licenses remain unchanged.
''').encode(),
            'research/EXECUTION.md':('''# Existing AWS execution paths

Keep the current `march-mania-dev` space and its original scientific checkout.
The consolidator uses a separate local clone of THIS SAME repository for safe
publication; it does not create another GitHub repository or reset the experiment
checkout. Source snapshot equality is recorded in the migration manifest. The
original experiment checkout remains pinned because existing checkpoints validate
its source, environment and data identity.

Run the existing next pair from `$HOME/march_next_steps/rounds_20_21` with
`$HOME/march-machine-learning-mania-2026/.venv/bin/python`.
Use `run_tests.py`, then notebook 20, then notebook 21; keep all `private_runs`.
They retain the documented cutoff, fixed features and reused validation years.

A fresh clone contains archived implementation, not raw data or fitted caches.
It is not a claim that all notebooks can run without restoring their documented
inputs. Do not execute two-repository publication scripts from archived folders.
''').encode(),
            'portfolio/DISCLOSURE.md':('''# Publication and evaluation disclosure

The owner has requested that research source and the employer-facing portfolio
reside together in this original public repository. Earlier private/public split
instructions are superseded. The earlier presentation snapshot remains archived
under `research/publication_archive` for byte-level provenance, not as the current
publication policy. Existing MIT and third-party notices are unchanged.

The reported 0.1222672 is a late retrospective submission score. Historical fold
metrics use other populations and are not leaderboard scores. Prepared rounds are
not measured results. Imported source notebooks omit outputs; existing executed
release notebooks are retained. No new predictive improvement is claimed here.
''').encode(),
            'portfolio/research_results.ipynb':notebook_bytes()}


class Runner:
    def __init__(self, home=None):
        self.home = Path(home or Path.home()).absolute()
        self.work = no_links(self.home/'march_publication'/'canonical')
        self.work.mkdir(parents=True,exist_ok=True)
        self.state_path=self.work/'state.json'
        self.state=json.loads(self.state_path.read_text()) if self.state_path.exists() else {'version':VERSION,'target':TARGET}
        require(self.state.get('target')==TARGET and self.state.get('version')==VERSION,'Unexpected consolidation state')
        self.gh=shutil.which('gh') or str(self.home/'.local/bin/gh')
        self.env=os.environ.copy()
        self.env.update(GIT_TERMINAL_PROMPT='0',GH_PROMPT_DISABLED='1',GH_HOST='github.com',GH_PAGER='cat',PAGER='cat',GIT_LFS_SKIP_SMUDGE='1')
        self.env['PATH']=str(self.home/'.local/bin')+os.pathsep+self.env.get('PATH','')
        self.receipt=receipt_load()

    def save(self, **updates):
        self.state.update(updates);self.state['updated_utc']=stamp();atomic(self.state_path,self.state)
        with zipfile.ZipFile(self.work/'consolidation_return.zip','w',zipfile.ZIP_DEFLATED) as z:
            z.write(self.state_path,'state.json')
            for name in ['plan.json','checks.json','failure.json']:
                p=self.work/name
                if p.is_file():z.write(p,name)

    def cmd(self,args,cwd=None,timeout=180,input_bytes=None,check=True,env_overrides=None):
        env=self.env.copy()
        if env_overrides: env.update(env_overrides)
        if args[0]=='git':
            args=['git','-c','credential.helper=','-c','credential.https://github.com.helper=!'+shlex.quote(self.gh)+' auth git-credential','-c','core.autocrlf=false',*args[1:]]
        start=time.monotonic()
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            p=subprocess.Popen(args,cwd=cwd,env=env,stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
            try:
                sent=False
                while True:
                    remaining=timeout-(time.monotonic()-start)
                    if remaining<=0:raise TimeoutError('Command exceeded '+str(timeout)+' seconds: '+args[0])
                    try:
                        p.communicate(input=input_bytes if not sent else None,timeout=min(15,remaining))
                        break
                    except subprocess.TimeoutExpired:
                        sent=True
                        event('heartbeat',operation=args[0]+' '+(' '.join(args[-2:]) if args[0]!=self.gh else 'GitHub request'),elapsed_seconds=round(time.monotonic()-start,1))
                out.seek(0); stdout=out.read();err.seek(0);stderr=err.read().decode('utf-8','replace')
            except BaseException:
                if p.poll() is None:
                    os.killpg(p.pid,signal.SIGTERM)
                    try:p.wait(timeout=3)
                    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                raise
        if check and p.returncode:raise RuntimeError(f'Command failed ({p.returncode}): {redacted(stderr)}')
        return p.returncode,stdout,stderr

    def api(self,path,method='GET',payload=None):
        args=[self.gh,'api','--hostname','github.com','--method',method,path]
        if payload is not None:args+=['--input','-']
        raw=self.cmd(args,input_bytes=json.dumps(payload).encode() if payload is not None else None)[1]
        return json.loads(raw) if raw.strip() else {}

    def auth(self):
        require(Path(self.gh).is_file(),'Existing GitHub CLI not found. No installer or login was started.')
        require(self.api('user').get('login')==OWNER,'Existing CLI session is not the expected owner. No login was started.')
        r=self.api('repos/'+TARGET)
        require(int(r['id'])==TARGET_ID and not r['private'] and r['default_branch']=='main','Original destination identity/visibility changed')
        require(r.get('permissions',{}).get('push') is True,'No write permission on the original repository')
        event('authenticated',target=TARGET,created_repositories=0)
        return r

    def clone_sources(self):
        states,contents={},{}
        for role in ['private','public']:
            record=self.receipt[role];path=Path(record['clone'])
            # Rebase the supplied /home/sagemaker-user path only onto the user's actual HOME.
            rel=path.relative_to('/home/sagemaker-user')
            source=no_links(self.home/rel)
            require((source/'.git').is_dir(),'Published local clone is missing: '+str(source)+'. No data was deleted. Restore the recorded clone before migration.')
            origin=self.cmd(['git','remote','get-url','origin'],cwd=source)[1].decode().strip()
            require(origin=='https://github.com/'+record['repository']+'.git','Unexpected local source origin')
            commit=record['merge_commit']
            self.cmd(['git','cat-file','-e',commit+'^{commit}'],cwd=source)
            backup=self.work/'backups'/role
            backup.mkdir(parents=True,exist_ok=True)
            mirror=backup/'history.git'
            if not mirror.exists():self.cmd(['git','clone','--mirror','--no-hardlinks',str(source),str(mirror)],timeout=300)
            else:require((mirror/'HEAD').is_file(),'Unexpected backup directory')
            self.cmd(['git','cat-file','-e',commit+'^{commit}'],cwd=mirror)
            bundle=backup/'history.bundle'
            if not bundle.exists():self.cmd(['git','bundle','create',str(bundle),'--all'],cwd=mirror,timeout=180)
            self.cmd(['git','bundle','verify',str(bundle)],cwd=mirror)
            self.cmd(['git','fsck','--full','--no-dangling'],cwd=mirror,timeout=180)
            archive=backup/'snapshot.tar'
            if not archive.exists():self.cmd(['git','archive','--format=tar','--output='+str(archive),commit],cwd=mirror)
            raw=read_archive(archive)
            for p,h in record['published_files'].items():
                require(p in raw and sha(raw[p])==h,'Recorded published file not preserved: '+p)
            # Commit reference and bundle included in local archive; never send backups to GitHub.
            contents[role]={p:raw[p] for p in record['published_files']}
            refs=self.cmd(['git','for-each-ref','--format=%(objectname) %(refname)'],cwd=mirror)[1].decode()
            atomic(backup/'refs.txt',refs.encode())
            states[role]={'source_repository':record['repository'],'source_commit':commit,'bundle':str(bundle),'bundle_sha256':sha(bundle.read_bytes()),'mirror':str(mirror),'snapshot_sha256':sha(archive.read_bytes()),'files_verified':len(contents[role])}
        return states,contents

    def make_plan(self):
        self.auth()
        if self.state.get('merged_verified'):event('already_migrated',commit=self.state['merge_commit']);return
        backups,contents=self.clone_sources()
        files,mapping=build_payload(contents,self.receipt)
        files.update(front_matter(mapping,self.receipt))
        # Current single-repository tooling is published alongside the historical snapshot.
        for relative in ['consolidate_march.py','publication_receipt.json','START_HERE.md','RESEARCH_NEXT.md']:
            p = ROOT/relative
            if p.is_file(): files['tools/consolidation/'+relative] = p.read_bytes()
        for p in sorted((ROOT/'tests').glob('test_*.py')):
            files['tools/consolidation/tests/'+p.name] = p.read_bytes()
        files['portfolio/validation_metrics.csv']=contents['public']['data/validation_metrics.csv']
        stage=self.work/'stage';stage.mkdir(exist_ok=True)
        for name,raw in files.items():atomic(stage/name,raw)
        expected={p:sha(b) for p,b in files.items()}
        previous=self.state.get('payload_hashes')
        require(previous is None or previous==expected,'Staging differs from the saved plan; original plan preserved')
        original=self.api('repos/'+TARGET+'/git/ref/heads/main')['object']['sha']
        self.save(status='PLAN_READY',backups=backups,payload_hashes=expected,source_mapping=mapping,
                  target_base=self.state.get('target_base',original),stage=str(stage),published_source_files=len(mapping),created_repositories=0,
                  original_aws_checkout_modified=False,project_models_fitted=0)
        plan={'target':TARGET,'source_files':len(mapping),'all_source_sha256_matched':True,'archive_mapping':mapping,
              'additional_presentation_files':sorted(set(files)-{m['destination_path'] for m in mapping}),
              'not_in_scope':'Raw data, environments, model binaries and changes after the supplied publication snapshot are not in this receipt. Originals remain on AWS.',
              'delete_only_after_verified_merge':list(EXTRAS),'backups':backups}
        atomic(self.work/'plan.json',plan)
        atomic(self.work/'REVIEW.md',('# Original-repository consolidation\n\nTarget: `'+TARGET+'` (public)\n\nAll '+str(len(mapping))+' receipt-listed files retain their original bytes. Original root scientific code, six executed notebooks and CI remain untouched. Imported source resides under research/. Current documentation supersedes the split-repository instructions.\n\nNo GitHub repository will be created. Both extra repositories are eligible for deletion only after main contains every migration hash and the backed-up source commit is confirmed unchanged.\n\n## Files\n\n'+'\n'.join('- `'+p+'`' for p in sorted(files))+'\n').encode())
        self.save()
        event('PLAN_READY',source_files=len(mapping),target=TARGET,review=str(self.work/'REVIEW.md'))

    def clone_target(self):
        clone=self.work/'original-repository-checkout'
        if not clone.exists():self.cmd(['git','clone','https://github.com/'+TARGET+'.git',str(clone)],timeout=300)
        require((clone/'.git').is_dir(),'Destination local directory is not a clone')
        require(self.cmd(['git','remote','get-url','origin'],cwd=clone)[1].decode().strip()=='https://github.com/'+TARGET+'.git','Wrong target remote')
        return clone

    def stage_index(self,clone):
        hashes=self.state['payload_hashes']; stage=Path(self.state['stage']); records=[]
        index_env={'GIT_INDEX_FILE':str(no_links(self.work/'migration.index'))}
        self.cmd(['git','read-tree',self.state['target_base']],cwd=clone,env_overrides=index_env)
        for path,h in sorted(hashes.items()):
            raw=(stage/path).read_bytes();require(sha(raw)==h,'Staged bytes changed: '+path)
            blob=self.cmd(['git','hash-object','-w','--stdin','--no-filters'],cwd=clone,input_bytes=raw)[1].decode().strip()
            require(blob==git_blob_sha(raw),'Git object verification failed')
            records.append(('100644 '+blob+'\t'+safe_relative(path)+'\0').encode())
        self.cmd(['git','update-index','-z','--index-info'],cwd=clone,input_bytes=b''.join(records),env_overrides=index_env)
        tree=self.cmd(['git','write-tree'],cwd=clone,env_overrides=index_env)[1].decode().strip()
        # Preserved source may have historic whitespace; bytes are not rewritten to disguise it.
        checks=self.cmd(['git','diff','--cached','--check'],cwd=clone,check=False,env_overrides=index_env)
        atomic(self.work/'whitespace_review.txt',checks[1])
        return tree

    def publish(self):
        self.auth()
        require(self.state.get('status') not in {None,'FAILED'} or self.state.get('payload_hashes'),'Run plan first')
        require(self.state.get('payload_hashes'),'Run plan first')
        if self.state.get('merged_verified'):event('already_migrated',commit=self.state['merge_commit']);return
        clone=self.clone_target()
        branch='maintenance/consolidate-aws-research-'+sha(json.dumps(self.state['payload_hashes'],sort_keys=True).encode())[:10]
        if not self.state.get('commit'):
            require(self.api('repos/'+TARGET+'/git/ref/heads/main')['object']['sha']==self.state['target_base'],'Original main changed; preserve this plan and review the new base before publishing')
            tree=self.stage_index(clone)
            self.cmd(['git','config','user.name','Alvaro Mendizabal'],cwd=clone)
            self.cmd(['git','config','user.email','108156083+alvaromendizabal@users.noreply.github.com'],cwd=clone)
            message='Consolidate AWS research into the original public repository\n\nPreserve receipt-listed research source byte-for-byte, retain legacy release and CI, and add a navigable employer-facing research index. No scientific fitting or new repository creation.\n'
            commit=self.cmd(['git','commit-tree',tree,'-p',self.state['target_base']],cwd=clone,input_bytes=message.encode())[1].decode().strip()
            self.cmd(['git','update-ref','refs/heads/'+branch,commit],cwd=clone)
            self.save(commit=commit,branch=branch,clone=str(clone),status='COMMITTED_LOCAL')
        self.verify_objects(clone,self.state['commit'])
        # Push EXACTLY one normal branch to the original repository. Never force.
        self.cmd(['git','push','origin',self.state['commit']+':refs/heads/'+branch],cwd=clone,timeout=300)
        remote=self.api('repos/'+TARGET+'/git/ref/heads/'+branch)['object']['sha']
        require(remote==self.state['commit'],'Remote branch SHA differs from published commit')
        self.save(status='PUSHED')
        existing=self.api('repos/'+TARGET+'/pulls?state=all&head='+OWNER+':'+branch+'&base=main&per_page=100')
        prs=[p for p in existing if p['head']['sha']==self.state['commit']]
        require(len(prs)<=1,'Multiple matching PRs require review')
        if prs:p=prs[0]
        else:p=self.api('repos/'+TARGET+'/pulls',method='POST',payload={'title':'Consolidate research source and portfolio into the original repository','head':branch,'base':'main','body':self.pr_body()})
        self.save(pr_number=p['number'],pr_url=p['html_url'],status='PULL_REQUEST_OPEN')
        event('PUSHED_TO_ORIGINAL',repository=TARGET,commit=self.state['commit'],pr=p['html_url'])

    def pr_body(self):
        return ('Owner-requested consolidation into the ORIGINAL repository only.\n\n'
                f'- {self.state["published_source_files"]} receipt-listed source/presentation files preserved by SHA-256 under research/.\n'
                '- Existing root scientific source, canonical executed release notebooks, license and CI remain unchanged.\n'
                '- New research modules are archived source: this PR does not claim their tests or notebooks were executed.\n'
                '- Updated employer-facing README, navigable implementation index, report-only Plotly notebook and exact source mapping.\n'
                '- No credentials, model binaries, raw data or local Git-history backups included.\n'
                '- The two extra repositories are deleted separately ONLY after merge/hash verification and local backups.\n'
                '- No new repositories, force pushes, automatic experiments or CI bypass.\n')

    def verify_objects(self,clone,commit):
        raw=self.cmd(['git','ls-tree','-r','-z',commit],cwd=clone)[1]
        tree={}
        for item in raw.split(b'\0'):
            if item:
                meta,path=item.split(b'\t',1);mode,typ,oid=meta.decode().split();tree[path.decode()]=(mode,typ,oid)
        for path,h in self.state['payload_hashes'].items():
            data=(Path(self.state['stage'])/path).read_bytes()
            require(sha(data)==h and path in tree and tree[path][1]=='blob' and tree[path][2]==git_blob_sha(data),'Target commit file mismatch: '+path)
        return len(self.state['payload_hashes'])

    def check_ci(self,commit):
        rows=[];page=1
        while True:
            r=self.api('repos/'+TARGET+'/commits/'+commit+'/check-runs?per_page=100&page='+str(page))
            batch=r.get('check_runs',[]);rows+=batch
            if len(batch)<100:break
            page+=1;require(page<=10,'Unexpected CI result size')
        latest={}
        for r in sorted(rows,key=lambda x:x['id']):latest[r['name']]=r
        status=self.api('repos/'+TARGET+'/commits/'+commit+'/status?per_page=100')
        summary={name:{k:r.get(k) for k in ['status','conclusion','head_sha','html_url']} for name,r in latest.items()}
        atomic(self.work/'checks.json',{'sha':commit,'checks':summary,'combined_state':status.get('state')})
        fail=[n for n,r in latest.items() if r.get('status')=='completed' and r.get('conclusion') not in {'success','skipped','neutral'}]
        require(not fail,'CI failed: '+', '.join(fail)+'. No merge or deletion performed; inspect the PR.')
        require(not any(s.get('state') in {'failure','error'} for s in status.get('statuses',[])),'A commit status failed')
        ready=REQUIRED_CHECKS.issubset(latest) and all(latest[n].get('conclusion')=='success' and latest[n].get('head_sha')==commit for n in REQUIRED_CHECKS)
        ready=ready and all(r.get('status')=='completed' for r in latest.values()) and all(s.get('state')=='success' for s in status.get('statuses',[]))
        return ready

    def finish(self, wait=600):
        self.auth();require(self.state.get('pr_number'),'Publish the plan first')
        begin=time.monotonic();number=self.state['pr_number']
        while True:
            p=self.api('repos/'+TARGET+'/pulls/'+str(number))
            require(p['head']['sha']==self.state['commit'],'PR head changed; no merge performed')
            if p.get('merged'):
                merge=p['merge_commit_sha'];break
            require(p['state']=='open','PR was closed without merging')
            if self.check_ci(self.state['commit']):
                m=self.api('repos/'+TARGET+'/pulls/'+str(number)+'/merge',method='PUT',payload={'sha':self.state['commit'],'merge_method':'merge','commit_title':'Consolidate AWS research in the original repository'})
                require(m.get('merged') is True,'GitHub did not confirm the merge')
                merge=m['sha'];break
            if time.monotonic()-begin>=wait:
                self.save(status='CHECKS_PENDING',pr_url=p['html_url'])
                event('CHECKS_PENDING',pr=p['html_url'],next_command='python3 consolidate_march.py finish --wait 600')
                return False
            event('waiting_for_original_ci',pr=number,elapsed_seconds=round(time.monotonic()-begin,1),limit_seconds=wait)
            time.sleep(min(15,max(0.1,wait-(time.monotonic()-begin))))
        clone=Path(self.state['clone']);self.cmd(['git','fetch','origin','main'],cwd=clone)
        head=self.cmd(['git','rev-parse','FETCH_HEAD'],cwd=clone)[1].decode().strip()
        self.cmd(['git','merge-base','--is-ancestor',merge,head],cwd=clone)
        count=self.verify_objects(clone,head)
        require(not self.cmd(['git','status','--porcelain'],cwd=clone)[1].strip(), 'Publication clone has local edits; merged remote is preserved, but no local changes will be overwritten')
        self.cmd(['git','switch','main'],cwd=clone)
        self.cmd(['git','merge','--ff-only',head],cwd=clone)
        require(self.cmd(['git','rev-parse','HEAD'],cwd=clone)[1].decode().strip()==head,'Publication clone did not advance to verified main')
        self.save(status='MERGED_IN_ORIGINAL_AND_VERIFIED',merge_commit=merge,verified_main=head,merged_verified=True,verified_files=count)
        legacy=self.retire_legacy_publisher()
        self.save(retired_legacy_publisher=legacy)
        event('MERGED_IN_ORIGINAL_AND_VERIFIED',repository=TARGET,main=head,verified_files=count,source_files=self.state['published_source_files'])
        return True

    def retire_legacy_publisher(self):
        """Disable only the receipt-matching obsolete publication helper, not research code."""
        old = no_links(self.home/'march_next_steps/github_publish.py')
        wrapper = ("#!/usr/bin/env python3\n"
                   "\"\"\"Retired two-repository publisher. Existing source is preserved in the consolidation backup.\"\"\"\n"
                   "import sys\n"
                   "print('The two-repository publisher is retired. Do not create extra repositories.')\n"
                   "print('Use ~/march_canonical_release/consolidate_march.py instead.')\n"
                   "print('Only destination: alvaromendizabal/march-machine-learning-mania-2026')\n"
                   "sys.exit(2)\n").encode()
        if not old.exists(): return {'status':'NOT_PRESENT'}
        raw = old.read_bytes()
        if raw == wrapper: return {'status':'ALREADY_RETIRED'}
        expected = [h for p,h in self.receipt['private']['published_files'].items()
                    if p.endswith('/research/march_next_steps/github_publish.py')]
        if len(expected)!=1 or sha(raw)!=expected[0]:
            event('legacy_helper_not_overwritten',reason='Unrecognized local edit preserved; do not run the old publisher.')
            return {'status':'LOCAL_EDIT_PRESERVED_NOT_RETIRED'}
        backup=self.work/'backups/retired_helpers/github_publish.py'
        if backup.exists(): require(backup.read_bytes()==raw,'Retired-helper backup differs; preserve both versions')
        else: atomic(backup,raw)
        require(old.read_bytes()==raw,'Legacy helper changed during verification')
        atomic(old,wrapper)
        return {'status':'RETIRED_AFTER_VERIFIED_MIGRATION','backup':str(backup),'original_sha256':sha(raw)}

    def owned_repository_names(self):
        names=set();page=1
        while True:
            batch=self.api('user/repos?affiliation=owner&per_page=100&page='+str(page))
            names.update(r['full_name'] for r in batch if r.get('owner',{}).get('login')==OWNER)
            if len(batch)<100:break
            page+=1;require(page<=100,'Owner listing unexpectedly large')
        return names

    def cleanup(self):
        self.auth();require(self.state.get('merged_verified') is True,'Deletion forbidden before verified migration')
        clone=Path(self.state['clone']);self.cmd(['git','fetch','origin','main'],cwd=clone)
        head=self.cmd(['git','rev-parse','FETCH_HEAD'],cwd=clone)[1].decode().strip();self.verify_objects(clone,head)
        outcomes=self.state.get('cleanup',{})
        for role,name in zip(['private','public'], EXTRAS):
            require(name!=TARGET and name in EXTRAS,'Refusing to delete original or an unapproved repository')
            b=self.state['backups'][role];bundle=Path(b['bundle'])
            require(bundle.is_file() and sha(bundle.read_bytes())==b['bundle_sha256'],'History backup missing or changed; no deletion')
            self.cmd(['git','bundle','verify',str(bundle)],cwd=Path(b['mirror']))
            if name not in self.owned_repository_names():
                if outcomes.get(name,{}).get('status')=='DELETED':
                    continue
                outcomes[name]={'status':'NOT_VISIBLE_DELETION_NOT_CONFIRMED'}
                self.save(status='MIGRATED_CLEANUP_UNVERIFIED',cleanup=outcomes)
                event('MIGRATED_CLEANUP_UNVERIFIED',repository=name,detail='Not visible in the owner listing; no deletion is claimed. The original migration remains verified.')
                return False
            r=self.api('repos/'+name)
            require(r['full_name']==name and int(r['id'])!=TARGET_ID and r['owner']['login']==OWNER,'Deletion identity mismatch')
            require(r.get('permissions',{}).get('admin') is True,'Repository deletion requires admin permission')
            current=self.api('repos/'+name+'/git/ref/heads/main')['object']['sha']
            require(current==self.receipt[role]['merge_commit'],'Extra repository has new main work. No deletion; back up and migrate that new work first.')
            # All remote branches/tags must also be represented in the independent mirror.
            refs=self.cmd(['git','ls-remote','--heads','--tags','--refs','https://github.com/'+name+'.git'])[1].decode().splitlines()
            for line in refs:
                oid,ref=line.split('\t')
                self.cmd(['git','cat-file','-e',oid],cwd=Path(b['mirror']))
            metadata={'repository':r,'verified_refs':refs,'saved_utc':stamp()}
            for family in ['issues','pulls','releases']:
                collected=[];page=1
                while True:
                    q='?per_page=100&page='+str(page)+('&state=all' if family in ['issues','pulls'] else '')
                    batch=self.api('repos/'+name+'/'+family+q);collected+=batch
                    if len(batch)<100:break
                    page+=1;require(page<=10,'Additional repository metadata needs separate review')
                metadata[family]=collected
            metadata['discussion_details'] = {}
            for issue in metadata['issues']:
                number = issue['number']
                details = {}
                endpoints = ['issues/'+str(number)+'/comments']
                if 'pull_request' in issue: endpoints += ['pulls/'+str(number)+'/reviews','pulls/'+str(number)+'/comments']
                for endpoint in endpoints:
                    values=[];page=1
                    while True:
                        batch=self.api('repos/'+name+'/'+endpoint+'?per_page=100&page='+str(page)); values+=batch
                        if len(batch)<100: break
                        page+=1; require(page<=10,'Discussion requires a larger explicit backup')
                    details[endpoint]=values
                metadata['discussion_details'][str(number)]=details
            require(not any(x.get('assets') for x in metadata['releases']),'Release assets need independent backup before deletion')
            # Main code/history and top-level metadata preserved; GitHub settings and all comments are not a full migration archive.
            atomic(Path(b['mirror']).parent/'github_metadata.json',metadata)
            code,out,err=self.cmd([self.gh,'repo','delete',name,'--yes'],check=False)
            if code:
                outcomes[name]={'status':'DELETION_PERMISSION_OR_POLICY_REQUIRED','error':redacted(err)}
                self.save(status='MIGRATED_CLEANUP_PENDING',cleanup=outcomes)
                event('MIGRATED_CLEANUP_PENDING',repository=name,detail='Migration is complete. Deletion was refused; no automatic scope change. See receipt.');return False
            require(name not in self.owned_repository_names(),'Deletion not confirmed by owner listing')
            outcomes[name]={'status':'DELETED','repository_id':r['id'],'source_commit':current,'backup_sha256':b['bundle_sha256']}
            self.save(cleanup=outcomes);event('EXTRA_REPOSITORY_DELETED',repository=name)
        self.save(status='CONSOLIDATED_AND_EXTRA_REPOSITORIES_REMOVED',cleanup=outcomes)
        event('CONSOLIDATED_AND_EXTRA_REPOSITORIES_REMOVED',original=TARGET,receipt=str(self.work/'consolidation_return.zip'))
        return True

    @contextlib.contextmanager
    def locked(self):
        import fcntl
        with open(no_links(self.work/'operation.lock'),'a+') as f:
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise RuntimeError('Another consolidation process is running')
            try:yield
            finally:fcntl.flock(f,fcntl.LOCK_UN)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','publish','finish','cleanup','run'])
    parser.add_argument('--approve-public-source',action='store_true',help='Explicitly authorize publishing the receipt-listed source into the original PUBLIC repo')
    parser.add_argument('--delete-extra-repos',action='store_true',help='Remove only the two fixed extra repos after verified migration and backups')
    parser.add_argument('--wait',type=int,default=600,help='Bounded CI polling seconds, 0–900')
    args=parser.parse_args();require(0<=args.wait<=900,'CI wait must be 0–900 seconds')
    if args.action in {'publish','run'}:require(args.approve_public_source,'Add --approve-public-source to explicitly approve the original public destination')
    if args.action=='cleanup':require(args.delete_extra_repos,'Add --delete-extra-repos for the explicitly requested cleanup')
    runner=Runner()
    try:
        with runner.locked():
            if args.action=='plan':runner.make_plan()
            elif args.action=='publish':runner.publish()
            elif args.action=='finish':runner.finish(args.wait)
            elif args.action=='cleanup':runner.cleanup()
            else:
                runner.make_plan();runner.publish()
                if runner.finish(args.wait) and args.delete_extra_repos:runner.cleanup()
        print('RECEIPT:',runner.work/'consolidation_return.zip')
    except Exception as exc:
        atomic(runner.work/'failure.json',{'utc':stamp(),'error':redacted(str(exc)),'type':type(exc).__name__,'target':TARGET,'action':args.action})
        runner.save(last_error=redacted(str(exc)))
        print('STOP:',redacted(str(exc)),file=sys.stderr)
        print('Return:',runner.work/'consolidation_return.zip',file=sys.stderr)
        raise SystemExit(1)

if __name__=='__main__':main()
