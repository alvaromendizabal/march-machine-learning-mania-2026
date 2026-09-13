"""Ten inline/exportable Plotly figures; no fitted models are loaded for reporting."""
from pathlib import Path
import html,json
import pandas as pd
import plotly.express as px
import plotly.io as pio

TITLES={'20':'Pace and shot-variance context','21':'Responses to similar opponent styles'}
def figures(run, rid, evidence):
    run=Path(run); evidence=Path(evidence)
    read=lambda n:pd.read_csv(run/n)
    m=read('metrics.csv');effect=read('ablations.csv');cov=read('coverage.csv');prof=read('profiles.csv')
    previous=[]
    for r in ['17','18','19']:
        d=json.loads((evidence/f'round{r}/decisions.json').read_text())
        previous.append({'round':r,'mean_delta':d['mean_delta'],'decision':d['decision']})
    figs=[px.bar(pd.DataFrame(previous),x='round',y='mean_delta',hover_data=['decision'],title='Previous findings: primary Brier change (negative is better)',labels={'mean_delta':'Mean Brier change','round':'Round'})]
    figs.append(px.line(cov,x='Season',y='minimum_support',markers=True,title='Minimum feature support across potential seeded matchups',labels={'minimum_support':'Detailed games (20) / weighted opponents (21)'}))
    p=prof.loc[prof.Season.eq(2025)&prof.seed.notna()]
    x,y=('pace_mean','shot_variance') if rid=='20' else ('three_share','forced_turnovers')
    figs.append(px.scatter(p,x=x,y=y,hover_data=['TeamID','seed','strength'],title='2025 pre-tournament team profiles — inputs, not predictions',labels={'pace_mean':'Possessions per 40 minutes','shot_variance':'FG-point variance proxy','three_share':'Three-point attempt share','forced_turnovers':'Opponent turnovers / possession'}))
    figs.append(px.line(m,x='Season',y='brier',color='recipe',markers=True,title='All fixed configurations: exploratory validation Brier',labels={'brier':'Brier score (lower is better)'}))
    primary=effect.loc[effect.comparison.eq('context_given_controls')]
    figs.append(px.bar(primary,x='Season',y='delta_brier',title='Primary: both context families beyond descriptive controls',labels={'delta_brier':'Paired season Brier change'}))
    figs.append(px.bar(effect.loc[effect.comparison.eq('both_given_duplicate')],x='Season',y='delta_brier',title='Sensitivity: context representation versus duplicate-input control',labels={'delta_brier':'Brier change'}))
    keep=effect.loc[~effect.comparison.isin(['rates_given_reference','both_given_reference','duplicate_given_rates'])]
    figs.append(px.bar(keep,x='comparison',y='delta_brier',color=keep.Season.astype(str),barmode='group',title='Controlled family additions and removals',labels={'color':'Season','delta_brier':'Brier change'}))
    overlap=read('training_overlap.csv')
    figs.append(px.bar(overlap,x='feature',y='abs_correlation',color=overlap.Season.astype(str),barmode='group',hover_data=['closest_reference_or_rate','training_nonzero'],title='Training-only overlap with reference and control inputs',labels={'abs_correlation':'Largest absolute Pearson correlation','color':'Validation season (training is earlier)'}))
    cal=read('calibration.csv')
    fig=px.line(cal,x='mean_probability',y='observed_fraction',color='recipe',markers=True,hover_data=['games'],title='Pooled exploratory reliability; small bins are descriptive',labels={'mean_probability':'Mean forecast probability','observed_fraction':'Observed fraction'})
    fig.add_shape(type='line',x0=0,y0=0,x1=1,y1=1,line={'dash':'dash'});figs.append(fig)
    co=read('coefficients.csv'); co=co.loc[co.recipe.eq('both')]
    registry=read('feature_registry.csv');new=registry.loc[registry.new_candidate.astype(str).str.lower().eq('true'),'feature']
    figs.append(px.bar(co.loc[co.feature.isin(new)],x='feature',y='coefficient',color=co.loc[co.feature.isin(new),'Season'].astype(str),barmode='group',title='Candidate coefficient stability (train-scaled, not causal)',labels={'color':'Season'}))
    for f in figs:f.update_layout(height=480,margin=dict(l=65,r=30,t=80,b=120),legend_title_text='Configuration / season')
    return figs

def render(run,rid,evidence):
    run=Path(run);fs=figures(run,rid,evidence)
    summary=json.loads((run/'summary.json').read_text())
    metrics=pd.read_csv(run/'metrics.csv')
    pieces=['<!doctype html><html><head><meta charset="utf-8"><title>March Mania Research</title></head><body style="font-family:Arial;max-width:1200px;margin:40px auto">',f'<h1>Round {rid}: {html.escape(TITLES[rid])}</h1>', '<p>Exploratory reused 2022–2025 history. No leaderboard or production-transfer claim.</p>',f'<pre>{html.escape(json.dumps(summary["decision"],indent=2))}</pre>',metrics[['Season','recipe','brier','log_loss']].to_html(index=False,float_format=lambda x:f'{x:.7f}')]
    for i,f in enumerate(fs):pieces.append(pio.to_html(f,full_html=False,include_plotlyjs=True if i==0 else False))
    pieces.append('</body></html>');dest=run/'results.html';temp=dest.with_suffix('.html.partial')
    if dest.is_symlink() or temp.is_symlink():raise ValueError('Unsafe HTML output')
    temp.write_text('\n'.join(pieces));temp.replace(dest);return dest
