"""User-run device login and reviewed publication. Not executed by the assistant.

Never operates the experiment's original Git checkout. Only separate publication
clones are committed. No credentials are captured in logs or return packages.
"""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,sys,time,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OWNER='alvaromendizabal'
TARGETS={'private':('march-mania-research',True),'public':('march-mania-portfolio',False)}
PUBLIC_FILES=['README.md','RIGHTS.md','CITATION.cff','.gitignore','data/validation_metrics.csv',
 'data/evidence_sources.json','docs/DISCLOSURE.md','docs/EXPERIMENT_LEDGER.md','docs/CASE_STUDY.md',
 'notebooks/portfolio_results.ipynb']

def require(test,msg):
    if not test:raise ValueError(msg)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def atomic(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    require(not path.is_symlink() and not any(p.is_symlink() for p in path.parents),'Unsafe output path')
    tmp=path.with_suffix(path.suffix+'.partial');require(not tmp.is_symlink(),'Unsafe temporary file')
    tmp.write_text(json.dumps(obj,indent=2)+'\n');tmp.replace(path)
def command(args,cwd=None,timeout=120,inherit=False,check=True):
    env=os.environ.copy();env['PATH']=str(Path.home()/'.local/bin')+os.pathsep+env.get('PATH','');env.update(GIT_TERMINAL_PROMPT='0',GH_PROMPT_DISABLED='1',GH_PAGER='cat',PAGER='cat')
    # Use gh only as a per-command HTTPS credential helper, not a global Git change.
    if args[0]=='git':args=['git','-c','credential.helper=','-c','credential.https://github.com.helper=!gh auth git-credential',*args[1:]]
    p=subprocess.run(args,cwd=cwd,env=env,timeout=timeout,text=True,
        stdout=None if inherit else subprocess.PIPE,stderr=None if inherit else subprocess.PIPE)
    if check and p.returncode:
        # Error content can contain credential-bearing URLs: do not save/echo it blindly.
        raise RuntimeError(f'{args[0]} command failed (exit {p.returncode}). No automatic retry or credential dump. Review the specific command locally.')
    return p

def gh_json(*args):return json.loads(command(['gh',*args]).stdout)
def auth():
    """Reuse existing device authorization; do not start a new login automatically."""
    candidate=shutil.which('gh')
    if candidate is None:
        candidate=str(Path.home()/'.local/bin/gh')
        require(Path(candidate).is_file(),'GitHub CLI not found in PATH or ~/.local/bin; no automatic install')
        os.environ['PATH']=str(Path(candidate).parent)+os.pathsep+os.environ.get('PATH','')
    require(not os.environ.get('GH_TOKEN') and not os.environ.get('GITHUB_TOKEN'),
        'A token environment override is present. Do not print it; use the authorized CLI session instead.')
    require(command(['gh','auth','status','--hostname','github.com'],check=False).returncode==0,
        'Existing GitHub login is not usable. No password prompt or new login was started.')
    who=gh_json('api','user')['login']
    require(who==OWNER,'Wrong active GitHub account; no publication attempted')
    print('GITHUB_DEVICE_AUTH: PASS — '+who)


def plan():
    """Always persist the review state, including blocked plans."""
    from publication.stage_private import stage
    from publication.review_support import inspect_previous,diagnostic,UPDATE_ID
    work=Path.home()/'march_publication';work.mkdir(exist_ok=True,mode=0o700)
    require(not work.is_symlink(),'Publication directory must not be a symlink')
    prior=inspect_previous(Path.home())
    stamp=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+os.urandom(3).hex()
    folder=work/'plans'/stamp;folder.mkdir(parents=True,mode=0o700)
    private=stage(Path.home(),folder/'private_source')
    private_record=json.loads((private/'PRIVATE_SNAPSHOT.json').read_text())
    pub=folder/'public_source';pub.mkdir()
    pins=json.loads((ROOT/'PUBLIC_MANIFEST.json').read_text())['sha256']
    require(set(pins)==set(PUBLIC_FILES),'Public allowlist and manifest disagree')
    public_issues=[]
    for n in PUBLIC_FILES:
        file=ROOT/'public_portfolio'/n
        if not file.is_file() or file.is_symlink() or digest(file)!=pins[n]:
            public_issues.append({'path':'public_portfolio/'+n,'reason':'Public source changed; do not publish unreviewed content'})
            continue
        target=pub/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
    maps={role:{str(q.relative_to(folder/(role+'_source'))):digest(q)
        for q in sorted((folder/(role+'_source')).rglob('*')) if q.is_file()} for role in TARGETS}
    blockers=private_record['blocked']+public_issues
    if not private_record['files']: blockers.append({'path':'[snapshot]','reason':'No research source found'})
    record={'plan_dir':str(folder),'plan_id':stamp,'update_id':UPDATE_ID,'targets':TARGETS,'sha256':maps,
        'status':'REVIEW_BLOCKED' if blockers else 'LOCAL_PLAN_READY',
        'missing_source_roots':private_record['missing_known_roots'],'blocked_files':blockers,
        'private_scope':'Current source, tests, configurations and small supplied evidence; NOT old Git history, raw data, models or full executed outputs.',
        'public_scope':'Only the explicit report-only portfolio allowlist, not the private source.',
        'scientific_execution':'None by publication. Test and scientific status remain separate.',
        'prior_blocker_review':prior,'source_exclusions':private_record.get('exclusions',[])}
    review=['# Review before publication','',record['status'],'Plan: '+stamp,
        'Private destination: '+OWNER+'/'+TARGETS['private'][0],
        'Public destination: '+OWNER+'/'+TARGETS['public'][0],
        '',record['private_scope'],'',record['public_scope'],'',
        '## Missing known roots',json.dumps(record['missing_source_roots'],indent=2),
        '## Unresolved blockers',json.dumps(blockers,indent=2),
        '## Excluded generated/private directories',json.dumps(record['source_exclusions'],indent=2),
        '## Previous blocker classifications',json.dumps(prior,indent=2),
        '## Private file list',*maps['private'].keys(),'## Public file list',*maps['public'].keys()]
    (folder/'REVIEW.md').write_text('\n'.join(review)+'\n')
    atomic(folder/'plan.json',record)
    atomic(work/'latest_plan.json',{'path':str(folder/'plan.json'),'sha256':digest(folder/'plan.json')})
    print('REVIEW:',folder/'REVIEW.md')
    print('SOURCE_FILES:',len(private_record['files']))
    print('UNRESOLVED_BLOCKERS:',len(blockers))
    for b in blockers: print(json.dumps(b))
    diagnostic(Path.home(),{'action':'plan','status':record['status']})
    if blockers:
        print('REVIEW_BLOCKED: plan saved. Publish is disabled until these exact source issues are resolved.')
        raise SystemExit(2)
    print('LOCAL_PLAN_READY — source exclusions are explicit; review the file list before publish.')
    return record


def load_plan():
    from publication.review_support import inspect_previous,safe_path
    index=Path.home()/'march_publication/latest_plan.json'
    if not index.is_file():
        old=inspect_previous(Path.home())
        latest=old['plans'][-1] if old['plans'] else None
        if latest and latest['blocked_files']:
            raise ValueError('The prior scan was blocked, not absent. Run github_publish.py inspect, then the revised plan.')
        raise ValueError('No publication plan exists. Run the revised github_publish.py plan.')
    safe_path(index);r=json.loads(index.read_text());file=Path(r['path']);safe_path(file)
    require(file.is_relative_to(Path.home()/'march_publication/plans'),'Unexpected plan location')
    require(digest(file)==r['sha256'],'Plan changed after creation; do not publish')
    result=json.loads(file.read_text());folder=file.parent
    require(result['targets']=={k:list(v) for k,v in TARGETS.items()},'Unexpected publication targets')
    if result.get('blocked_files'):
        raise ValueError(str(len(result['blocked_files']))+' unresolved source blockers remain. Inspect '+str(folder/'REVIEW.md')+'; no remote write attempted.')
    for role,mapping in result['sha256'].items():
        root=folder/(role+'_source');files=set()
        for q in root.rglob('*'):
            safe_path(q)
            if q.is_file(): files.add(str(q.relative_to(root)))
        require(files==set(mapping),'Staged file set changed')
        for n,h in mapping.items():
            rel=Path(n);require(not rel.is_absolute() and '..' not in rel.parts,'Unsafe staged relative path')
            require(digest(root/n)==h,'Staged file changed: '+n)
    return folder,result


def ensure_repo(role):
    name,private=TARGETS[role];full=OWNER+'/'+name
    # Repository lookup errors are not automatically treated as absence. Enumerate
    # authenticated owned repos, then only create a name genuinely absent there.
    raw=command(['gh','api','--paginate','--slurp','user/repos?affiliation=owner&per_page=100']).stdout
    pages=json.loads(raw);owned=[item for page in pages for item in page]
    matches=[x for x in owned if x['full_name']==full]
    require(len(matches)<=1,'Ambiguous repository lookup')
    if not matches:
        command(['gh','repo','create',full,'--private' if private else '--public','--add-readme',
            '--description','Private NCAA research source snapshots' if private else 'NCAA forecasting: public evidence, validation, and private-implementation case study'],inherit=True)
    meta=gh_json('api','repos/'+full)
    require(meta['private'] is private and not meta.get('archived') and meta['owner']['login']==OWNER,
        'Repository visibility/owner/state differs from plan. Nothing will be pushed there.')
    require(meta.get('default_branch'),'Repository has no initialized default branch')
    return full,meta['default_branch']

def public_publish_allowed(role,mapping):
    if role=='public':require(set(mapping)==set(PUBLIC_FILES),'Public publication must contain only the explicit portfolio allowlist')

def publish():
    folder,p=load_plan();auth()
    print('Private source files:',len(p['sha256']['private']),'Public evidence files:',len(p['sha256']['public']))
    print('Review first:',folder/'REVIEW.md')
    require(input('After reviewing the staged files and exclusions, type PUBLISH to commit, push and open both PRs: ').strip()=='PUBLISH','Cancelled before remote writes')
    states=json.loads((folder/'publication.json').read_text()) if (folder/'publication.json').is_file() else {}
    for role in ['private','public']:
        mapping=p['sha256'][role];public_publish_allowed(role,mapping)
        full,base=ensure_repo(role);clone=folder/'checkouts'/role;branch='publication/'+p['plan_id']
        if not clone.exists():
            clone.parent.mkdir(exist_ok=True)
            command(['git','clone','--no-tags','--single-branch','--branch',base,'https://github.com/'+full+'.git',str(clone)],inherit=True)
        require(not clone.is_symlink(),'Unsafe publication clone')
        remote=command(['git','remote','get-url','origin'],cwd=clone).stdout.strip()
        require(remote=='https://github.com/'+full+'.git','Unexpected clone remote')
        command(['git','fetch','origin',base],cwd=clone)
        if role=='public':
            existing=set(command(['git','ls-files'],cwd=clone).stdout.splitlines())
            require(existing<=set(PUBLIC_FILES),'Existing public repository has files outside the showcase allowlist. Review them before publishing; no deletion is automatic.')
        current=command(['git','branch','--show-current'],cwd=clone).stdout.strip()
        status=command(['git','status','--porcelain'],cwd=clone).stdout
        if current!=branch:
            require(not status,'Publication clone contains edits. Preserve them; no switch performed.')
            exists=command(['git','show-ref','--verify','--quiet','refs/heads/'+branch],cwd=clone,check=False).returncode==0
            command(['git','switch',branch] if exists else ['git','switch','-c',branch,'origin/'+base],cwd=clone)
        # All private snapshots live under a unique release directory. Never erase prior snapshots.
        prefix=Path('snapshots')/p['plan_id'] if role=='private' else Path('.')
        destinations={str(prefix/n):h for n,h in mapping.items()}
        changed=set()
        for a in [['diff','--name-only'],['diff','--cached','--name-only'],['ls-files','--others','--exclude-standard']]:
            changed.update(command(['git',*a],cwd=clone).stdout.splitlines())
        require(changed<=set(destinations),'Unrelated files in publication clone; refusing to mix changes')
        for n in mapping:
            target=clone/prefix/n
            require(not target.is_symlink() and not any(q.is_symlink() for q in target.parents),'Symlink in publication destination')
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(folder/(role+'_source')/n,target)
        command(['git','config','--local','user.name','Alvaro Mendizabal'],cwd=clone)
        command(['git','config','--local','user.email','108156083+alvaromendizabal@users.noreply.github.com'],cwd=clone)
        command(['git','add','--force','--',str(prefix)],cwd=clone) if role=='private' else command(['git','add','--',*sorted(destinations)],cwd=clone)
        staged_names=set(command(['git','diff','--cached','--name-only'],cwd=clone).stdout.splitlines())
        require(staged_names<=set(destinations),'Unexpected staged paths; no commit made')
        whitespace=command(['git','diff','--cached','--check'],cwd=clone,check=False)
        if role=='public':require(whitespace.returncode==0,'Public text has whitespace errors; review before commit')
        elif whitespace.returncode:print('Private archival source retains existing whitespace; this is not a style-gate pass.')
        if command(['git','diff','--cached','--quiet'],cwd=clone,check=False).returncode:
            command(['git','commit','-m',f'Publish reviewed {role} research snapshot {p["plan_id"]}'],cwd=clone,inherit=True)
        commit=command(['git','rev-parse','HEAD'],cwd=clone).stdout.strip()
        require(not command(['git','status','--porcelain'],cwd=clone).stdout,'Clone not clean after commit')
        # Recheck visibility immediately before network transfer.
        require(gh_json('api','repos/'+full)['private'] is TARGETS[role][1],'Visibility changed; push blocked')
        command(['git','push','--set-upstream','origin',branch],cwd=clone,inherit=True)
        require(command(['git','ls-remote','origin','refs/heads/'+branch],cwd=clone).stdout.split()[0]==commit,'Remote branch SHA differs')
        prs=gh_json('pr','list','--repo',full,'--head',branch,'--state','all','--json','url,state,number,headRefOid')
        if not prs:
            command(['gh','pr','create','--repo',full,'--base',base,'--head',branch,'--title',f'Reviewed {role} research snapshot',
                '--body','User-run reviewed publication. No science was executed by publication. Source snapshot exclusions and validation status are explicit.'],inherit=True)
            prs=gh_json('pr','list','--repo',full,'--head',branch,'--state','all','--json','url,state,number,headRefOid')
        require(len(prs)==1 and prs[0]['headRefOid']==commit and prs[0]['state'] in ['OPEN','MERGED'],'PR head mismatch, closed-unmerged, or ambiguous PR')
        states[role]={'repository':full,'private':TARGETS[role][1],'base':base,'branch':branch,'commit':commit,'pr':prs[0],
            'clone':str(clone),'published_files':destinations,'merged':prs[0]['state']=='MERGED'}
        atomic(folder/'publication.json',states);print('PR:',prs[0]['url'])
    print('PUSHED_AND_PRS_OPEN — review the two PR links. Nothing was force-pushed and no PR was merged automatically.')
    print('After PR review, run: python github_publish.py merge')

def merge():
    folder,p=load_plan();auth();state=json.loads((folder/'publication.json').read_text())
    require(set(state)==set(TARGETS),'Both publication branches must exist first')
    require(input('After reviewing BOTH pull requests, type MERGE to merge these exact heads: ').strip()=='MERGE','Merge cancelled')
    for role,s in state.items():
        require(s['repository']==OWNER+'/'+TARGETS[role][0] and gh_json('api','repos/'+s['repository'])['private'] is TARGETS[role][1],'Unexpected destination or visibility')
        pr=gh_json('pr','view',str(s['pr']['number']),'--repo',s['repository'],'--json','state,headRefOid,mergeCommit,statusCheckRollup,url')
        require(pr['headRefOid']==s['commit'],'PR changed after plan; review again, no merge')
        if pr['state']!='MERGED':
            require(pr['state']=='OPEN','PR not open')
            for check in pr.get('statusCheckRollup') or []:
                status=check.get('status');conclusion=check.get('conclusion');legacy=check.get('state')
                require((status=='COMPLETED' and conclusion in ['SUCCESS','NEUTRAL','SKIPPED']) or legacy=='SUCCESS','A reported check is failing or pending; no override')
            s['checks_at_merge']=pr.get('statusCheckRollup') or []
            s['ci_status']='reported_checks_completed' if s['checks_at_merge'] else 'NO_REPORTED_CHECKS_NOT_A_CI_PASS'
            atomic(folder/'publication.json',state)
            # Empty checks are not reported as a CI pass; GitHub still enforces branch protections.
            command(['gh','pr','merge',str(s['pr']['number']),'--repo',s['repository'],'--merge','--match-head-commit',s['commit']],inherit=True)
        pr=gh_json('pr','view',str(s['pr']['number']),'--repo',s['repository'],'--json','state,mergeCommit,url')
        require(pr['state']=='MERGED','GitHub did not confirm merge')
        clone=Path(s['clone'])
        require(not command(['git','status','--porcelain'],cwd=clone).stdout,'Publication clone has edits; no switch or merge performed')
        command(['git','fetch','origin',s['base']],cwd=clone)
        command(['git','switch',s['base']],cwd=clone);command(['git','merge','--ff-only','origin/'+s['base']],cwd=clone)
        head=command(['git','rev-parse','HEAD'],cwd=clone).stdout.strip()
        require(head==command(['git','rev-parse','origin/'+s['base']],cwd=clone).stdout.strip(),'Publication clone not synchronized')
        for n,h in s['published_files'].items():require(digest(clone/n)==h,'Merged file bytes differ: '+n)
        s.update(merged=True,merge_commit=pr['mergeCommit']['oid'],synced_head=head)
        atomic(folder/'publication.json',state)
    print('MERGED_AND_PUBLICATION_CLONES_VERIFIED. Original AWS research checkout remains unchanged.')
    out=Path.home()/'march_publication/publication_return.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:z.write(folder/'publication.json','publication.json')
    print('Return receipt:',out)

def main():
    from publication.review_support import lock,require_test_receipt,show_inspection,diagnostic,UPDATE_ID
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['auth','inspect','plan','publish','merge','status'])
    args=parser.parse_args()
    try:
        with lock(Path.home()):
            print('PUBLICATION_VERSION:',UPDATE_ID)
            if args.action=='inspect':
                show_inspection(Path.home());diagnostic(Path.home(),{'action':'inspect','status':'METADATA_ONLY'});return
            if args.action=='status':
                folder,record=load_plan();state=folder/'publication.json'
                print(state.read_text() if state.is_file() else 'PLAN_READY_NOT_PUBLISHED');return
            if args.action in {'plan','publish','merge'}:require_test_receipt(ROOT,Path.home())
            globals()[args.action]()
    except Exception as error:
        from publication.review_support import clean
        print('STOP:',clean(error))
        try:diagnostic(Path.home(),{'action':args.action,'error':clean(error),'type':type(error).__name__})
        except Exception:print('Diagnostic could not be written; preserve this terminal message.')
        print('Original research checkout, raw data and model caches are unchanged. No blind retry.')
        raise SystemExit(1)

if __name__=='__main__':main()
