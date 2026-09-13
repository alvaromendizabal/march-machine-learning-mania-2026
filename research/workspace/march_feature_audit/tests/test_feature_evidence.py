import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import feature_evidence as fe


def sh(repo,*args):
    return subprocess.check_output(['git',*args],cwd=repo,stderr=subprocess.DEVNULL).decode().strip()


def nb(source='x = 1\n',outputs=None,tag=None):
    return json.dumps({'nbformat':4,'nbformat_minor':5,'metadata':{},'cells':[{'id':'a','cell_type':'code',
        'source':[source],'outputs':outputs or [],'execution_count':None,
        'metadata':{} if tag is None else {'tags':[tag]}}]}).encode()


def fixture_data():
    registry=pd.DataFrame([{'feature':'diff_seed','family':'core'}, {'feature':'diff_strength','family':'core'},
                           {'feature':'diff_efg','family':'four_factors'},{'feature':'diff_variance','family':'distribution'}])
    usage=[];screen=[];metrics=[]
    for gender in 'MW':
        for model in ['logistic','hist']:
            for season in [2016,2017]:
                games=67 if gender=='M' else 63
                key=dict(Gender=gender,Season=season,model=model,block='full')
                for feature in ['diff_seed','diff_strength' if season==2016 else 'diff_efg']:
                    usage.append(dict(**key,feature=feature,fitted=True,train_nonmissing=200,validation_nonmissing=games,
                                      train_games=200,validation_games=games,standardized_coefficient=None,status='retained'))
                screen.append(dict(**key,capacity=1,near_constant=0,no_training_signal=0,redundant=1,retained=2,
                                   candidate_count=4,retained_count=2,rejected_count=2))
                for block,diff in [('full',0),('strength',-.01),('baseline_124',.01),('without_core',.02)]:
                    metrics.append(dict(Gender=gender,Season=season,model=model,block=block,games=games,
                                        brier=.20+.005*(season-2016)+diff-(.04 if gender=='W' else 0)))
    return {'feature_registry.csv':registry.to_csv(index=False).encode(),
            'feature_usage.csv':pd.DataFrame(usage).to_csv(index=False).encode(),
            'screening_summary.csv':pd.DataFrame(screen).to_csv(index=False).encode(),
            'metrics_by_season.csv':pd.DataFrame(metrics).to_csv(index=False).encode()}


def create_repo(base):
    repo=base/'repo';repo.mkdir()
    sh(repo,'init','-q','--initial-branch=main')
    sh(repo,'config','user.email','local-tests@example.invalid');sh(repo,'config','user.name','Local Tests')
    sh(repo,'remote','add','origin',f'https://github.com/{fe.SLUG}.git')
    (repo/'.gitignore').write_text('data/\n.venv/\n')
    (repo/'src').mkdir();(repo/'src/model.py').write_text('x = 1\n')
    (repo/'notebooks').mkdir();(repo/'notebooks/02_features.ipynb').write_bytes(nb())
    raw=repo/'data/kaggle/raw';raw.mkdir(parents=True)
    (raw/'MTeams.csv').write_text('TeamID,TeamName\n1101,Example\n')
    data_hash=fe.sha_file(raw/'MTeams.csv')
    folder=repo/'reports/feature_store';folder.mkdir(parents=True)
    blobs=fixture_data()
    for name,blob in blobs.items(): (folder/name).write_bytes(blob)
    manifest={'sha256':{name:fe.digest(blob) for name,blob in blobs.items()},
              'manifest':{'evidence_status':'synthetic-fixture-only','inputs':{
                  'data':{'MTeams.csv':data_hash},'source':{'src/model.py':fe.sha_file(repo/'src/model.py')}}}}
    (folder/'run.json').write_text(json.dumps(manifest))
    sh(repo,'add','.');sh(repo,'commit','-qm','Synthetic test fixture')
    head=sh(repo,'rev-parse','HEAD')
    prior=base/'prior';prior.mkdir()
    (prior/'milestone_summary.json').write_text(json.dumps(dict(head=head,canonical_path_ready=True,
        core_files_missing=[],schema_errors={},modeled_season_coverage_gaps={},
        raw_fingerprints=[dict(file='MTeams.csv',sha256=data_hash)])))
    return repo,head,prior


