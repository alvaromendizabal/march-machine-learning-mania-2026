"""Synthetic full-size tournament fields; never real competition-performance evidence."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
from unittest.mock import patch
import zipfile
import numpy as np
import pandas as pd
import consensus_workflow as w
import consensus_features as cf
from research_io import sf,rf

ROOT=Path(__file__).resolve().parents[1]


def toy_data():
    rng=np.random.default_rng(20260913);ids=np.arange(1101,1169)
    codes=[]
    for r in 'WXYZ':
        for seed in range(1,17):
            stem=f'{r}{seed:02d}'
            codes += [stem+'a',stem+'b'] if stem in ['W16','X16','Y11','Z11'] else [stem]
    code_to_id=dict(zip(codes,ids));first_pair=(int(code_to_id['W01']),int(code_to_id['W02']))
    names=pd.DataFrame({'TeamID':ids,'TeamName':[('Oregon' if t==first_pair[0] else 'VCU' if t==first_pair[1] else f'Team {t}') for t in ids]})
    compact=[];detailed=[];seedrows=[];results=[];ranking=[]
    for year in cf.YEARS:
        ab=rng.normal(0,1,len(ids))
        for t,code in zip(ids,codes):seedrows.append({'Season':year,'TeamID':int(t),'Seed':code})
        used=set()
        for rnd in range(24):
            perm=rng.permutation(ids);day=5+rnd*5
            for a,b in zip(perm[::2],perm[1::2]):
                home=int(rng.choice([-1,0,1]));p=1/(1+np.exp(-(ab[a-1101]-ab[b-1101]+.3*home)))
                aw=rng.random()<p;win,lose=(a,b) if aw else (b,a)
                box={}
                for side in ['W','L']:
                    made=(28 if side=='W' else 23)+int(rng.integers(0,3))
                    threes=int(rng.integers(4,10));ft=12 if side=='W' else 9
                    for k,v in {'FGM':made,'FGA':60,'FGM3':threes,'FGA3':22,'FTM':ft,'FTA':18,
                                'OR':9,'DR':28,'TO':12}.items():box[side+k]=v
                ws=2*box['WFGM']+box['WFGM3']+box['WFTM'];ls=2*box['LFGM']+box['LFGM3']+box['LFTM']
                assert ws>ls
                game={'Season':year,'DayNum':day,'WTeamID':int(win),'LTeamID':int(lose),'WScore':ws,'LScore':ls,
                      'WLoc':{-1:'A',0:'N',1:'H'}[home if aw else -home],'NumOT':0}
                compact.append(game);detailed.append(dict(game,**box))
        survivors=[]
        for stem in [f'{r}{s:02d}' for r in 'WXYZ' for s in range(1,17)]:
            group=[code_to_id[c] for c in codes if c[:3]==stem]
            if len(group)==2:
                winner,loser=group
                results.append({'Season':year,'DayNum':136 if year==2021 else 134,'WTeamID':int(winner),'LTeamID':int(loser),'WScore':78,'LScore':65,'WLoc':'N'})
                survivors.append(winner)
            else:survivors.extend(group)
        rnd=0
        while len(survivors)>1:
            next_round=[]
            for a,b in zip(survivors[::2],survivors[1::2]):
                winner,loser=(a,b) if rng.random()<.55 else (b,a)
                nc=year==2021 and rnd==0 and {int(a),int(b)}==set(first_pair)
                if nc:winner,loser=first_pair
                results.append({'Season':year,'DayNum':(137 if year==2021 else 136)+rnd*3,'WTeamID':int(winner),'LTeamID':int(loser),
                    'WScore':2 if nc else 80,'LScore':0 if nc else 70,'WLoc':'N'})
                next_round.append(winner)
            survivors=next_round;rnd+=1
        for system in range(8):
            for day in [110,124,128,150]:
                strength=ab+rng.normal(0,.4,len(ids));ordinals=pd.Series(-strength).rank(method='first').astype(int)
                for t,rank in zip(ids,ordinals):ranking.append({'Season':year,'RankingDayNum':day,'SystemName':f'S{system:02d}','TeamID':int(t),'OrdinalRank':int(rank)})
    return pd.DataFrame(compact),pd.DataFrame(detailed),pd.DataFrame(seedrows),pd.DataFrame(results),names,pd.DataFrame(ranking)


def write_manifest(kit):
    w.atomic_json(kit/'MANIFEST.json',{'sha256':{str(p.relative_to(kit)):w.sha(p) for p in kit.rglob('*')
        if p.is_file() and p.name!='MANIFEST.json' and not set(p.relative_to(kit).parts)&{'__pycache__','reports','private_runs'}}})


def build_fixture(root):
    root=Path(root);args={k:root/n for k,n in [('kit','march_consensus_validation'),('repo','repo'),('shooting','march_shooting_research'),('rankings','march_ranking_matchups')]}
    for p in args.values():p.mkdir(parents=True)
    kit,repo=args['kit'],args['repo']
    for name in w.SOURCES+['13_consensus_later_era.ipynb']:
        p=kit/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
    shutil.copytree(ROOT/'evidence',kit/'evidence')
    compact,detailed,seeds,targets,names,ranks=toy_data();raw=repo/'data/kaggle/raw';raw.mkdir(parents=True)
    for name,frame in [('MRegularSeasonCompactResults',compact),('MRegularSeasonDetailedResults',detailed),('MNCAATourneySeeds',seeds),
                       ('MNCAATourneyCompactResults',targets),('MTeams',names),('MMasseyOrdinals',ranks)]:w.atomic_csv(raw/(name+'.csv'),frame)
    (repo/'src').mkdir();(repo/'src/example.py').write_text('VALUE=1\n');(repo/'.gitignore').write_text('data/\n')
    for n in rf.ALLOWED_DIRTY:
        (repo/n).parent.mkdir(exist_ok=True);(repo/n).write_text('{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}\n')
    def git(*a):return subprocess.check_output(['git','-C',str(repo),*a],stderr=subprocess.DEVNULL).decode().strip()
    git('init','-b','main');git('config','user.email','test@example.invalid');git('config','user.name','Synthetic Test');git('add','.');git('commit','-m','synthetic')
    head=git('rev-parse','HEAD');git('update-ref','refs/remotes/origin/main',head)
    for n in rf.ALLOWED_DIRTY:(repo/n).write_text((repo/n).read_text()+'\n')
    p=kit/'frozen/research_workflow.py';p.write_text(p.read_text().replace(rf.EXPECTED_SHA,head))
    with patch.object(rf,'EXPECTED_SHA',head):state=rf.repository_state(repo)
    fps={'shooting':'a'*64,'rankings':'b'*64};roots={k:args[k]/'private_runs'/fp for k,fp in fps.items()}
    for k,p in roots.items():p.mkdir(parents=True);w.atomic_json(p/'manifest.json',{'fingerprint':fps[k],'synthetic':True})
    # Real reference component formulas, not fabricated new-year ratings.
    import ranking_features_round12 as oldrank
    tables=[]
    for s in cf.OLD_YEARS:
        base,audit=sf.build_snapshot(compact,detailed,seeds,'M',s)
        folder=roots['shooting']/f'snapshots/M_{s}';w.atomic_csv(folder/'teams.csv',base)
        w.atomic_csv(folder/'opponent_exclusion_audit.csv',audit);w.atomic_json(folder/'coverage.json',{'synthetic':True})
        w.seal(folder,['teams.csv','coverage.json','opponent_exclusion_audit.csv'])
        panel,info=oldrank.publication_panel(ranks,s);pf=roots['rankings']/f'panels/M_{s}'
        w.atomic_csv(pf/'panel.csv',panel);w.atomic_json(pf/'panel_support.json',info);w.seal(pf,w.PANEL_FILES)
        pair,profile,support,detail=oldrank.build_matchups(base,panel);folder=roots['rankings']/f'snapshots/M_{s}'
        for n,f in [('matchups.csv',pair),('team_profiles.csv',profile),('pair_support.csv',detail)]:w.atomic_csv(folder/n,f)
        w.atomic_json(folder/'support.json',support);w.seal(folder,['matchups.csv','team_profiles.csv','pair_support.csv','support.json']);tables.append(pair)
    pairs,y=sf.tournament_pairs(targets,'M',cf.OLD_YEARS)
    x=pairs.merge(pd.concat(tables,ignore_index=True),on=cf.KEYS,validate='one_to_one');rows=[];preds=[]
    for s in [2016,2017,2018,2019]:
        ti,vi=rf.split_indices(x,s)
        for recipe,cols in oldrank.RECIPES.items():
            model=rf.fitted_model(x.iloc[ti],y[ti],cols);model['train_seasons']=list(range(2013,s));probs=rf.predict(model,x.iloc[vi])
            metric={'Gender':'M','Season':s,'recipe':recipe,'games':len(vi),'train_games':len(ti),'brier':float(np.mean((probs-y[vi])**2)),
                'log_loss':float(-np.mean(y[vi]*np.log(probs)+(1-y[vi])*np.log1p(-probs)))}
            folder=roots['rankings']/f'fits/M_{s}_{recipe}';pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=probs
            w.atomic_json(folder/'model.json',model);w.atomic_json(folder/'metrics.json',metric);w.atomic_csv(folder/'predictions.csv',pred);w.seal(folder,w.FIT_FILES)
            pred['recipe']=recipe;preds.append(pred);rows.append(metric)
    metrics=pd.DataFrame(rows);metrics=metrics.merge(metrics.query("recipe=='anchor'")[['Season','brier']].rename(columns={'brier':'anchor_brier'}),on='Season')
    metrics['delta_vs_anchor']=metrics.brier-metrics.anchor_brier
    w.atomic_csv(roots['rankings']/'metrics.csv',metrics);w.atomic_csv(roots['rankings']/'predictions.csv',pd.concat(preds,ignore_index=True))
    w.atomic_csv(roots['rankings']/'coverage.csv',pd.DataFrame({'synthetic':[True]}))
    w.atomic_json(roots['rankings']/'decisions.json',{'synthetic':True,'decisions':[]})
    w.stage_seal(roots['rankings'],'prepare',['coverage.csv']);w.stage_seal(roots['rankings'],'evaluation',['metrics.csv','predictions.csv','decisions.json'])
    report=args['rankings']/'reports/milestone_12_return.zip';report.parent.mkdir()
    payload={n:(roots['rankings']/n).read_bytes() for n in ['metrics.csv','decisions.json','manifest.json','prepare_hashes.json','evaluation_hashes.json']}
    with zipfile.ZipFile(report,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in payload.items():z.writestr(n,b)
        z.writestr('return_integrity.json',json.dumps({'sha256':{n:hashlib.sha256(b).hexdigest() for n,b in payload.items()}}))
    w.atomic_csv(kit/'evidence/round12/metrics.csv',metrics)
    c={'reference_commit':head,'state':state,'data':{p.name:w.sha(p) for p in raw.glob('*.csv')},'environment':w.environment(),'fingerprints':fps,
       'previous_report_sha256':w.sha(report),'ranking_manifest_sha256':w.sha(roots['rankings']/'manifest.json'),
       'ranking_preparation_hashes_sha256':w.sha(roots['rankings']/'prepare_hashes.json'),'ranking_evaluation_hashes_sha256':w.sha(roots['rankings']/'evaluation_hashes.json'),
       'frozen_sources':{n:w.sha(kit/n) for n in ['frozen/research_workflow.py','frozen/shot_features.py','frozen/ranking_features_round12.py']},
       'shooting_pins':{str(p.relative_to(roots['shooting'])):w.sha(p) for p in roots['shooting'].rglob('*') if p.is_file()}}
    w.atomic_json(kit/'constraints.json',c);write_manifest(kit)
    return args,head
