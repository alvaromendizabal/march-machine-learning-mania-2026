"""Regression tests for the exact .tools blockers in the supplied terminal log.

Temporary local directories only. No AWS/GitHub access or scientific execution.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import github_publish as g
from publication import stage_private as s
from publication import review_support as r

ROOT_NAME = 'march-machine-learning-mania-2026'


def fixture(home):
    root = home / ROOT_NAME
    env = root / '.tools'
    (env / 'bin').mkdir(parents=True)
    (env / 'lib/python3.12/site-packages').mkdir(parents=True)
    (env / 'pyvenv.cfg').write_text('home = /usr/bin\ninclude-system-site-packages = false\n')
    (env / 'lib/python3.12/site-packages/vendor.py').write_text('RUNTIME_ONLY = True\n')
    (env / 'bin/python').symlink_to('/usr/bin/python3')
    (env / 'bin/python3').symlink_to('python')
    (env / 'bin/python3.12').symlink_to('python')
    (env / 'lib64').symlink_to('lib', target_is_directory=True)
    (root / 'src').mkdir()
    (root / 'src/model.py').write_text('VALUE = 1\n')
    (root / 'pyproject.toml').write_text('[project]\nname="example"\n')
    (root / 'uv.lock').write_text('version = 1\n')
    return root, env


def tree_bytes(root):
    values = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            p = Path(directory) / name
            rel = str(p.relative_to(root))
            if p.is_symlink():
                values[rel] = ('link', os.readlink(p))
            elif p.is_file():
                values[rel] = ('file', p.read_bytes())
            else:
                values[rel] = ('dir', None)
    return values


class ToolsEnvironmentTests(unittest.TestCase):
    def test_exact_four_reported_links_no_longer_block(self):
        with tempfile.TemporaryDirectory() as d:
            h = Path(d); root, env = fixture(h)
            out = s.stage(h, h/'snapshot')
            m = json.loads((out/'PRIVATE_SNAPSHOT.json').read_text())
            self.assertEqual(m['blocked'], [])
            self.assertEqual(m['status'], 'SOURCE_SNAPSHOT_READY_FOR_PRIVATE_REVIEW')
            self.assertEqual(m['exclusion_counts']['excluded_tool_environments'], 1)

    def test_original_environment_and_source_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            h = Path(d); root, env = fixture(h); old = tree_bytes(root)
            s.stage(h,h/'snapshot')
            self.assertEqual(tree_bytes(root), old)

    def test_no_runtime_site_packages_in_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            h = Path(d); fixture(h); out = s.stage(h,h/'snapshot')
            m = json.loads((out/'PRIVATE_SNAPSHOT.json').read_text())
            self.assertEqual(len(m['files']), 3)
            self.assertFalse((out/'research'/ROOT_NAME/'.tools').exists())

    def test_generated_environment_not_read_or_traversed(self):
        original = Path.read_bytes
        with tempfile.TemporaryDirectory() as d:
            h=Path(d); fixture(h)
            def guarded(p):
                if '.tools' in p.parts:
                    raise AssertionError('Environment content must not be read')
                return original(p)
            with patch.object(Path,'read_bytes',guarded):
                out=s.stage(h,h/'snapshot')
            self.assertEqual(json.loads((out/'PRIVATE_SNAPSHOT.json').read_text())['blocked'], [])

    def test_tools_directory_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);root=h/ROOT_NAME;root.mkdir();(root/'a.py').write_text('x=1\n')
            target=h/'outside';target.mkdir();(target/'a.py').write_text('PRIVATE=1\n')
            (root/'.tools').symlink_to(target,target_is_directory=True)
            out=s.stage(h,h/'snapshot')
            self.assertEqual(json.loads((out/'PRIVATE_SNAPSHOT.json').read_text())['blocked'], [])
            self.assertTrue((root/'.tools').is_symlink())
            self.assertFalse((out/'research'/ROOT_NAME/'.tools').exists())

    def test_other_source_symlinks_remain_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);root,_=fixture(h);(root/'src/linked.py').symlink_to(root/'src/model.py')
            out=s.stage(h,h/'snapshot');m=json.loads((out/'PRIVATE_SNAPSHOT.json').read_text())
            self.assertEqual(len(m['blocked']),1)
            self.assertTrue(m['blocked'][0]['path'].endswith('src/linked.py'))

    def test_tools_named_directory_in_other_project_not_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);fixture(h);p=h/'march_shooting_research/.tools';p.mkdir(parents=True)
            (p/'custom.py').write_text('x=3\n')
            out=s.stage(h,h/'snapshot')
            self.assertTrue((out/'research/march_shooting_research/.tools/custom.py').is_file())

    def test_nested_tools_in_src_not_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);root,_=fixture(h);p=root/'src/.tools';p.mkdir();(p/'custom.py').write_text('x=2\n')
            out=s.stage(h,h/'snapshot')
            self.assertTrue((out/'research'/ROOT_NAME/'src/.tools/custom.py').is_file())

    def test_lookalike_names_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);root,_=fixture(h);(root/'.tools_config.py').write_text('x=4\n')
            out=s.stage(h,h/'snapshot')
            self.assertTrue((out/'research'/ROOT_NAME/'.tools_config.py').is_file())

    def test_secret_outside_environment_still_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);root,_=fixture(h);(root/'config.py').write_text('x="'+('ghp_'+'B'*36)+'"\n')
            out=s.stage(h,h/'snapshot');m=json.loads((out/'PRIVATE_SNAPSHOT.json').read_text())
            self.assertEqual(len(m['blocked']),1)
            self.assertIn('possible secret',m['blocked'][0]['reason'])

    def test_prior_blockers_classified_without_reading_source(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);p=h/'march_publication/plans/old/private_source';p.mkdir(parents=True)
            names=['.tools/lib64','.tools/bin/python','.tools/bin/python3','.tools/bin/python3.12']
            (p/'PRIVATE_SNAPSHOT.json').write_text(json.dumps({'files':[], 'blocked':[
                {'path':ROOT_NAME+'/'+n,'reason':'symlink source omitted'} for n in names]}))
            obj=r.inspect_previous(h)
            self.assertTrue(all(b['classification']=='EXCLUDED_BY_DOCUMENTED_DIRECTORY_POLICY' for b in obj['plans'][0]['blockers']))
            self.assertFalse(obj['source_contents_read'])

    def test_fresh_plan_replaces_pointer_not_old_plan(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);fixture(h);old=h/'march_publication/plans/old/private_source';old.mkdir(parents=True)
            evidence=json.dumps({'files':[],'blocked':[{'path':ROOT_NAME+'/.tools/bin/python','reason':'symlink'}]})
            (old/'PRIVATE_SNAPSHOT.json').write_text(evidence)
            with patch.object(g.Path,'home',return_value=h),patch.object(g,'command',side_effect=AssertionError('No account calls while planning')):
                g.plan();folder,m=g.load_plan()
            self.assertEqual(m['status'],'LOCAL_PLAN_READY')
            self.assertEqual(m['blocked_files'],[])
            self.assertEqual((old/'PRIVATE_SNAPSHOT.json').read_text(),evidence)

    def test_outside_and_traversal_paths_do_not_match(self):
        for p in ['/home/user/'+ROOT_NAME+'/.tools', ROOT_NAME+'/../.tools',ROOT_NAME+'/src/.tools',ROOT_NAME+'/.toolsmith']:
            self.assertFalse(s.documented_environment(p),p)
        self.assertTrue(s.documented_environment(ROOT_NAME+'/.tools/lib64'))

    def test_environment_exclusion_keeps_dependency_definitions(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);root,_=fixture(h);out=s.stage(h,h/'snapshot')
            for name in ['pyproject.toml','uv.lock']:
                self.assertEqual((root/name).read_bytes(),(out/'research'/ROOT_NAME/name).read_bytes())


if __name__ == '__main__':
    unittest.main()
