"""Offline tests use temporary local Git repos and synthetic CSVs, never user data."""
import contextlib
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import workspace_sync as w


def cmd(cwd,*args):
    return subprocess.run(['git',*args],cwd=cwd,check=True,capture_output=True,text=True).stdout.strip()

def identity(p):
    cmd(p,'config','user.name','Offline Test')
    cmd(p,'config','user.email','test@example.invalid')


def synthetic(root):
    root.mkdir(parents=True,exist_ok=True)
    for name in sorted(w.CORE | {'MMasseyOrdinals.csv','SampleSubmissionStage2.csv'}):
        cols=sorted(w.required_columns(name))
        with (root/name).open('w',newline='') as out:
            writer=csv.DictWriter(out,fieldnames=cols);writer.writeheader()
            years=[y for y in range(2013,2027) if y!=2020] if 'Season' in cols else [None]
            for year in years:
                row={c:1 for c in cols}
                if year:row['Season']=year
                if 'TeamID' in cols:row['TeamID']=1101 if name[0]=='M' else 3101
                if 'TeamName' in cols:row['TeamName']='Synthetic Test Team'
                if 'DayNum' in cols:row['DayNum']=140 if 'NCAATourney' in name else 100
                if 'RankingDayNum' in cols:row['RankingDayNum']=133 if year==2026 else 100
                if 'DayZero' in cols:row['DayZero']=f'{year-1}-11-01'
                if 'Seed' in cols:row['Seed']='W01'
                if 'ID' in cols:row['ID']='2026_1101_1102';row['Pred']=0.5
                if 'SystemName' in cols:row['SystemName']='SYN'
                writer.writerow(row)

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
        self.origin=self.base/'origin';self.origin.mkdir()
        cmd(self.origin,'init','-b','main');identity(self.origin)
        (self.origin/'README.md').write_text('old\n')
        (self.origin/'.gitignore').write_text('data/\noutputs/\nmodels/\nsubmissions/\n.venv/\n')
        (self.origin/'notebooks').mkdir();(self.origin/'notebooks/00.ipynb').write_text('old notebook\n')
        cmd(self.origin,'add','.');cmd(self.origin,'commit','-m','initial')
        self.old=cmd(self.origin,'rev-parse','HEAD')
        self.repo=self.base/'repo'
        subprocess.run(['git','clone',str(self.origin),str(self.repo)],check=True,capture_output=True)
        identity(self.repo)
        (self.origin/'README.md').write_text('new\n');cmd(self.origin,'commit','-am','new source')
        self.new=cmd(self.origin,'rev-parse','HEAD')
        self.runs=[]
        self.quiet=contextlib.redirect_stdout(io.StringIO());self.quiet.__enter__()
    def tearDown(self):
        for r in self.runs:
            r.stop_event.set();r.thread.join(timeout=1)
        self.quiet.__exit__(None,None,None);self.tmp.cleanup()
    def runstage(self,name='test',seconds=60):
        r=w.Run(self.base/'receipts',name,seconds);self.runs.append(r);return r
    def sync(self):return w.sync(self.runstage(),self.repo,self.new,test_remote=self.origin)
    def test_clean_fast_forward(self):
        result=self.sync();self.assertEqual(cmd(self.repo,'rev-parse','HEAD'),self.new)
        self.assertTrue(result['tracked_matches_origin_main'])
    def test_staged_and_unstaged_notebooks_preserved(self):
        p=self.repo/'notebooks/00.ipynb';p.write_text('staged\n');cmd(self.repo,'add',str(p));p.write_text('unstaged\n')
        result=self.sync();self.assertIsNotNone(result['stash_commit'])
        self.assertIn('unstaged',cmd(self.repo,'show',result['stash_commit']+':notebooks/00.ipynb'))
        self.assertIn('staged',cmd(self.repo,'show',result['stash_commit']+'^2:notebooks/00.ipynb'))
        self.assertTrue((Path(result['recovery_directory'])/'history.bundle').is_file())
        self.assertEqual(p.read_text(),'old notebook\n')
    def test_untracked_file_preserved(self):
        p=self.repo/'local_notes.txt';p.write_text('keep me')
        self.sync();self.assertEqual(p.read_text(),'keep me')
    def test_raw_and_checkpoints_unchanged(self):
        p=self.repo/'data/kaggle/raw';synthetic(p)
        (self.repo/'outputs').mkdir();model=self.repo/'outputs/model.bin';model.write_bytes(b'private\x00bytes')
        before=w.sha(model);result=self.sync()
        self.assertEqual(w.sha(model),before);self.assertTrue(result['raw_sha256_unchanged'])
        self.assertGreater(result['raw_files_hashed'],0)
    def test_unmerged_local_commit_stops_before_stash(self):
        (self.repo/'README.md').write_text('my new research');cmd(self.repo,'commit','-am','unpublished')
        head=cmd(self.repo,'rev-parse','HEAD')
        with self.assertRaisesRegex(w.Stop,'UNMERGED_LOCAL_COMMITS'):self.sync()
        self.assertEqual(cmd(self.repo,'rev-parse','HEAD'),head)
        self.assertEqual(cmd(self.repo,'stash','list'),'')
    def test_remote_changed_stops_without_checkout(self):
        with self.assertRaisesRegex(w.Stop,'REMOTE_MAIN_CHANGED'):
            w.sync(self.runstage(),self.repo,self.old,test_remote=self.origin)
        self.assertEqual(cmd(self.repo,'rev-parse','HEAD'),self.old)
    def test_wrong_origin_rejected(self):
        with self.assertRaisesRegex(w.Stop,'UNEXPECTED_ORIGIN'):w.repo_check(self.runstage(),self.repo)
    def test_missing_repo_rejected(self):
        with self.assertRaisesRegex(w.Stop,'REPOSITORY_NOT_FOUND'):w.repo_check(self.runstage(),self.base/'missing')
    def test_untracked_upstream_collision_rejected(self):
        (self.origin/'notes.txt').write_text('upstream');cmd(self.origin,'add','.');cmd(self.origin,'commit','-m','notes')
        self.new=cmd(self.origin,'rev-parse','HEAD');(self.repo/'notes.txt').write_text('private')
        with self.assertRaisesRegex(w.Stop,'UNTRACKED_COLLISION'):self.sync()
        self.assertEqual((self.repo/'notes.txt').read_text(),'private')
    def test_ignored_upstream_collision_rejected(self):
        (self.repo/'.git/info/exclude').write_text('notes.txt\n')
        (self.repo/'notes.txt').write_text('private ignored')
        (self.origin/'notes.txt').write_text('new');cmd(self.origin,'add','notes.txt');cmd(self.origin,'commit','-m','new ignored collision')
        self.new=cmd(self.origin,'rev-parse','HEAD')
        with self.assertRaisesRegex(w.Stop,'UNTRACKED_COLLISION'):self.sync()
        self.assertEqual((self.repo/'notes.txt').read_text(),'private ignored')
    def test_repeat_sync_preserves_old_stash(self):
        (self.repo/'notebooks/00.ipynb').write_text('edits')
        first=self.sync();second=self.sync()
        self.assertIn(first['stash_commit'],cmd(self.repo,'stash','list','--format=%H'))
        self.assertEqual(second['head'],self.new)
    def test_merged_feature_branch_switches_safely(self):
        cmd(self.repo,'switch','-c','feat/old')
        result=self.sync();self.assertEqual(result['branch'],'main')
    def test_zip_traversal_rejected(self):
        z=self.base/'bad.zip'
        with zipfile.ZipFile(z,'w') as out:out.writestr('../MTeams.csv','x')
        with zipfile.ZipFile(z) as src:
            with self.assertRaisesRegex(w.Stop,'UNSAFE_ZIP'):w.safe_zip_members(src)
    def test_zip_symlink_rejected(self):
        z=self.base/'bad.zip';info=zipfile.ZipInfo('MTeams.csv');info.external_attr=0o120777<<16
        with zipfile.ZipFile(z,'w') as out:out.writestr(info,'target')
        with zipfile.ZipFile(z) as src:
            with self.assertRaisesRegex(w.Stop,'UNSAFE_ZIP'):w.safe_zip_members(src)
    def test_zip_duplicate_basename_rejected(self):
        z=self.base/'bad.zip'
        with zipfile.ZipFile(z,'w') as out:out.writestr('a/MTeams.csv','x');out.writestr('b/MTeams.csv','y')
        with zipfile.ZipFile(z) as src:
            with self.assertRaisesRegex(w.Stop,'DUPLICATE_ZIP'):w.safe_zip_members(src)
    def test_copy_never_overwrites(self):
        source=self.base/'source';synthetic(source)
        target=self.repo/'data/kaggle/raw';target.mkdir(parents=True)
        (target/'MTeams.csv').write_text('private,do not overwrite\n')
        with self.assertRaisesRegex(w.Stop,'RAW_SNAPSHOT_CONFLICT'):
            w.copy_csvs(self.runstage(),source,target,self.repo)
        self.assertEqual(len(list(target.iterdir())),1)
        self.assertIn('private',(target/'MTeams.csv').read_text())
    def test_copy_resumable_verified(self):
        source=self.base/'source';synthetic(source);target=self.repo/'data/kaggle/raw'
        first=w.copy_csvs(self.runstage(),source,target,self.repo)
        second=w.copy_csvs(self.runstage(),source,target,self.repo)
        self.assertGreater(first['files_copied'],0);self.assertEqual(second['files_copied'],0)
    def test_audit_checkpoint_reuse(self):
        raw=self.base/'raw';synthetic(raw);cache=self.base/'cache';cache.mkdir()
        p=raw/'MRegularSeasonDetailedResults.csv';run=self.runstage()
        a=w.audit_file(run,p,cache);b=w.audit_file(run,p,cache)
        self.assertEqual(a,b);self.assertIsNone(a['error'])
        self.assertIn('file_audit_reused',(run.directory/'events.jsonl').read_text())
    def test_massey_post132_not_counted_as_legal(self):
        raw=self.base/'raw';synthetic(raw);cache=self.base/'cache';cache.mkdir()
        a=w.audit_file(self.runstage(),raw/'MMasseyOrdinals.csv',cache)
        self.assertEqual(a['seasons']['2026']['pre132_rows'],0)
        self.assertEqual(a['seasons']['2026']['systems_pre132'],[])
    def test_current_tourney_outcomes_flagged(self):
        raw=self.base/'raw';synthetic(raw);cache=self.base/'cache';cache.mkdir()
        a=w.audit_file(self.runstage(),raw/'MNCAATourneyCompactResults.csv',cache)
        self.assertTrue(a['has_2026_tournament_labels'])
    def test_bad_schema_recorded(self):
        p=self.base/'MTeams.csv';p.write_text('Wrong\n1\n');cache=self.base/'cache';cache.mkdir()
        a=w.audit_file(self.runstage(),p,cache);self.assertIn('Missing columns',a['error'])
    def test_full_audit_outputs_no_training(self):
        self.sync();cmd(self.repo,'remote','set-url','origin',w.REMOTE)
        synthetic(self.repo/'data/kaggle/raw')
        result=w.audit(self.runstage(),self.repo,self.new)
        self.assertTrue(result['ready_for_next_feature_milestone'])
        s=json.loads((self.base/'receipts/milestone_summary.json').read_text())
        self.assertEqual(s['new_experiments_run'],0)
    def test_missing_data_stops(self):
        with self.assertRaisesRegex(w.Stop,'RAW_DATA_MISSING'):w.choose_raw(self.repo)
    def test_assume_unchanged_edits_are_not_lost(self):
        cmd(self.repo,'update-index','--assume-unchanged','README.md')
        (self.repo/'README.md').write_text('hidden local edit')
        with self.assertRaisesRegex(w.Stop,'HIDDEN_INDEX_FLAGS'):self.sync()
        self.assertEqual((self.repo/'README.md').read_text(),'hidden local edit')
    def test_skip_worktree_entries_stop(self):
        cmd(self.repo,'update-index','--skip-worktree','README.md')
        with self.assertRaisesRegex(w.Stop,'HIDDEN_INDEX_FLAGS'):self.sync()
    def test_child_process_timeout(self):
        import time
        r=self.runstage(seconds=5)
        with self.assertRaises(subprocess.TimeoutExpired):
            r.command([sys.executable,'-c','import time; time.sleep(10)'],limit=0.1)

if __name__=='__main__':unittest.main(verbosity=2)
