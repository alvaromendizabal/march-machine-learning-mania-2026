"""Plotly diagnostics; figures use saved evidence and never fit a model."""
from __future__ import annotations
import html
import json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px


def figures(directory):
    d=Path(directory);figs=[]
    old=pd.read_csv(d/'prior_replay.csv')
    anchors=old.loc[old.recipe=='anchor',['Gender','brier_replayed']].rename(columns={'brier_replayed':'anchor_brier'})
    old=old.merge(anchors,on='Gender',validate='many_to_one');old['delta']=old.brier_replayed-old.anchor_brier
    figs.append(px.bar(old.loc[old.recipe!='anchor'],x='recipe',y='delta',color='Gender',barmode='group',
                      title='2019 shooting test · every addition worsened Brier',labels={'delta':'Brier change; lower is better'}))
    groups=pd.read_csv(d/'prior_loss_groups.csv')
    figs.append(px.bar(groups,x='anchor_confidence_bin',y='mean_delta',color='recipe',pattern_shape='Gender',
                      barmode='group',hover_data=['games','total_loss_change'],
                      title='2019 diagnosis · where additional loss accumulated',
                      labels={'mean_delta':'Mean paired loss change','anchor_confidence_bin':'Reference confidence bin'}))
    catalog=pd.read_csv(d/'feature_registry.csv')
    counts=catalog.groupby('family').size().rename('features').reset_index()
    figs.append(px.bar(counts,x='family',y='features',text='features',title='2018 experiment · 16 unchanged controls + 7 candidates'))
    teams=pd.concat([pd.read_csv(d/'snapshots'/f'{g}_2018'/'features.csv') for g in ('M','W')])
    teams=teams.loc[teams.seed.notna()]
    figs.append(px.scatter(teams,x='quality_points_won',y='reference_surplus',color='Gender',
                          hover_data=['TeamID','seed','strength','games'],
                          title='2018 seeded teams · quality wins versus reference-team record',
                          labels={'reference_surplus':'Custom reference surplus (NOT official WAB)'}))
    metrics=pd.read_csv(d/'metrics.csv')
    figs.append(px.bar(metrics,x='recipe',y='brier',color='Gender',barmode='group',hover_data=['games','train_games'],
                      title='2018 main-draw Brier · fixed classifier, not the 2026 leaderboard'))
    fig=px.bar(metrics.loc[metrics.recipe!='anchor'],x='recipe',y='delta_vs_anchor',color='Gender',barmode='group',
               title='2018 paired feature contribution · negative means lower Brier')
    fig.add_hline(y=0,line_dash='dot');figs.append(fig)
    abl=pd.read_csv(d/'ablations.csv').pivot(index='comparison',columns='Gender',values='delta_brier')
    figs.append(px.imshow(abl,text_auto='.5f',aspect='auto',title='Controlled add/drop effects · no replacement-feature selection'))
    for gender in ('M','W'):
        parts=[]
        for recipe in metrics.recipe.unique():
            p=pd.read_csv(d/'fits'/f'{gender}_2018_{recipe}'/'predictions.csv');p['recipe']=recipe;parts.append(p)
        p=pd.concat(parts);p['bin']=np.minimum((p.probability*10).astype(int),9)
        cal=p.groupby(['recipe','bin']).agg(mean_probability=('probability','mean'),outcome_rate=('y','mean'),
                                           games=('y','size')).reset_index()
        fig=px.scatter(cal,x='mean_probability',y='outcome_rate',color='recipe',size='games',hover_data=['games','bin'],
                       title=f'{gender} · descriptive 2018 reliability, sparse bins; not recalibration')
        fig.add_shape(type='line',x0=0,y0=0,x1=1,y1=1,line={'dash':'dot'})
        fig.update_xaxes(range=[0,1]);fig.update_yaxes(range=[0,1]);figs.append(fig)
    red=pd.read_csv(d/'training_redundancy.csv')
    figs.append(px.bar(red,x='absolute_correlation',y='feature',color='Gender',orientation='h',barmode='group',
                      hover_data=['most_correlated_anchor'],title='Training-only overlap with existing controls · diagnostic, not automatic selection'))
    for f in figs:
        f.update_layout(font={'family':'Arial','size':13},margin={'l':65,'r':25,'t':90,'b':80},
                        title={'x':.025},legend_title_text='',height=510)
    figs[-1].update_layout(height=650)
    return figs


def make_report(directory):
    d=Path(directory);summary=json.loads((d/'summary.json').read_text());fs=figures(d)
    body='''<!doctype html><html><head><meta charset="utf-8"><title>March Mania | Quality wins and record</title>
<style>body{font:16px/1.65 Arial,sans-serif;max-width:1280px;margin:40px auto;padding:0 24px}h1{font-size:38px;line-height:1.2}section{margin:28px 0;padding:18px;border:1px solid #ddd;border-radius:10px}pre{white-space:pre-wrap;font-size:13px}.tag{font-size:12px;letter-spacing:2px;text-transform:uppercase}td,th{padding:8px}</style></head><body>
<p class="tag">Feature investigation 04 · fixed-recipe historical experiment</p><h1>Quality wins and<br>schedule-adjusted records</h1>
<p>The previous shooting study worsened 2019 Brier. No shooting candidate is promoted. This new experiment holds the 16-input control and classifier fixed, adding two small families individually and together.</p>
<p>2018 is already-consumed exploratory history. This is not a reproduction of the final submitted model. Negative deltas favor inclusion; no single-season result proves future gain. The submitted Brier remains 0.1222672; the research target is 0.1097454.</p>'''
    for i,fig in enumerate(fs):body+='<section>'+fig.to_html(full_html=False,include_plotlyjs=(True if i==0 else False))+'</section>'
    body+='<section><h2>Measured metrics</h2>'+pd.read_csv(d/'metrics.csv').to_html(index=False)+'</section>'
    body+='<section><h2>Receipt and limitations</h2><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre></section>'
    body+='<p>Definitions and source attribution: RESEARCH_PLAN.md. Repository, raw files, and upstream checkpoints are preserved. No automatic submissions or feature promotion.</p></body></html>'
    dest=d/'schedule_report.html';dest.write_text(body)
    return dest
