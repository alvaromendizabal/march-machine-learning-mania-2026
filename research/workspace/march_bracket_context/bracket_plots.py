"""Plotly evidence without pandas Styler/Jinja2; no training or external requests."""
from __future__ import annotations
from pathlib import Path
import html
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from bracket_io import read_csv, read_json, require


def figures(out:Path,evidence:Path):
    out=Path(out);evidence=Path(evidence)
    metrics=read_csv(out/'metrics.csv');eff=read_csv(out/'ablations.csv');pred=read_csv(out/'predictions.csv')
    prior=read_csv(evidence/'ablations.csv').query("comparison=='mechanism_given_rates'")
    fs=[]
    fs.append(px.bar(prior,x='Season',y='delta_brier',color='Gender',barmode='group',title='08 · Previous nonlinear possession features: incremental Brier (positive = worse)'))
    # Context depends on pairs, not outcomes: inspect the complete 2019 announced field.
    context=read_csv(out/'snapshots/W_2019/context.csv')
    mat=context.groupby(['seed_A','seed_B']).eligibility_contrast.mean().unstack().reindex(index=range(1,17),columns=range(1,17))
    fs.append(go.Figure(go.Heatmap(x=mat.columns,y=mat.index,z=mat.to_numpy(),colorbar={'title':'Mean signed eligibility'})).update_layout(title='Announced-bracket eligibility by seed pairing · all 2019 pairs',xaxis_title='Team B seed',yaxis_title='Team A seed'))
    coverage=read_csv(out/'coverage.csv')
    fs.append(px.bar(coverage,x='Season',y=['same_pod_pairs','eligible_pairs'],barmode='group',title='All possible pairs: policy-era eligibility is not actual home status'))
    fs.append(px.line(metrics,x='Season',y='brier',color='recipe',markers=True,title='Women · unchanged classifier · Brier by season'))
    fs.append(px.bar(eff.query("comparison in ['host_given_status','scaled_given_status']"),x='Season',y='delta_brier',color='comparison',barmode='group',title='Primary evidence: bracket features beyond top-four status (negative = better)'))
    fs.append(px.bar(eff,x='Season',y='delta_brier',color='comparison',barmode='group',title='Fixed-set feature additions and component removal effects'))
    cohort=read_csv(out/'cohort_metrics.csv')
    w=cohort.pivot(index=['Season','cohort'],columns='recipe',values='brier').reset_index()
    w['delta']=w.host_context_scaled-w.seed_status
    fs.append(px.bar(w,x='Season',y='delta',color='cohort',barmode='group',title='Where added loss changed: bracket-derived cohorts (descriptive, not causal)'))
    rel=[]
    for recipe,g in pred.groupby('recipe',sort=False):
        h=g.assign(bin=np.minimum((g.probability*8).astype(int),7)).groupby('bin').agg(probability=('probability','mean'),observed=('y','mean'),games=('y','size')).reset_index()
        h['recipe']=recipe;rel.append(h)
    fs.append(px.scatter(pd.concat(rel),x='probability',y='observed',size='games',color='recipe',title='Calibration · pooled historical games · sparse bins are uncertain',range_x=[0,1],range_y=[0,1]))
    fs[-1].add_shape(type='line',x0=0,y0=0,x1=1,y1=1,line={'dash':'dash'})
    coeff=read_csv(out/'coefficients.csv').query("recipe=='host_context_scaled'")
    coeff=coeff.loc[coeff.feature.isin(['diff_top4_status','host_eligibility_contrast','host_eligibility_volatility_scaled'])]
    fs.append(px.bar(coeff,x='Season',y='standardized_coefficient',color='feature',barmode='group',title='Training-fitted coefficients · no causal interpretation'))
    overlap=read_csv(out/'training_overlap.csv')
    fs.append(px.bar(overlap,x='Season',y='training_correlation',color='feature',barmode='group',hover_data=['closest_control'],title='Training-only correlation with the closest existing input'))
    for f in fs:
        f.update_layout(height=470,margin={'l':60,'r':40,'t':85,'b':70},legend={'orientation':'h','y':-.22},font={'size':13})
    require(len(fs)==10,'Unexpected figure count')
    return fs


def render(out,evidence):
    fs=figures(out,evidence);summary=read_json(Path(out)/'summary.json')
    parts=['<!doctype html><html><head><meta charset="utf-8"><title>March Mania | Bracket context</title>',
           '<style>body{font:16px system-ui;max-width:1250px;margin:45px auto;padding:0 25px}h1{font-size:36px}section{margin:38px 0}table{border-collapse:collapse;font-size:14px}td,th{padding:8px;border-bottom:1px solid}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style></head><body>',
           '<h1>Women’s bracket context</h1><p>Round 09 · eligibility proxy, not actual venue. No leaderboard improvement is inferred from historical results.</p>',
           '<p>Primary: host_context_scaled − seed_status. Discovery and repeated testing limit all conclusions. Negative Brier changes favor inclusion.</p>',
           '<pre>'+html.escape(__import__('json').dumps(summary,indent=2))+'</pre>']
    for i,f in enumerate(fs):parts.append('<section>'+f.to_html(full_html=False,include_plotlyjs=True if i==0 else False)+'</section>')
    for n in ['metrics.csv','ablations.csv','support_by_fold.csv']:
        parts+=['<h2>'+html.escape(n)+'</h2>',read_csv(Path(out)/n).to_html(index=False,escape=True)]
    parts.append('</body></html>');path=Path(out)/'bracket_context.html';require(not path.is_symlink(),'Unsafe HTML output')
    temp=path.with_suffix('.html.partial');require(not temp.is_symlink(),'Unsafe HTML temporary path');temp.write_text(''.join(parts));temp.replace(path)
    return path
