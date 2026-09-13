"""Plotly evidence for the shooting research round. Report rendering never trains."""
from __future__ import annotations
import html
import json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from shot_features import ALL_FEATURES,RESIDUAL_COLS,PROFILE_COLS


def figures(directory:Path,phase:str) -> list:
    directory=Path(directory)
    reg=pd.read_csv(directory/'feature_registry.csv')
    metrics=pd.read_csv(directory/f'{phase}_metrics.csv')
    agg=pd.read_csv(directory/f'{phase}_aggregate.csv')
    abl=pd.read_csv(directory/f'{phase}_ablations.csv')
    latest=int(metrics.Season.max())
    teams=pd.concat([pd.read_csv(directory/'snapshots'/f'{g}_{latest}'/'teams.csv') for g in ('M','W')],ignore_index=True)
    teams=teams.loc[teams.seed.notna()].copy()
    figs=[]
    fig=px.bar(reg.groupby('family').size().rename('features').reset_index(),x='family',y='features',
               text='features',title='Representation under test · 16 control features + 14 new candidates')
    figs.append(fig)
    fig=px.scatter(teams,x='profile_two_offense',y='profile_three_offense',color='Gender',
                   hover_data=['TeamID','seed','detailed_games'],
                   title=f'{latest} seeded teams · opponent-adjusted shooting profiles',
                   labels={'profile_two_offense':'Adjusted 2P offensive effect (probability units)',
                           'profile_three_offense':'Adjusted 3P offensive effect (probability units)'})
    figs.append(fig)
    fig=px.scatter(teams,x='schedule_three_accuracy',y='opp_three_posterior',color='Gender',
                   size='detailed_games',hover_data=['TeamID','seed','resid_three_pp100'],
                   title=f'{latest} · opponent shooting environment versus observed defense',
                   labels={'schedule_three_accuracy':'Expected opponent 3P% (all head-to-head meetings excluded)',
                           'opp_three_posterior':'Observed opponent 3P% (standard shrunk control)'})
    fig.add_shape(type='line',x0=.20,y0=.20,x1=.50,y1=.50,line={'dash':'dot'})
    figs.append(fig)
    visible=agg.loc[agg.Gender.isin(['M','W'])]
    fig=px.bar(visible,x='recipe',y='mean_season_brier',color='Gender',barmode='group',
               hover_data=['games','seasons','game_weighted_brier'],
               title='Historical main-draw Brier · lower is better; not the 2026 leaderboard')
    fig.update_yaxes(rangemode='tozero')
    figs.append(fig)
    deltas=metrics.loc[metrics.recipe!='anchor'].copy()
    deltas['route']=deltas.Gender+' · '+deltas.recipe
    fig=px.line(deltas,x='Season',y='delta_vs_anchor',color='route',markers=True,
                title='Paired changes from the identical reference · negative favors new features')
    fig.add_hline(y=0,line_dash='dot')
    fig.update_xaxes(dtick=1)
    figs.append(fig)
    abl['fold']=abl.Gender+' '+abl.Season.astype(str)
    pivot=abl.pivot(index='comparison',columns='fold',values='delta_brier')
    fig=px.imshow(pivot,aspect='auto',text_auto='.4f',
                  title='Controlled add/drop comparisons · fixed feature sets, no capacity replacements')
    figs.append(fig)
    for gender in ('M','W'):
        parts=[]
        for _,row in metrics.loc[metrics.Gender==gender].iterrows():
            f=directory/'fits'/f'{gender}_{int(row.Season)}_{row.recipe}'/'predictions.csv'
            pred=pd.read_csv(f);pred['recipe']=row.recipe;parts.append(pred)
        pred=pd.concat(parts,ignore_index=True)
        pred['bin']=np.minimum((pred.probability*10).astype(int),9)
        cal=pred.groupby(['recipe','bin']).agg(mean_probability=('probability','mean'),
                  observed_rate=('y','mean'),games=('y','size')).reset_index()
        fig=px.scatter(cal,x='mean_probability',y='observed_rate',color='recipe',size='games',
                       hover_data=['games','bin'],
                       title=f'{gender} reliability · descriptive bins, not a calibrated replacement')
        fig.add_shape(type='line',x0=0,y0=0,x1=1,y1=1,line={'dash':'dot'})
        fig.update_xaxes(range=[0,1]);fig.update_yaxes(range=[0,1])
        figs.append(fig)
    coeff=[]
    for g in ('M','W'):
        model=json.loads((directory/'fits'/f'{g}_{latest}_anchor_both'/'model.json').read_text())
        for i,b in zip(model['active_indices'],model['coefficients']):
            c=model['columns'][i]
            if c in RESIDUAL_COLS+PROFILE_COLS:
                coeff.append({'Gender':g,'feature':c,'standardized_coefficient':b})
    fig=px.bar(pd.DataFrame(coeff),x='standardized_coefficient',y='feature',color='Gender',barmode='group',
               orientation='h',title=f'{latest} fixed-recipe coefficients · diagnostic, not causal importance')
    fig.update_layout(height=650)
    figs.append(fig)
    for fig in figs:
        fig.update_layout(font={'family':'Arial','size':13},margin={'l':65,'r':35,'t':85,'b':80},
                          legend_title_text='',title={'x':.03},hoverlabel={'namelength':-1})
    return figs


def make_report(directory:Path,phase:str) -> Path:
    summary=json.loads((directory/f'{phase}_summary.json').read_text())
    fs=figures(directory,phase)
    head='''<!doctype html><html><head><meta charset="utf-8"><title>March Mania | Shooting Research</title>
<style>body{font:16px/1.6 Arial,sans-serif;max-width:1250px;margin:40px auto;padding:0 25px}h1{font-size:36px;line-height:1.15}section{margin:32px 0;border:1px solid #ddd;border-radius:10px;padding:20px}pre{white-space:pre-wrap;font-size:13px}p{max-width:980px}.tag{font-size:12px;letter-spacing:2px;text-transform:uppercase}footer{margin:40px 0}</style></head><body>'''
    text=head+'<p class="tag">Research round 02 · '+html.escape(phase)+'</p>'
    text+='<h1>Opponent shooting environment<br>and matchup-specific shot profiles</h1>'
    text+='<p>Four fixed logistic recipes; 16 existing-concept control features, 14 new candidates. '
    text+='This report contains retrospective historical measurements, not an official Kaggle score. '
    text+='The submitted reference remains 0.1222672; the historical research target is 0.1097454.</p>'
    text+='<p>Features use regular-season games through day 132 and bracket seeds. Tournament labels are separate. '
    text+='The same train-only scaling, regularization and input-set protocol applies to every comparison. '
    text+='Opponent residuals are not identified causal luck. Previously consumed seasons limit the strength of conclusions.</p>'
    for i,fig in enumerate(fs):
        text+='<section>'+fig.to_html(full_html=False,include_plotlyjs=True if i==0 else False)+'</section>'
    text+='<section><h2>Execution receipt</h2><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre></section>'
    text+='<footer>Source notes and hypotheses are in RESEARCH_PLAN.md. No feature is promoted automatically.</footer></body></html>'
    dest=directory/f'{phase}_report.html'
    dest.write_text(text)
    return dest
