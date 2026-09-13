"""Interactive research evidence; no Jinja2, Styler, web assets, or image renderer."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def read(p):return pd.read_csv(p,float_precision='round_trip')

def figures(run:Path,evidence:Path):
    run=Path(run);prior=read(Path(evidence)/'replication_metrics.csv')
    prior=prior.query("recipe == 'anchor_change'").copy();prior['year_role']=prior.Season.astype(str)+' · '+prior.role
    charts=[]
    f=px.bar(prior,x='year_role',y='delta_vs_anchor',title='07 · Temporal-change results: discovery gains did not replicate',labels={'delta_vs_anchor':'Brier change (negative is better)','year_role':'Season and role'})
    f.add_hline(y=0);charts.append(f)
    registry=read(run/'feature_registry.csv');counts=registry.groupby('family').size().reset_index(name='inputs')
    charts.append(px.bar(counts,x='family',y='inputs',title='08 · Four new nonlinear candidates, plus six ordinary rate controls'))
    cover=read(run/'coverage.csv')
    charts.append(px.line(cover,x='Season',y='min_seeded_detail_games',color='Gender',markers=True,title='Minimum regular-season detailed-game support among tournament teams'))
    diag=read(run/'matchup_diagnostics.csv')
    charts.append(px.scatter(diag,x='a_proxy_pp100',y='b_proxy_pp100',color='Gender',hover_data=['Season','Team1ID','Team2ID'],title='Approximate scoring profiles: not calibrated game predictions',labels={'a_proxy_pp100':'Team A proxy points/100','b_proxy_pp100':'Team B proxy points/100'}))
    m=read(run/'metrics.csv');m['route']=m.Gender+' · '+m.recipe
    charts.append(px.line(m,x='Season',y='brier',color='route',markers=True,title='Four-season Brier — every predeclared recipe, no best-season filtering'))
    f=px.bar(m.query("recipe!='anchor'"),x='Season',y='delta_vs_anchor',color='route',barmode='group',title='Changes versus the original 16-input reference');f.add_hline(y=0);charts.append(f)
    a=read(run/'ablations.csv');primary=a.query("comparison=='mechanism_given_rates'")
    f=px.bar(primary,x='Season',y='delta_brier',color='Gender',barmode='group',title='PRIMARY: Do nonlinear candidates beat the rate-augmented reference?');f.add_hline(y=0);charts.append(f)
    means=a.groupby(['Gender','comparison'],as_index=False).delta_brier.mean()
    f=px.bar(means,x='comparison',y='delta_brier',color='Gender',barmode='group',title='Controlled family effects — negative favors inclusion');f.add_hline(y=0);charts.append(f)
    p=read(run/'predictions.csv');p=p[p.recipe.isin(['anchor_rates','anchor_both'])].copy();p['bin']=np.minimum((p.probability*10).astype(int),9)
    rel=p.groupby(['Gender','recipe','bin'],as_index=False).agg(predicted=('probability','mean'),observed=('y','mean'),games=('y','size'))
    rel['route']=rel.Gender+' · '+rel.recipe
    f=px.scatter(rel,x='predicted',y='observed',size='games',color='route',hover_data=['bin','games'],title='Calibration of the primary comparison — sparse bins are descriptive')
    f.add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Identity',line={'dash':'dash'}));charts.append(f)
    r=read(run/'training_redundancy.csv');r['route']=r.Gender+' · '+r.feature
    charts.append(px.line(r,x='Season',y='training_correlation',color='route',markers=True,hover_data=['closest_control'],title='Training-only overlap: highest absolute correlation with an existing control'))
    for f in charts:f.update_layout(height=460,margin={'l':65,'r':35,'t':85,'b':85},legend_title_text='')
    return charts


def render(run:Path,evidence:Path):
    run=Path(run);figs=figures(run,evidence)
    intro='<h1>March Mania · Possession-accounting feature investigation</h1><p>Exploratory historical comparisons. No leaderboard improvement is established. Negative Brier differences favor inclusion. The primary comparison includes ordinary rate controls on both sides.</p>'
    body=[intro]
    for i,f in enumerate(figs):body.append(f.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    body.append('<h2>All measured scores</h2>'+read(run/'metrics.csv').round(7).to_html(index=False,escape=True))
    body.append('<h2>Compute-allocation decisions (not significance tests)</h2><pre>'+__import__('html').escape((run/'decisions.json').read_text())+'</pre>')
    html='<!doctype html><html><head><meta charset="utf-8"><title>Possession features</title><style>body{font-family:system-ui;max-width:1250px;margin:36px auto;padding:20px}table{border-collapse:collapse}td,th{padding:8px}pre{white-space:pre-wrap}</style></head><body>'+''.join(body)+'</body></html>'
    path=run/'possession_evidence.html';tmp=path.with_suffix('.html.partial');tmp.write_text(html);tmp.replace(path)
    return path
