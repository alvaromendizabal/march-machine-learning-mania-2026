"""Interactive evidence, independent of pandas Styler/Jinja2."""
from __future__ import annotations
import html,json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from research_io import read_csv,read_json,require


def figures(run,evidence):
    run=Path(run);evidence=Path(evidence)
    old=read_csv(evidence/'log_metrics.csv')
    old=old.merge(old.query("recipe=='anchor'")[['Season','brier']].rename(columns={'brier':'baseline'}),on='Season')
    old['delta']=old.brier-old.baseline
    m=np.linspace(-60,60,241)
    curves=pd.DataFrame({'margin':m,'unchanged':m,'compressed':15*np.tanh(m/15)})
    psi=pd.DataFrame({'residual':m,'squared_error':m,'huber':np.clip(m,-15,15)})
    trace=read_csv(run/'optimization_trace.csv');trace['fit']=trace.Season.astype(str)+' '+trace.kind
    team=read_csv(run/'team_profiles.csv').query('Season==2019')
    metrics=read_csv(run/'metrics.csv');eff=read_csv(run/'ablations.csv');cal=read_csv(run/'calibration.csv')
    overlap=read_csv(run/'training_overlap.csv')
    plots=[px.bar(old.query("recipe!='anchor'"),x='Season',y='delta',color='recipe',barmode='group',
        title='Completed round10 · no feature passed the declared expansion rule'),
      px.line(curves,x='margin',y=['unchanged','compressed'],title='Observed-margin compression · separate hypothesis'),
      px.line(psi,x='residual',y=['squared_error','huber'],title='Huber limits large residual influence, not large margins themselves'),
      px.line(trace.query("kind=='huber'"),x='iteration',y='gradient_max_abs',color='fit',log_y=True,
        title='Numerical certificates · bounded robust fits'),
      px.scatter(team,x='strength',y='huber_margin_strength',hover_name='TeamID',hover_data=['seed','compressed_margin_strength'],
        title='2019 seeded teams · raw versus residual-robust strength'),
      px.line(metrics,x='Season',y='brier',color='recipe',markers=True,title='Men · fixed tournament recipe, reused historical seasons'),
      px.bar(eff.query("comparison=='huber_given_anchor'"),x='Season',y='delta_brier',title='Primary: robust margin feature beyond the reference'),
      px.bar(eff.query("comparison!='huber_given_anchor'"),x='Season',y='delta_brier',color='comparison',barmode='group',
        title='Secondary controlled comparisons · no replacement of a failed primary'),
      px.line(cal,x='mean_probability',y='observed_fraction',color='recipe',markers=True,hover_data=['games'],
        title='Calibration · pooled historical bins, not independent trials'),
      px.bar(overlap,x='Season',y='training_correlation',color='feature',barmode='group',hover_data=['closest_reference'],
        title='Training-only overlap with existing inputs')]
    plots[8].add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Ideal reference'))
    for f in plots:f.update_layout(height=470,margin=dict(l=65,r=35,t=95,b=70))
    return plots


def render(run,evidence):
    run=Path(run);charts=figures(run,evidence)
    body=['<!doctype html><html><head><meta charset="utf-8"><title>March Mania · Margin robustness</title>',
      '<style>body{font-family:Arial,sans-serif;max-width:1240px;margin:36px auto;line-height:1.55}h1{font-size:30px}pre{white-space:pre-wrap}table{border-collapse:collapse}td,th{padding:8px;text-align:right}section{margin:32px 0}</style></head><body>',
      '<h1>March Mania · Margin robustness</h1><p>Milestone 11. Two representation hypotheses. No tournament-algorithm search. Repeatedly used historical seasons; not a leaderboard improvement.</p>',
      '<p>Unusual residuals are not confirmed bad data. Capping may discard genuine signal. Neither hypothesis is assumed to succeed.</p>',
      '<h2>Decisions</h2><pre>'+html.escape(json.dumps(read_json(run/'decisions.json'),indent=2))+'</pre>']
    for i,f in enumerate(charts):body.append('<section>'+f.to_html(full_html=False,include_plotlyjs=(True if i==0 else False))+'</section>')
    body += ['<h2>Actual metrics</h2>',read_csv(run/'metrics.csv').round(7).to_html(index=False),
      '<h2>Numerical diagnostics</h2>',read_csv(run/'rating_diagnostics.csv').to_html(index=False),
      '<p>Potential follow-up requires stability and transfer to a stronger fixed production recipe. No automatic promotion.</p></body></html>']
    p=run/'margin_evidence.html';tmp=p.with_suffix('.html.partial')
    require(not p.is_symlink() and not tmp.is_symlink(),'Unsafe HTML output')
    tmp.write_text('\n'.join(body));tmp.replace(p);return p
