"""Ten standalone Plotly figures per round; rendered only when the user executes."""
from __future__ import annotations
from pathlib import Path
import html,json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import feature_rounds as fr

TITLES={'18':'Rebounding and assisted-shot structure','19':'Scoring-source dependence'}

def figures(out:Path,round_id:str,evidence:Path):
    def read(n):return pd.read_csv(Path(out)/n)
    m=read('metrics.csv');effects=read('ablations.csv');diag=read('rating_diagnostics.csv')
    profile=read('profiles.csv');over=read('training_overlap.csv');cal=read('calibration.csv');co=read('coefficients.csv')
    previous=[]
    for rid in ['14','15']:
        decision=json.loads((Path(evidence)/f'round{rid}/decisions.json').read_text())
        previous.append({'round':'Round '+rid,'mean Brier change':decision['mean_delta']})
    figs=[px.bar(pd.DataFrame(previous),x='round',y='mean Brier change',
                  title='01 | Preserved negative findings — prior rounds, not new results')]
    figs.append(px.bar(diag,x='Season',y='minimum_seeded_exposure',color='target',barmode='group',
        labels={'minimum_seeded_exposure':'Minimum seeded-team opportunities'},
        title='02 | Rate support — denominators differ by target'))
    t=fr.FAMILIES[round_id][0]
    selected=profile.loc[profile.Season.eq(2025)&profile.seed.notna()].copy()
    figs.append(px.scatter(selected,x=f'rate_{t}_defense',y=f'adjusted_{t}_defense',hover_data=['TeamID','seed'],
        labels={f'rate_{t}_defense':'Raw signed defensive rate per 100',f'adjusted_{t}_defense':'Adjusted defensive effect per 100'},
        title='03 | 2025 raw versus opponent-adjusted profile — not validation'))
    figs.append(px.line(m,x='Season',y='brier',color='recipe',markers=True,
        labels={'brier':'Brier score (lower is better)'},title='04 | All fixed-recipe historical comparisons'))
    figs.append(px.bar(effects.query("comparison=='adjustment_given_rates'"),x='Season',y='delta_brier',
        labels={'delta_brier':'Brier: both families minus direct rates'},title='05 | Primary incremental effect — negative is better'))
    figs.append(px.bar(effects.query("comparison=='both_given_duplicate'"),x='Season',y='delta_brier',
        labels={'delta_brier':'Brier: both families minus duplicate control'},title='06 | Sensitivity to duplicated direct-rate inputs'))
    subset=effects.loc[~effects.comparison.isin(['adjustment_given_rates','both_given_duplicate','duplicate_given_rates','both_given_reference'])]
    figs.append(px.bar(subset,x='Season',y='delta_brier',color='comparison',barmode='group',
        title='07 | Controlled additions and conditional family removals'))
    matrix=over.pivot(index='feature',columns='Season',values='abs_correlation')
    figs.append(px.imshow(matrix,aspect='auto',zmin=0,zmax=1,text_auto='.2f',
        labels={'x':'Validation season (correlations use earlier training games)','y':'Candidate','color':'Absolute correlation'},
        title='08 | Closest training-only correlation with reference or rate controls'))
    figs.append(px.line(cal,x='mean_probability',y='observed_fraction',color='recipe',markers=True,hover_data=['games'],
        labels={'mean_probability':'Mean predicted P(team A wins)','observed_fraction':'Observed win fraction'},
        title='09 | Calibration — pooled exploratory seasons, sparse bins uncertain'))
    figs[-1].add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Perfect calibration'))
    only=co.loc[co.feature.isin(fr.FEATURES[round_id])&co.recipe.eq('both')]
    figs.append(px.line(only,x='Season',y='coefficient',color='feature',markers=True,
        title='10 | Standardized candidate coefficients — diagnostic, not causal'))
    for f in figs:
        f.update_layout(height=485,margin=dict(l=65,r=35,t=85,b=85),font=dict(size=13),legend_title_text='')
        if f.layout.xaxis.title and f.layout.xaxis.title.text=='Season':f.update_xaxes(dtick=1)
    for i in [0,3,4,5,6]:figs[i].update_yaxes(tickformat='.5f')
    return figs

def render(out:Path,round_id:str,evidence:Path):
    fs=figures(out,round_id,evidence);summary=json.loads((Path(out)/'summary.json').read_text())
    styles='body{font-family:Arial,sans-serif;max-width:1180px;margin:40px auto;padding:0 24px;line-height:1.55}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:7px;border-bottom:1px solid #ddd;text-align:right}pre{white-space:pre-wrap}section{margin:35px 0}'
    parts=['<!doctype html><html><head><meta charset="utf-8"><title>March Mania · Research</title>',
        '<style>'+styles+'</style></head><body>',f'<h1>Round {round_id} · {html.escape(TITLES[round_id])}</h1>',
        '<p>Four opponent-adjusted candidates, four direct-rate controls. The 17-input consensus reference is held fixed.</p>',
        '<p><strong>Previously used 2022–2025 men’s main draw; not production, an untouched holdout, or a leaderboard score.</strong></p>',
        '<pre>'+html.escape(json.dumps(summary['decision'],indent=2))+'</pre>',
        pd.read_csv(Path(out)/'metrics.csv')[['Season','recipe','brier','log_loss','delta_vs_anchor','source']].to_html(index=False,border=0,float_format=lambda x:f'{x:.7f}',escape=True)]
    for i,fig in enumerate(fs):parts.append('<section>'+fig.to_html(full_html=False,include_plotlyjs=(i==0))+'</section>')
    for n in ['season_bootstrap.json','prepare.json','evaluation_receipt.json']:
        parts.append('<h2>'+html.escape(n)+'</h2><pre>'+html.escape((Path(out)/n).read_text())+'</pre>')
    parts.append('<h2>Limitations</h2><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre></body></html>')
    dest=Path(out)/f'round_{round_id}_report.html';tmp=dest.with_suffix('.html.partial')
    if dest.is_symlink() or tmp.is_symlink():raise ValueError('Unsafe HTML destination')
    tmp.write_text('\n'.join(parts));tmp.replace(dest);return dest
