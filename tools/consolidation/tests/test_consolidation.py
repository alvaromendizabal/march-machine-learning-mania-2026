"""Publication-only regression tests. No network or scientific project imports."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('consolidate_march',ROOT/'consolidate_march.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

def git(root,*args,input_data=None):
    env=os.environ.copy();env.update(GIT_AUTHOR_NAME='Fixture',GIT_COMMITTER_NAME='Fixture',GIT_AUTHOR_EMAIL='fixture@example.invalid',GIT_COMMITTER_EMAIL='fixture@example.invalid',GIT_TERMINAL_PROMPT='0')
    p=subprocess.run(['git',*args],cwd=root,input=input_data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,check=True)
    return p.stdout.decode().strip()

def sample():
    content={'private':{'snapshots/s/research/kit/code.py':b'x = 1\n', 'snapshots/s/README.md':b'# Snapshot\n', 'snapshots/s/PRIVATE_SNAPSHOT.json':b'{}\n'},'public':{'README.md':b'# View\n','data/validation_metrics.csv':b'round,population,season,arm,brier,setting\r\n02,M,2019,Reference,0.2,exploratory\r\n'}}
    receipt={role:{'repository':name,'merged':True,'merge_commit':'a'*40,'published_files':{p:c.sha(b) for p,b in content[role].items()}} for role,name in zip(['private','public'],c.EXTRAS)}
    return content,receipt

class PureTests(unittest.TestCase):
    def test_only_original_target(self):self.assertEqual(c.TARGET,'alvaromendizabal/march-machine-learning-mania-2026')
    def test_original_not_deletion_target(self):self.assertNotIn(c.TARGET,c.EXTRAS)
    def test_two_deletion_targets(self):self.assertEqual(len(c.EXTRAS),2)
    def test_no_repository_creation_command(self):
        s=(ROOT/'consolidate_march.py').read_text()
        self.assertNotIn("'repo','create'",s);self.assertNotIn("'user/repos',method='POST'",s)
    def test_no_force_push_or_admin_bypass(self):
        s=(ROOT/'consolidate_march.py').read_text();self.assertNotIn("'--force'",s);self.assertNotIn("'--admin'",s)
    def test_no_auth_login(self):self.assertNotIn("'auth','login'",(ROOT/'consolidate_march.py').read_text())
    def test_no_scientific_imports(self):
        import ast
        tree=ast.parse((ROOT/'consolidate_march.py').read_text())
        names=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):names += [a.name for a in n.names]
            elif isinstance(n,ast.ImportFrom):names.append(n.module or '')
        self.assertFalse(any(x.startswith(('sklearn','numpy','pandas','torch','march_mania')) for x in names))
    def test_receipt_identity(self):
        r=c.receipt_load();self.assertEqual(len(r['private']['published_files']),881);self.assertEqual(len(r['public']['published_files']),10)
    def test_receipt_tampering_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'receipt.json';p.write_text('{}')
            with self.assertRaises(RuntimeError):c.receipt_load(p)
    def test_mapping_every_file(self):
        raw,r=sample();files,m=c.build_payload(raw,r);self.assertEqual(len(files),5);self.assertEqual(len(m),5)
    def test_exact_crlf_preserved(self):
        raw,r=sample();files,m=c.build_payload(raw,r)
        self.assertEqual(files['research/publication_archive/data/validation_metrics.csv'],raw['public']['data/validation_metrics.csv'])
    def test_actual_tampering_refused(self):
        raw,r=sample();raw['private']['snapshots/s/research/kit/code.py']=b'x=2'
        with self.assertRaises(RuntimeError):c.build_payload(raw,r)
    def test_traversal_refused(self):
        for p in ['../x','/root/x','a/../b','a\\b','a\nx','.git/config']:
            with self.assertRaises(RuntimeError):c.safe_relative(p)
    def test_unexpected_snapshot_root(self):
        with self.assertRaises(RuntimeError):c.mapped_path('private','snapshots/s/credentials')
    def test_target_collision_refused(self):
        raw,r=sample();p='snapshots/s2/research/kit/code.py';raw['private'][p]=b'x=1';r['private']['published_files'][p]=c.sha(b'x=1')
        with self.assertRaises(RuntimeError):c.build_payload(raw,r)
    def test_secret_refused(self):
        with self.assertRaises(RuntimeError):c.check_source_bytes('x.py',('token="ghp_'+'A'*40+'"').encode())
    def test_lfs_refused(self):
        with self.assertRaises(RuntimeError):c.check_source_bytes('x.txt',b'version https://git-lfs.github.com/spec/v1\n')
    def test_outputs_not_mislabeled_as_source(self):
        b=json.dumps({'cells':[{'cell_type':'code','outputs':[{'output_type':'stream','text':'x'}]}]}).encode()
        with self.assertRaises(RuntimeError):c.check_source_bytes('x.ipynb',b)
    def test_safe_source_notebook(self):
        b=json.dumps({'cells':[{'cell_type':'code','outputs':[],'source':['x=1']}]}).encode()
        self.assertEqual(c.check_source_bytes('x.ipynb',b),b)
    def test_reports_not_fabricated_executed(self):
        n=json.loads(c.notebook_bytes());codes=[x for x in n['cells'] if x['cell_type']=='code']
        self.assertEqual(len(codes),3);self.assertTrue(all(x['outputs']==[] and x['execution_count'] is None for x in codes))
    def test_atomic_preserves_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'original';f.write_text('keep');p=Path(d)/'p';p.symlink_to(f)
            with self.assertRaises(RuntimeError):c.atomic(p,b'change')
            self.assertEqual(f.read_text(),'keep')
    def test_git_blob_computation(self):self.assertEqual(c.git_blob_sha(b'test\n'),'9daeafb9864cf43055ae93beb0afd6c7d144bfa4')
    def test_headline_retains_original(self):
        raw,r=sample();files,m=c.build_payload(raw,r);docs=c.front_matter(m,r)
        self.assertIn(c.TARGET.encode(),docs['README.md']);self.assertIn(b'not an achieved',docs['README.md'])

class LocalGitTests(unittest.TestCase):
    def fixture(self,d):
        home=Path(d);r=c.Runner(home=home)
        base=home/'base';base.mkdir();git(base,'init','-b','main')
        (base/'README.md').write_text('old\n');(base/'original.py').write_text('preserve\n')
        git(base,'add','.');git(base,'commit','-m','base');head=git(base,'rev-parse','HEAD')
        bare=home/'origin.git';git(home,'clone','--bare',str(base),str(bare))
        clone=home/'clone';git(home,'clone',str(bare),str(clone))
        r.state.update(target_base=head,stage=str(home/'stage'),clone=str(clone))
        return r,clone,bare
    def test_real_local_commit_push_merge_and_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            r,clone,bare=self.fixture(d);raw,rc=sample();files,m=c.build_payload(raw,rc)
            files['README.md']=b'# Professional landing\n'
            for p,b in files.items():c.atomic(Path(r.state['stage'])/p,b)
            r.state['payload_hashes']={p:c.sha(b) for p,b in files.items()}
            tree=r.stage_index(clone)
            self.assertEqual(len(tree),40)
            commit=git(clone,'commit-tree',tree,'-p',r.state['target_base'],input_data=b'consolidate\n')
            r.verify_objects(clone,commit)
            git(clone,'push','origin',commit+':refs/heads/consolidate')
            git(clone,'fetch','origin','consolidate');git(clone,'checkout','main')
            git(clone,'merge','--no-ff',commit,'-m','merge');git(clone,'push','origin','main')
            git(clone,'fetch','origin','main');merged=git(clone,'rev-parse','FETCH_HEAD');r.verify_objects(clone,merged)
            self.assertEqual(git(clone,'show',merged+':original.py'),'preserve')
            for p,b in files.items():
                got=subprocess.check_output(['git','show',merged+':'+p],cwd=clone)
                self.assertEqual(got,b)
            # Independently backed up history remains readable.
            mirror=Path(d)/'backup.git';git(Path(d),'clone','--mirror','--no-hardlinks',str(clone),str(mirror))
            bundle=Path(d)/'all.bundle';git(mirror,'bundle','create',str(bundle),'--all');git(mirror,'bundle','verify',str(bundle))
    def test_changed_staging_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r,clone,bare=self.fixture(d);r.state['payload_hashes']={'research/a.py':c.sha(b'a')};c.atomic(Path(r.state['stage'])/'research/a.py',b'b')
            with self.assertRaises(RuntimeError):r.stage_index(clone)
    def test_symlink_git_archive_refused(self):
        with tempfile.TemporaryDirectory() as d:
            r,clone,bare=self.fixture(d);p=Path(d)/'bad.tar'
            import tarfile
            with tarfile.open(p,'w') as t:
                e=tarfile.TarInfo('link');e.type=tarfile.SYMTYPE;e.linkname='../secret';t.addfile(e)
            with self.assertRaises(RuntimeError):c.read_archive(p)
    def test_cleanup_before_merge_impossible(self):
        with tempfile.TemporaryDirectory() as d:
            r=c.Runner(home=Path(d))
            with patch.object(r,'auth',return_value={}):
                with self.assertRaisesRegex(RuntimeError,'forbidden'):r.cleanup()
    def test_lock_rejects_concurrent_process(self):
        with tempfile.TemporaryDirectory() as d:
            a=c.Runner(home=Path(d));b=c.Runner(home=Path(d))
            with a.locked():
                with self.assertRaises(RuntimeError):
                    with b.locked():pass
    def test_command_timeout_terminates_child(self):
        with tempfile.TemporaryDirectory() as d:
            r=c.Runner(home=Path(d))
            with self.assertRaises(TimeoutError):r.cmd([sys.executable,'-c','import time; time.sleep(4)'],timeout=.05)
    def test_diagnostics_archive(self):
        with tempfile.TemporaryDirectory() as d:
            r=c.Runner(home=Path(d));r.save(status='PLAN_READY')
            with zipfile.ZipFile(r.work/'consolidation_return.zip') as z:self.assertIn('state.json',z.namelist())

    def test_retire_only_known_legacy_publisher(self):
        with tempfile.TemporaryDirectory() as d:
            r=c.Runner(home=Path(d));old=Path(d)/'march_next_steps/github_publish.py';old.parent.mkdir();old.write_bytes(b'old publisher\n')
            key='snapshots/s/research/march_next_steps/github_publish.py'
            r.receipt['private']['published_files'][key]=c.sha(old.read_bytes())
            # Fixture removes the real receipt's duplicate suffix, retaining one accepted checksum.
            r.receipt['private']['published_files']={k:v for k,v in r.receipt['private']['published_files'].items() if not k.endswith('/research/march_next_steps/github_publish.py') or k==key}
            result=r.retire_legacy_publisher();self.assertEqual(result['status'],'RETIRED_AFTER_VERIFIED_MIGRATION')
            self.assertEqual(Path(result['backup']).read_bytes(),b'old publisher\n')
            self.assertIn(b'two-repository publisher is retired',old.read_bytes())
            self.assertEqual(r.retire_legacy_publisher()['status'],'ALREADY_RETIRED')
    def test_unknown_legacy_edit_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            r=c.Runner(home=Path(d));old=Path(d)/'march_next_steps/github_publish.py';old.parent.mkdir();old.write_bytes(b'my private local edit\n')
            result=r.retire_legacy_publisher();self.assertEqual(result['status'],'LOCAL_EDIT_PRESERVED_NOT_RETIRED');self.assertEqual(old.read_bytes(),b'my private local edit\n')

class CITests(unittest.TestCase):
    def run_check(self,checks,state='pending',statuses=None):
        d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup);r=c.Runner(home=Path(d.name))
        def api(path,**kw):
            return {'check_runs':checks} if 'check-runs?' in path else {'state':state,'statuses':statuses or []}
        with patch.object(r,'api',side_effect=api):return r.check_ci('a'*40)
    def records(self):return [{'id':i,'name':n,'head_sha':'a'*40,'status':'completed','conclusion':'success'} for i,n in enumerate(c.REQUIRED_CHECKS)]
    def test_zero_checks_not_success(self):self.assertFalse(self.run_check([]))
    def test_two_named_checks_required(self):self.assertFalse(self.run_check(self.records()[:1]))
    def test_exact_head_required(self):
        r=self.records();r[0]['head_sha']='b'*40;self.assertFalse(self.run_check(r))
    def test_pending_not_mergeable(self):
        r=self.records();r[0]['status']='in_progress';r[0]['conclusion']=None;self.assertFalse(self.run_check(r))
    def test_failure_refused(self):
        r=self.records();r[0]['conclusion']='failure'
        with self.assertRaises(RuntimeError):self.run_check(r)
    def test_successful_existing_ci(self):self.assertTrue(self.run_check(self.records(),state='success'))
    def test_other_failed_status_not_bypassed(self):
        with self.assertRaises(RuntimeError):self.run_check(self.records(),statuses=[{'state':'failure'}])
    def test_skipped_required_job_not_pass(self):
        r=self.records();r[0]['conclusion']='skipped';self.assertFalse(self.run_check(r))


class SimulatedGitHubRunner(c.Runner):
    """Actual Git transport uses local bare remotes; ONLY GitHub API is simulated."""
    def __init__(self,home,remotes):
        super().__init__(home=home);self.remotes=remotes;self.pr=None;self.deleted=set();self.ci_ready=True;self.api_calls=[]
        fake=Path(home)/'fake-gh';fake.write_text('#!/bin/sh\nexit 99\n');fake.chmod(0o700);self.gh=str(fake)
    def cmd(self,args,**kw):
        args=list(args)
        if args[:3]==[self.gh,'repo','delete']:
            name=args[3]
            assert name in c.EXTRAS and name!=c.TARGET
            self.deleted.add(name);return 0,b'',''
        if args[0]=='git':
            saved=args[:];remote_name=None
            for i,v in enumerate(args):
                if isinstance(v,str) and v.startswith('https://github.com/') and v.endswith('.git'):
                    remote_name=v[len('https://github.com/'):-4]
                    args[i]=str(self.remotes[remote_name])
            if args[1] in {'push','fetch'} and args[2]=='origin':args[2]=str(self.remotes[c.TARGET])
            result=super().cmd(args,**kw)
            if args[1]=='clone' and remote_name is not None:
                clone=Path(args[-1]);git(clone,'remote','set-url','origin','https://github.com/'+remote_name+'.git')
            return result
        return super().cmd(args,**kw)
    def api(self,path,method='GET',payload=None):
        self.api_calls.append((method,path))
        if path=='user':return {'login':c.OWNER}
        if path.startswith('user/repos?'):
            return [{'full_name':n,'owner':{'login':c.OWNER}} for n in self.remotes if n not in self.deleted]
        for name,remote in self.remotes.items():
            prefix='repos/'+name
            if path==prefix:
                return {'id':c.TARGET_ID if name==c.TARGET else (1367942723 if name.endswith('research') else 1367942724), 'full_name':name,'owner':{'login':c.OWNER},'private':name.endswith('research'),'default_branch':'main','permissions':{'push':True,'admin':True}}
            if path.startswith(prefix+'/git/ref/heads/'):
                branch=path[len(prefix+'/git/ref/heads/'):]
                return {'object':{'sha':git(remote,'rev-parse','refs/heads/'+branch)}}
            if path.startswith(prefix+'/commits/') and '/check-runs?' in path:
                head=path.split('/commits/')[1].split('/')[0]
                return {'check_runs':[{'id':i,'name':n,'head_sha':head,'status':'completed' if self.ci_ready else 'in_progress','conclusion':'success' if self.ci_ready else None} for i,n in enumerate(c.REQUIRED_CHECKS)]}
            if path.startswith(prefix+'/commits/') and '/status?' in path:return {'state':'success','statuses':[]}
            if path.startswith(prefix+'/pulls?'):
                if name==c.TARGET:return [self.pr] if self.pr else []
                return []
            if path.startswith(prefix+'/issues?') or path.startswith(prefix+'/releases?'):return []
            if path==prefix+'/pulls' and method=='POST':
                self.pr={'number':24,'html_url':'https://github.com/'+name+'/pull/24','head':{'sha':self.state['commit']},'state':'open','merged':False}
                return self.pr
            if path==prefix+'/pulls/24':return self.pr
            if path==prefix+'/pulls/24/merge' and method=='PUT':
                assert payload['sha']==self.state['commit']
                mergeclone=self.home/'api-merge'
                git(self.home,'clone',str(remote),str(mergeclone))
                git(mergeclone,'fetch','origin',self.state['branch'])
                git(mergeclone,'merge','--no-ff',payload['sha'],'-m','API fixture merge')
                git(mergeclone,'push','origin','main')
                oid=git(mergeclone,'rev-parse','HEAD')
                self.pr.update(merged=True,state='closed',merge_commit_sha=oid)
                return {'merged':True,'sha':oid}
        raise AssertionError('Unexpected simulated API request: '+method+' '+path)

class CompletePublicationFixture(unittest.TestCase):
    def prepare(self,root):
        data,receipt=sample();remotes={}
        origin=root/'original';origin.mkdir();git(origin,'init','-b','main')
        (origin/'README.md').write_text('# Existing release\n');(origin/'original.py').write_text('original stays\n');git(origin,'add','.');git(origin,'commit','-m','original')
        remote=root/'original.git';git(root,'clone','--bare',str(origin),str(remote));remotes[c.TARGET]=remote
        for role,name in zip(['private','public'],c.EXTRAS):
            relative=Path('march_publication/plans/fixture/checkouts')/role
            clone=root/relative;clone.mkdir(parents=True);git(clone,'init','-b','main')
            for path,raw in data[role].items():
                f=clone/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(raw)
            git(clone,'add','.');git(clone,'commit','-m','published source')
            oid=git(clone,'rev-parse','HEAD');receipt[role]['merge_commit']=oid;receipt[role]['clone']=str(Path('/home/sagemaker-user')/relative)
            extra=root/(role+'.git');git(root,'clone','--bare',str(clone),str(extra));remotes[name]=extra
            git(clone,'remote','add','origin','https://github.com/'+name+'.git')
        r=SimulatedGitHubRunner(root,remotes);r.receipt=receipt
        return r,remotes
    def test_plan_publish_finish_cleanup_full_sequence(self):
        with tempfile.TemporaryDirectory() as d:
            r,remotes=self.prepare(Path(d));r.make_plan();r.publish()
            self.assertFalse(r.deleted);self.assertTrue(r.finish(wait=0))
            self.assertFalse(r.deleted);self.assertTrue(r.cleanup())
            self.assertEqual(r.deleted,set(c.EXTRAS));self.assertNotIn(c.TARGET,r.deleted)
            self.assertEqual(r.state['status'],'CONSOLIDATED_AND_EXTRA_REPOSITORIES_REMOVED')
            self.assertEqual(git(Path(r.state['clone']),'status','--porcelain'),'')
            self.assertEqual(git(Path(r.state['clone']),'rev-parse','HEAD'),r.state['verified_main'])
            self.assertEqual(git(remotes[c.TARGET],'show','main:original.py'),'original stays')
            # Idempotent: no new PR, commit, or repository creation on repeat.
            commit=r.state['commit'];r.make_plan();r.publish();r.finish(wait=0);r.cleanup();self.assertEqual(r.state['commit'],commit)
            self.assertFalse(any(p=='user/repos' and m=='POST' for m,p in r.api_calls))
    def test_pending_ci_never_deletes_or_merges(self):
        with tempfile.TemporaryDirectory() as d:
            r,remotes=self.prepare(Path(d));r.make_plan();r.publish();r.ci_ready=False
            self.assertFalse(r.finish(wait=0));self.assertFalse(r.pr['merged']);self.assertFalse(r.deleted)
            with self.assertRaises(RuntimeError):r.cleanup()
    def test_changed_source_head_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            r,remotes=self.prepare(Path(d));r.make_plan();r.publish();r.finish(wait=0)
            extra=remotes[c.EXTRAS[0]];w=Path(d)/'changed';git(Path(d),'clone',str(extra),str(w));(w/'new.py').write_text('new work\n');git(w,'add','.');git(w,'commit','-m','new');git(w,'push','origin','main')
            with self.assertRaisesRegex(RuntimeError,'new main work'):r.cleanup()
            self.assertFalse(r.deleted)
    def test_changed_backup_forbids_deletion(self):
        with tempfile.TemporaryDirectory() as d:
            r,remotes=self.prepare(Path(d));r.make_plan();r.publish();r.finish(wait=0)
            Path(r.state['backups']['private']['bundle']).write_bytes(b'corrupt')
            with self.assertRaisesRegex(RuntimeError,'backup missing or changed'):r.cleanup()
            self.assertFalse(r.deleted)


_EVENT_PATCH = None
def setUpModule():
    global _EVENT_PATCH
    _EVENT_PATCH = patch.object(c, 'event', lambda *args, **kwargs: None)
    _EVENT_PATCH.start()
def tearDownModule():
    _EVENT_PATCH.stop()

if __name__ == '__main__':
    unittest.main(verbosity=2)
