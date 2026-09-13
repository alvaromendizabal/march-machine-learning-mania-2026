"""Exercise real local Git commits/pushes/merges against two temporary bare repos.

GitHub API/PR operations are simulated. No network or user accounts are accessed.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import github_publish as g
from test_publication_tools_environment import fixture


class LocalBackend:
    def __init__(self, home):
        self.home = home; self.meta = {}; self.bare = {}; self.pr = {}; self.calls=[]
        self.env = os.environ.copy()
        self.env.update(HOME=str(home), GIT_CONFIG_NOSYSTEM='1',GIT_TERMINAL_PROMPT='0',GIT_ALLOW_PROTOCOL='file')
        self.env.pop('GIT_CONFIG_GLOBAL',None)
        for key in list(self.env):
            if key.startswith('GIT_CONFIG_') and key != 'GIT_CONFIG_NOSYSTEM': self.env.pop(key)
        self.work=home/'backend';self.work.mkdir()

    def git(self, args, cwd=None, check=True):
        cmd=['git','-c','protocol.file.allow=always','-c','user.name=Local Test',
             '-c','user.email=local-test@example.invalid']
        # Route transport to temporary local repositories; keep metadata reads
        # faithful to the canonical HTTPS origin saved by clone.
        if args and args[0] in {'clone','fetch','push','ls-remote'}:
            for full,bare in self.bare.items():
                cmd += ['-c',f'url.{bare}.insteadOf=https://github.com/{full}.git']
        p=subprocess.run(cmd+list(args),cwd=cwd,env=self.env,text=True,capture_output=True,timeout=20)
        if check and p.returncode: raise AssertionError('Local git failure: '+repr(args)+' '+p.stderr)
        return p

    def create_repo(self, full, private):
        bare=self.work/(full.split('/')[-1]+'.git');self.bare[full]=bare
        self.git(['init','--bare','--initial-branch=main',str(bare)])
        seed=self.work/(full.split('/')[-1]+'-seed')
        self.git(['clone',str(bare),str(seed)])
        (seed/'README.md').write_text('# Local simulated repository\n')
        self.git(['add','README.md'],seed);self.git(['commit','-m','Initialize'],seed)
        self.git(['push','origin','main'],seed)
        self.meta[full]={'full_name':full,'owner':{'login':g.OWNER},'private':private,'archived':False,'default_branch':'main'}

    @staticmethod
    def result(obj=None):
        return subprocess.CompletedProcess([],0,'' if obj is None else json.dumps(obj),'')

    def command(self,args,cwd=None,timeout=120,inherit=False,check=True):
        self.calls.append(list(args))
        if args[0]=='git':
            for item in args:
                if item.startswith('https://'):
                    assert item in {'https://github.com/'+f+'.git' for f in self.bare}, item
            return self.git(args[1:],cwd,check)
        assert args[0]=='gh', args
        if args[1:3]==['auth','status']:return self.result()
        if args[1]=='api':
            if args[-1]=='user':return self.result({'login':g.OWNER})
            if args[-1].startswith('user/repos?'):return self.result([list(self.meta.values())])
            if args[-1].startswith('repos/'):return self.result(self.meta[args[-1][6:]])
        if args[1:3]==['repo','create']:
            self.create_repo(args[3],'--private' in args);return self.result()
        if args[1]=='pr':
            kind=args[2];full=args[args.index('--repo')+1]
            if kind=='list':return self.result([self.pr[full]] if full in self.pr else [])
            if kind=='create':
                branch=args[args.index('--head')+1]
                sha=self.git(['--git-dir',str(self.bare[full]),'rev-parse',branch]).stdout.strip()
                self.pr[full]={'url':'https://github.com/'+full+'/pull/1','state':'OPEN','number':1,
                    'headRefOid':sha,'mergeCommit':None,'statusCheckRollup':[], 'branch':branch}
                return self.result()
            if kind=='view':return self.result(self.pr[full])
            if kind=='merge':
                p=self.pr[full];assert args[args.index('--match-head-commit')+1]==p['headRefOid']
                dest=self.work/(full.split('/')[-1]+'-merge')
                self.git(['clone',str(self.bare[full]),str(dest)])
                self.git(['merge','--no-ff','origin/'+p['branch'],'-m','Reviewed local merge'],dest)
                sha=self.git(['rev-parse','HEAD'],dest).stdout.strip()
                self.git(['push','origin','main'],dest)
                p.update(state='MERGED',mergeCommit={'oid':sha});return self.result()
        raise AssertionError('Unexpected simulated command: '+repr(args))


@unittest.skipUnless(shutil.which('git'), 'Local Git needed for publication integration tests')
class LocalGitPublicationTests(unittest.TestCase):
    def execute(self,repeat):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);root,env=fixture(h)
            (root/'private_runs').mkdir();(root/'private_runs/model.json').write_text('{}')
            backend=LocalBackend(h)
            def confirm(prompt):return 'PUBLISH' if 'PUBLISH' in prompt else 'MERGE'
            with patch.object(g.Path,'home',return_value=h),patch.object(g,'command',side_effect=backend.command),\
                 patch.object(g.shutil,'which',return_value='/local/fake-gh'),\
                 patch.dict(g.os.environ,{'GH_TOKEN':'','GITHUB_TOKEN':''}),patch('builtins.input',side_effect=confirm):
                g.plan();folder,plan=g.load_plan();g.publish();g.merge()
                if repeat:g.publish();g.merge()
                state=json.loads((folder/'publication.json').read_text())
            self.assertEqual(set(state),{'private','public'})
            for role,s in state.items():
                self.assertTrue(s['merged'])
                for name,digest in s['published_files'].items():
                    self.assertEqual(g.digest(Path(s['clone'])/name),digest)
                files=backend.git(['--git-dir',str(backend.bare[s['repository']]),'ls-tree','-r','--name-only','main']).stdout.splitlines()
                self.assertFalse(any('/.tools/' in p or '/private_runs/' in p for p in files))
                if role=='public':self.assertEqual(set(files),set(g.PUBLIC_FILES))
            self.assertTrue((h/'march_publication/publication_return.zip').is_file())
            self.assertTrue((env/'bin/python').is_symlink())
            self.assertFalse(any('--admin' in a or '--force' in a and a[:2]==['git','push'] for a in backend.calls))
            self.assertFalse(any(a[:3]==['gh','auth','login'] for a in backend.calls))

    def test_local_private_public_commit_push_merge_and_hashes(self):self.execute(False)
    def test_repeated_publication_reuses_reviewed_branch(self):self.execute(True)

if __name__=='__main__':unittest.main()
