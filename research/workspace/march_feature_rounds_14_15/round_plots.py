"""Ten standalone Plotly figures per independent experiment; no Styler dependency."""
from __future__ import annotations
from pathlib import Path
import html
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import feature_rounds as fr

TITLES={'14':'Ranking resolution and cardinal strength','15':'Common-opponent, same-venue performance'}

def figures(out:Path,round_id:str,evidence:Path):
    def read(n):return pd.read_csv(Path(out)/n)
    prior=pd.read_csv(Path(evidence)/'metrics.csv');prior=prior.query("recipe=='anchor_consensus'")
    m=read('metrics.csv');effects=read('ablations.csv');cov=read('coverage.csv');prof=read('profiles.csv')
    co=read('coefficients.csv');over=read('training_overlap.csv');cal=read('calibration.csv')
    figs=[]
    figs.append(px.bar(prior,x='Season',y='delta_vs_anchor',title='01 | Earlier consensus test — context, not this experiment'))
    figs.append(px.line(m,x='Season',y='brier',color='recipe',markers=True,title='02 | Historical Brier by fixed feature configuration'))
    figs.append(px.bar(effects.query("comparison=='both_given_reference'"),x='Season',y='delta_brier',
                       title='03 | Primary incremental Brier — negative is better'))
    figs.append(px.bar(effects.query("comparison=='both_given_duplicate'"),x='Season',y='delta_brier',
                       title='04 | Both families versus duplicated-input control'))
    ab=effects.loc[~effects.comparison.isin(['both_given_reference','both_given_duplicate','duplicate_given_reference'])]
    figs.append(px.bar(ab,x='Season',y='delta_brier',color='comparison',barmode='group',title='05 | Fixed add/drop family comparisons'))
    if round_id=='14':
        figs.append(px.bar(cov,x='Season',y='seeded_clipped_teams',title='06 | Seeded teams at the previous percentile clip'))
        selected=prof.loc[prof.Season.eq(2025)&prof.seed.notna()]
        figs.append(px.scatter(selected,x='old_logit',y='unclipped_logit',hover_data=['TeamID','seed','systems'],
                     title='07 | 2025 ordinal-tail separation — descriptive inputs only'))
    else:
        cov=cov.melt(id_vars='Season',value_vars=['pairs_with_compact_evidence','pairs_with_detail_evidence'],var_name='support',value_name='supported_pairs')
        figs.append(px.bar(cov,x='Season',y='supported_pairs',color='support',barmode='group',title='06 | Potential pairs with matched opponent and venue evidence'))
        figs.append(px.bar(read('support_diagnostics.csv'),x='support_bin',y='mean_delta',hover_data=['games'],
                     title='07 | Observed loss change by matched-opponent support (descriptive)'))
    overlap=over.pivot(index='feature',columns='Season',values='abs_correlation')
    figs.append(px.imshow(overlap,aspect='auto',zmin=0,zmax=1,text_auto='.2f',
                title='08 | Maximum absolute training-only correlation with reference inputs'))
    figs.append(px.line(cal,x='mean_probability',y='observed_fraction',color='recipe',markers=True,hover_data=['games'],
                title='09 | Calibration — pooled exploratory seasons; sparse bins remain uncertain'))
    figs[-1].add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Perfect calibration'))
    only=co.loc[co.feature.isin(fr.FEATURES[round_id]) & co.recipe.eq('both')]
    figs.append(px.line(only,x='Season',y='coefficient',color='feature',markers=True,
                title='10 | Standardized candidate coefficients in the combined model'))
    for f in figs:
        f.update_layout(height=470,margin=dict(l=65,r=35,t=80,b=70),font=dict(size=13),legend_title_text='')
        if f.layout.xaxis.title and f.layout.xaxis.title.text=='Season':f.update_xaxes(dtick=1)
    for i in [0,1,2,3,4]:figs[i].update_yaxes(tickformat='.5f')
    return figs


def render(out:Path,round_id:str,evidence:Path):
    figs=figures(out,round_id,evidence);summary=json.loads((Path(out)/'summary.json').read_text())
    parts=['<!doctype html><html><head><meta charset="utf-8"><title>March Mania research</title>',
           '<style>body{font-family:Arial,sans-serif;max-width:1120px;margin:40px auto;padding:0 24px;line-height:1.55}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:8px;border-bottom:1px solid #ddd;text-align:right}th:first-child,td:first-child{text-align:left}pre{white-space:pre-wrap}h1{line-height:1.15}section{margin:32px 0}</style></head><body>',
           f'<h1>March Mania · Round {round_id}</h1><h2>{html.escape(TITLES[round_id])}</h2>',
           '<p>Four candidates. Fixed 17-input consensus reference. Two independent families. No automatic feature promotion.</p>',
           '<p><strong>Exploratory 2022–2025 main draw. Not untouched testing, the production model, or the 2026 leaderboard.</strong></p>',
           f'<pre>{html.escape(json.dumps(summary["decision"],indent=2))}</pre>',
           pd.read_csv(Path(out)/'metrics.csv')[['Season','recipe','brier','log_loss','delta_vs_anchor','active_features','source']].to_html(index=False,border=0,float_format=lambda x:f'{x:.7f}',escape=True)]
    for i,f in enumerate(figs):parts.append('<section>'+f.to_html(full_html=False,include_plotlyjs=True if i==0 else False)+'</section>')
    parts.append('<h2>Limits and provenance</h2><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre></body></html>')
    p=Path(out)/f'round_{round_id}_report.html';tmp=p.with_suffix('.html.partial')
    if p.is_symlink() or tmp.is_symlink():raise ValueError('Unsafe HTML output')
    tmp.write_text('\n'.join(parts));tmp.replace(p);return p