class ReportTests(unittest.TestCase):
    def test_outputs_only_classification(self):
        a=nb(); b=nb(outputs=[{'output_type':'stream','name':'stdout','text':['1']}])
        self.assertEqual(fe.classify('x.ipynb',a,a,b),'notebook_outputs_or_execution_only')
    def test_cell_source_change_preserved(self):
        a=nb(); self.assertEqual(fe.classify('x.ipynb',a,a,nb('x = 2\n')),'notebook_source_or_metadata_change')
    def test_execution_tags_are_not_ignored(self):
        a=nb(); self.assertEqual(fe.classify('x.ipynb',a,a,nb(tag='skip-execution')),'notebook_source_or_metadata_change')
    def test_invalid_notebook_not_assumed_safe(self):
        self.assertEqual(fe.classify('x.ipynb',nb(),nb(),b'invalid'),'notebook_requires_review')
    def test_mode_only_classification(self):
        self.assertEqual(fe.classify('x.py',b'x',b'x',b'x',True),'mode_only')
    def test_traversal_refused(self):
        for name in ['../x','/x','.git/config']:
            with self.assertRaises(fe.Stop):fe.safe_relative(name)
    def test_counts_and_weighting(self):
        result=fe.summarize_reports(fixture_data())
        self.assertEqual(len(result['full_screening']),8)
        self.assertEqual(result['usage'].feature.nunique(),3)
        self.assertEqual(int(result['family_by_fit'].groupby(['route','Season']).retained.sum().min()),2)
        self.assertAlmostEqual(result['ablations'].delta_without_minus_full.mean(),.02)
    def test_false_string_not_truthy(self):
        values=fe.bool_series(pd.Series(['False','True']))
        self.assertEqual(values.tolist(),[False,True])
    def test_unknown_boolean_refused(self):
        with self.assertRaises(fe.Stop):fe.bool_series(pd.Series(['maybe']))
    def test_duplicate_usage_refused(self):
        raw=fixture_data(); df=pd.read_csv(__import__('io').BytesIO(raw['feature_usage.csv']))
        raw['feature_usage.csv']=pd.concat([df,df.iloc[[0]]]).to_csv(index=False).encode()
        with self.assertRaisesRegex(fe.Stop,'DUPLICATE_USAGE'):fe.summarize_reports(raw)
    def test_unknown_family_refused(self):
        raw=fixture_data(); raw['feature_registry.csv']=b'feature,family\ndiff_seed,core\n'
        with self.assertRaisesRegex(fe.Stop,'MISSING_FROM_REGISTRY'):fe.summarize_reports(raw)
    def test_count_mismatch_refused(self):
        raw=fixture_data();raw['screening_summary.csv']=raw['screening_summary.csv'].replace(b',4,2,2',b',5,2,2')
        with self.assertRaises(fe.Stop):fe.summarize_reports(raw)
    def test_future_season_refused(self):
        raw={k:v.replace(b'2017',b'2026') for k,v in fixture_data().items()}
        with self.assertRaisesRegex(fe.Stop,'UNEXPECTED_STUDY_SEASON'):fe.summarize_reports(raw)
    def test_unequal_games_not_paired(self):
        raw=fixture_data();df=pd.read_csv(__import__('io').BytesIO(raw['metrics_by_season.csv']))
        df.loc[df.block.eq('without_core'),'games']=1
        raw['metrics_by_season.csv']=df.to_csv(index=False).encode()
        result=fe.summarize_reports(raw)
        self.assertTrue(result['ablations'].delta_without_minus_full.isna().all())
    def test_weighted_mean_is_not_macro_mean(self):
        raw=fixture_data();df=pd.read_csv(__import__('io').BytesIO(raw['metrics_by_season.csv']))
        pick=(df.Gender=='M')&(df.model=='logistic')&(df.block=='full')
        df.loc[pick&(df.Season==2016),['games','brier']]=[1,.1]
        df.loc[pick&(df.Season==2017),['games','brier']]=[3,.3]
        raw['metrics_by_season.csv']=df.to_csv(index=False).encode()
        row=fe.summarize_reports(raw)['metric_summary'].query("Gender == 'M' and model == 'logistic' and block == 'full'").iloc[0]
        self.assertAlmostEqual(row.mean_season_brier,.2);self.assertAlmostEqual(row.game_weighted_brier,.25)
    def test_chart_generation(self):
        figures=fe.make_figures(fe.summarize_reports(fixture_data()))
        self.assertEqual(len(figures),18)
        self.assertTrue(all(fig.to_json() for _,fig in figures))


class GitTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
        self.repo,self.head,self.prior=create_repo(self.base)
        self.run=fe.Budget(self.base/'kit/reports',45)
    def tearDown(self):
        self.run.close();self.tmp.cleanup()
    def test_clean_checkout_read_only(self):
        before=(self.repo/'.git/index').read_bytes()
        state=fe.inspect_worktree(self.run,self.repo,self.head)
        self.assertTrue(state['tracked_clean']);self.assertEqual((self.repo/'.git/index').read_bytes(),before)
    def test_staged_and_unstaged_bytes_backed_up(self):
        p=self.repo/'src/model.py';p.write_text('x = 2\n');sh(self.repo,'add','src/model.py');p.write_text('x = 3\n')
        before=(self.repo/'.git/index').read_bytes()
        state=fe.inspect_worktree(self.run,self.repo,self.head)
        row=state['changed_files'][0]
        self.assertTrue(row['staged']);self.assertTrue(row['unstaged'])
        backup=Path(state['private_backup_directory'])
        self.assertEqual((backup/'index/src/model.py').read_text(),'x = 2\n')
        self.assertEqual((backup/'worktree/src/model.py').read_text(),'x = 3\n')
        self.assertEqual((self.repo/'.git/index').read_bytes(),before);self.assertEqual(p.read_text(),'x = 3\n')
    def test_net_zero_change_still_detects_staged_version(self):
        p=self.repo/'src/model.py';p.write_text('x = 2\n');sh(self.repo,'add','src/model.py');p.write_text('x = 1\n')
        state=fe.inspect_worktree(self.run,self.repo,self.head)
        self.assertEqual(state['tracked_change_count'],1);self.assertFalse(state['tracked_clean'])
    def test_untracked_ignored_data_preserved(self):
        (self.repo/'untracked.txt').write_text('preserve me')
        data=self.repo/'data/kaggle/raw/MTeams.csv';before=data.read_bytes()
        state=fe.inspect_worktree(self.run,self.repo,self.head)
        self.assertEqual(state['untracked_file_count'],1);self.assertEqual(data.read_bytes(),before)
    def test_assume_unchanged_flags_block_ready(self):
        sh(self.repo,'update-index','--assume-unchanged','src/model.py')
        (self.repo/'src/model.py').write_text('changed\n')
        state=fe.inspect_worktree(self.run,self.repo,self.head)
        self.assertFalse(state['tracked_clean']);self.assertEqual(state['hidden_index_flag_count'],1)
    def test_wrong_head_stops(self):
        with self.assertRaisesRegex(fe.Stop,'REFERENCE_COMMIT_CHANGED'):fe.inspect_worktree(self.run,self.repo,'0'*40)
    def test_raw_change_detected_without_deleting(self):
        p=self.repo/'data/kaggle/raw/MTeams.csv';p.write_text('different')
        result=fe.revalidate_data(self.run,self.repo,self.prior)
        self.assertFalse(result['passed']);self.assertEqual(p.read_text(),'different')
    def test_cache_reuse_and_tamper_recovery(self):
        r,m,_=fe.collect_reports(self.run,self.repo,self.head)
        r2,_,_=fe.collect_reports(self.run,self.repo,self.head)
        self.assertEqual(r,r2)
        file=next((self.run.out/'cache').glob('*/feature_usage.csv'));file.write_bytes(b'corrupt')
        r3,_,_=fe.collect_reports(self.run,self.repo,self.head)
        self.assertEqual(r,r3)
    def test_edited_worktree_report_not_used_as_committed_evidence(self):
        (self.repo/'reports/feature_store/feature_registry.csv').write_text('bad')
        raws,_,_=fe.collect_reports(self.run,self.repo,self.head)
        self.assertIn(b'feature,family',raws['feature_registry.csv'])
        self.assertEqual((self.repo/'reports/feature_store/feature_registry.csv').read_text(),'bad')
    def test_no_changed_source_imported(self):
        (self.repo/'src/model.py').write_text('raise RuntimeError("DO NOT IMPORT")\n')
        state=fe.inspect_worktree(self.run,self.repo,self.head)
        self.assertFalse(state['tracked_clean'])
    def test_full_diagnostic_still_runs_while_dirty(self):
        (self.repo/'notebooks/02_features.ipynb').write_bytes(nb(outputs=[{'output_type':'stream','name':'stdout','text':['saved']}]))
        result=fe.run_audit(self.run,self.repo,self.prior,self.head)
        self.assertEqual(result['status'],'REVIEW_REQUIRED');self.assertEqual(result['new_models_fitted'],0)
        self.assertTrue(result['repository_state_unchanged']);self.assertTrue(result['data_preflight_revalidated'])
        self.assertTrue((self.run.out/'feature_evidence.html').is_file())
        with zipfile.ZipFile(self.run.out/'milestone_01_return.zip') as z:
            self.assertFalse(any('private' in name or '.ipynb' in name for name in z.namelist()))
    def test_timeout_check(self):
        self.run.deadline=0
        with self.assertRaisesRegex(fe.Stop,'TIME_LIMIT'):self.run.check()

if __name__=='__main__': unittest.main()
