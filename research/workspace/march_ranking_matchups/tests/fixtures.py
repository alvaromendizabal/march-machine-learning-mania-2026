"""Tiny synthetic games and cached reference features; never real score evidence."""
from __future__ import annotations
from pathlib import Path
import json, shutil, subprocess
from unittest.mock import patch
import numpy as np
import pandas as pd
import ranking_workflow as w
ROOT=Path(__file__).resolve().parents[1]


def toy_data():
    rng=np.random.default_rng(7102026);games=[];bases=[];targets=[]
    ids=np.arange(1101,1113)
    for year in w.YEARS:
        abilities=rng.normal(0,1,len(ids));rows=[]
        # Repeated round robin, varied home/neutral sites; connected by construction.
        day=0
        for repeat in range(2):
            for i in range(len(ids)):
                for j in range(i+1,len(ids)):
                    day=day%130+1;home=int(rng.choice([-1,0,1]));p=1/(1+np.exp(-(abilities[i]-abilities[j]+.4*home)))
                    a,b=int(ids[i]),int(ids[j]);wa=rng.random()<p
                    winner,loser=(a,b) if wa else (b,a);loc=home if wa else -home
                    games.append({'Season':year,'DayNum':day,'WTeamID':winner,'LTeamID':loser,
                       'WLoc':{-1:'A',0:'N',1:'H'}[loc],'WScore':int(71+abs(abilities[i]-abilities[j])*7+repeat),'LScore':60})
        for i,t in enumerate(ids):
            row={'Gender':'M','Season':year,'TeamID':int(t),'seed':float(i+1),'games':22.}
            for f in w.sf.CONTROL+w.sf.RESIDUAL+w.sf.PROFILE:
                if f not in row:row[f]=float(rng.normal())
            row.update(strength=float(abilities[i]*5+rng.normal()),win_rate=float(1/(1+np.exp(-abilities[i]))),margin_sd=float(10+rng.random()))
            rows.append(row)
        base=pd.DataFrame(rows);bases.append(base)
        # Distinct selected tournament games; seven per season, keys sorted by official converter.
        for a,b in [(0,11),(1,10),(2,9),(3,8),(4,7),(5,6),(0,1)]:
            p=1/(1+np.exp(-(abilities[a]-abilities[b])));wa=rng.random()<p
            winner,loser=(ids[a],ids[b]) if wa else (ids[b],ids[a])
            targets.append({'Season':year,'DayNum':136+a,'WTeamID':int(winner),'LTeamID':int(loser),'WScore':80,'LScore':70,'WLoc':'N'})
    return pd.DataFrame(games),bases,pd.DataFrame(targets)


def toy_rankings(bases):
    rng=np.random.default_rng(20260912);out=[]
    for base in bases:
        season=int(base.Season.iloc[0]);ids=base.TeamID.to_numpy()
        for system in range(8):
            for day in [110,124,128]:
                score=base.strength.to_numpy()+rng.normal(0,2,len(base))
                ranks=pd.Series(-score).rank(method='first').astype(int).to_numpy()
                for t,rank in zip(ids,ranks):
                    out.append({'Season':season,'RankingDayNum':day,'SystemName':f'S{system:02d}',
                        'TeamID':int(t),'OrdinalRank':int(rank)})
    return pd.DataFrame(out)


def manifest(kit):
    exclude={'MANIFEST.json'}
    w.atomic_json(kit/'MANIFEST.json',{'sha256':{str(p.relative_to(kit)):w.sha(p) for p in kit.rglob('*')
        if p.is_file() and p.name not in exclude and not set(p.parts)&{'private_runs','reports','__pycache__'}}})


