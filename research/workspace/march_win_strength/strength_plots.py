"""Plotly-only evidence; no optional pandas Styler/Jinja dependency."""
from __future__ import annotations
import html
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from strength_io import read_csv, read_json, require


def figures(run, evidence):
    run, evidence = Path(run), Path(evidence)
    previous = read_csv(evidence/'ablations.csv').query("comparison=='scaled_given_status'")
    team = read_csv(run/'team_profiles.csv')
    last = team.loc[team.Season.eq(2019)].copy()
    last['regular_win_rate'] = last.regular_wins / last.regular_games
    rating = read_csv(run/'rating_diagnostics.csv')
    pair = read_csv(run/'pair_diagnostics.csv').query('Season==2019')
    metrics = read_csv(run/'metrics.csv'); eff = read_csv(run/'ablations.csv')
    cal = read_csv(run/'calibration.csv'); overlap = read_csv(run/'training_overlap.csv')
    plots = [px.bar(previous, x='Season', y='delta_brier',
        title='Preserved round09 result · bracket features beyond seed-status control',
        labels={'delta_brier':'Brier change (lower is better)'})]
    plots.append(px.scatter(last, x='regular_win_rate', y='bt_ability', hover_name='TeamID',
        hover_data=['regular_games','unique_opponents','seed'],
        title='2019 pre-tournament · win percentage versus schedule-adjusted win ability'))
    plots.append(px.scatter(last, x='strength', y='bt_ability', hover_name='TeamID', hover_data=['seed'],
        title='2019 pre-tournament · cached margin strength versus win-loss strength'))
    plots.append(px.scatter(team, x='unique_opponents', y='bt_marginal_sd', color='Season',
        hover_data=['TeamID','regular_games'],
        title='Model-conditional rating uncertainty and schedule support',
        labels={'bt_marginal_sd':'Approximate marginal posterior SD'}))
    plots.append(px.line(rating, x='Season', y='home_logodds', markers=True,
        title='Estimated regular-season home effect · not an added tournament feature'))
    plots.append(px.line(metrics, x='Season', y='brier', color='recipe', markers=True,
        title='Men · fixed-recipe Brier on repeatedly-used historical seasons'))
    plots.append(px.bar(eff, x='Season', y='delta_brier', color='comparison', barmode='group',
        title='Controlled contributions · ability, uncertainty conditional on ability, and combined',
        labels={'delta_brier':'Brier change (lower is better)'}))
    pair = pair.copy()
    pair['uncertainty_correction'] = np.log(pair.bt_averaged_probability/(1-pair.bt_averaged_probability)) - pair.bt_logodds_difference
    plots.append(px.scatter(pair, x='bt_logodds_difference', y='uncertainty_correction', color='pair_variance',
        title='2019 potential pairings · approximate uncertainty correction, no outcome conditioning',
        hover_data=['Team1ID','Team2ID']))
    f=px.line(cal, x='mean_probability', y='observed_fraction', color='recipe', markers=True,
        hover_data=['games'], title='Historical reliability · sparse bins are descriptive, not proof')
    f.add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Ideal reference'))
    plots.append(f)
    plots.append(px.bar(overlap, x='Season', y='training_correlation', color='feature',barmode='group',
        hover_data=['closest_reference'], title='Training-only overlap with existing reference inputs'))
    require(len(plots)==10,'Unexpected chart count')
    for f in plots:
        f.update_layout(height=440,margin=dict(l=65,r=30,t=90,b=65),legend_title_text='Configuration')
    return plots


def render(run, evidence):
    run=Path(run); charts=figures(run,evidence)
    body=['<!doctype html><html><head><meta charset="utf-8"><title>March Mania · Win-loss strength research</title>',
       '<style>body{font-family:Arial,sans-serif;max-width:1200px;margin:36px auto;line-height:1.5}h1{font-size:30px}pre{white-space:pre-wrap}table{border-collapse:collapse}td,th{padding:8px;text-align:right}section{margin:32px 0}</style></head><body>',
       '<h1>March Mania · Joint win-loss strength and rating uncertainty</h1>',
       '<p>Milestone 10 · Historical exploratory feature test, not a leaderboard result. Ratings use only pre-cutoff regular-season wins, losses and venue. The tournament classifier is fixed.</p>',
       '<h2>Measured decisions</h2><pre>'+html.escape(__import__('json').dumps(read_json(run/'decisions.json'),indent=2))+'</pre>']
    for i,f in enumerate(charts):body.append('<section>'+f.to_html(full_html=False,include_plotlyjs=True if i==0 else False)+'</section>')
    body += ['<h2>Metrics</h2>', read_csv(run/'metrics.csv').round(7).to_html(index=False),
      '<p>Laplace and stationarity assumptions limit the uncertainty interpretation. No feature is automatically promoted. Review later-era and production-recipe transfer before a submission claim.</p></body></html>']
    p=run/'win_strength_evidence.html';tmp=p.with_suffix('.html.partial')
    require(not p.is_symlink() and not tmp.is_symlink(),'Unsafe HTML output')
    tmp.write_text('\n'.join(body));tmp.replace(p)
    return p