def build_fixture(root):
    root=Path(root);names={'kit':'march_ranking_matchups','repo':'repo','shooting':'march_shooting_research',
        'schedule':'march_schedule_research','temporal':'march_temporal_form','possession':'march_possession_research','margin':'march_margin_research'}
    args={k:root/n for k,n in names.items()}
    for p in args.values():p.mkdir(parents=True)
    kit,repo=args['kit'],args['repo']
    for n in w.SOURCES+['12_shared_ranking_matchups.ipynb']:
        p=kit/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/n,p)
    shutil.copytree(ROOT/'evidence',kit/'evidence')
    raw=repo/'data/kaggle/raw';raw.mkdir(parents=True);games,bases,targets=toy_data()
    w.atomic_csv(raw/'MRegularSeasonCompactResults.csv',games);w.atomic_csv(raw/'MNCAATourneyCompactResults.csv',targets)
    w.atomic_csv(raw/'MMasseyOrdinals.csv', toy_rankings(bases))
    (repo/'notebooks').mkdir();(repo/'src').mkdir();(repo/'src/value.py').write_text('VALUE=1\n');(repo/'.gitignore').write_text('data/\n')
    for n in w.rf.ALLOWED_DIRTY:(repo/n).write_text('{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}\n')
    def git(*a):return subprocess.check_output(['git','-C',str(repo),*a],stderr=subprocess.DEVNULL).decode().strip()
    git('init','-b','main');git('config','user.name','Synthetic Test');git('config','user.email','test@example.invalid');git('add','.');git('commit','-m','synthetic fixture');head=git('rev-parse','HEAD');git('update-ref','refs/remotes/origin/main',head)
    for n in w.rf.ALLOWED_DIRTY:(repo/n).write_text((repo/n).read_text()+'\n')
    path=kit/'frozen/research_workflow.py';path.write_text(path.read_text().replace(w.rf.EXPECTED_SHA,head))
    with patch.object(w.rf,'EXPECTED_SHA',head):state=w.rf.repository_state(repo)
    fps={k:char*64 for k,char in [('shooting','a'),('schedule','b'),('temporal','c'),('possession','d')]}
    roots={k:args[k]/'private_runs'/v for k,v in fps.items()}
    for k,p in roots.items():p.mkdir(parents=True);w.atomic_json(p/'manifest.json',{'fingerprint':fps[k],'synthetic':True})
    for s,base in zip(w.YEARS,bases):
        p=roots['shooting']/f'snapshots/M_{s}';w.atomic_csv(p/'teams.csv',base);w.atomic_json(p/'coverage.json',{'synthetic':True})
        w.atomic_csv(p/'opponent_exclusion_audit.csv',pd.DataFrame({'synthetic':[True]}));w.seal(p,['teams.csv','coverage.json','opponent_exclusion_audit.csv'])
    pairs,y=w.sf.tournament_pairs(targets,'M',w.YEARS)
    base=pd.concat(bases,ignore_index=True).set_index(['Season','TeamID']);x=pairs.copy()
    for f in w.sf.CONTROL:
        x['diff_'+f]=[base.loc[(r.Season,r.Team1ID),f]-base.loc[(r.Season,r.Team2ID),f] for r in pairs.itertuples()]
    scores=[]
    for s in w.SEASONS:
        ti,vi=w.rf.split_indices(x,s);m=w.rf.fitted_model(x.iloc[ti],y[ti],w.wf.BASE);m['train_seasons']=list(range(2013,s));p=w.rf.predict(m,x.iloc[vi]);b=float(np.mean((p-y[vi])**2))
        key,rel=w.ORIGINS[s];folder=roots[key]/rel
        pred=pairs.iloc[vi].copy();pred['y']=y[vi];pred['probability']=p
        # Sparse legacy metadata intentionally excludes log_loss.
        metric={'brier':b}
        w.atomic_json(folder/'model.json',m);w.atomic_json(folder/'metrics.json',metric);w.atomic_csv(folder/'predictions.csv',pred);w.seal(folder,w.FIT_FILES)
        scores.append({'Gender':'M','Season':s,'brier':b,'recipe':'anchor'})
    # A synthetic completed prior scientific archive; fixtures deliberately differ from real pins.
    expanded=[]
    for row in scores:
        for name in ['anchor','anchor_huber','anchor_compressed','anchor_both']:
            expanded.append(dict(row,recipe=name))
    table=pd.DataFrame(expanded)
    table["delta_vs_anchor"]=0.0
    w.atomic_csv(kit/'evidence/round11/metrics.csv',table)
    import zipfile,hashlib
    payload={'metrics.csv':table.to_csv(index=False,float_format='%.17g').encode(),
             'decisions.json':json.dumps({'synthetic':True}).encode()}
    report=args['margin']/'reports/milestone_11_return.zip';report.parent.mkdir(parents=True)
    with zipfile.ZipFile(report,'w') as z:
        for n,v in payload.items():z.writestr(n,v)
        z.writestr('return_integrity.json',json.dumps({'sha256':{n:hashlib.sha256(v).hexdigest() for n,v in payload.items()}}))
    pins={k+'/'+str(f.relative_to(p)):w.sha(f) for k,p in roots.items() for f in p.rglob('*') if f.is_file()}
    c={'reference_commit':head,'state':state,'data':{p.name:w.sha(p) for p in raw.glob('*.csv')},'environment':w.environment(),
        'fingerprints':fps,'upstream_pins':pins,'frozen_sources':{n:w.sha(kit/n) for n in ['frozen/research_workflow.py','frozen/shot_features.py']}}
    c['previous_report_sha256']=w.sha(report)
    w.atomic_json(kit/'constraints.json',c);manifest(kit)
    return args,head
