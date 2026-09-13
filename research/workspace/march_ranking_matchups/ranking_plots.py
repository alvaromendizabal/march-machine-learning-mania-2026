"""Ten Plotly figures and a self-contained report. No Styler/Jinja2 dependency."""
from __future__ import annotations
import html,json
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from research_io import read_csv,read_json,require


def figures(run: Path, evidence: Path) -> list:
    run=Path(run); evidence=Path(evidence)
    old=read_csv(evidence/'ablations.csv')
    panels=read_csv(run/'panel_coverage.csv'); support=read_csv(run/'pair_support.csv')
    teams=read_csv(run/'team_profiles.csv').query('Season==2019')
    pairs=read_csv(run/'snapshots/M_2019/matchups.csv')
    metrics=read_csv(run/'metrics.csv'); effects=read_csv(run/'ablations.csv')
    cal=read_csv(run/'calibration.csv'); overlap=read_csv(run/'training_overlap.csv')
    plots=[
      px.bar(old.query("comparison in ['huber_given_anchor','compression_given_huber']"),x='Season',y='delta_brier',color='comparison',barmode='group',title='Milestone 11 · neither declared comparison passed its gate'),
      px.bar(panels,x='Season',y='systems',hover_data=['max_publication_day','oldest_edition_age','observations'],title='Legal ranking editions · no post-day-132 information'),
      px.box(support,x='Season',y='common_systems',points=False,title='Shared-system support · counts are not independent evidence'),
      px.scatter(teams,x='strength',y='consensus_percentile',hover_name='TeamID',hover_data=['seed','system_count','rank_iqr'],title='2019 inputs · internal margin strength versus published consensus'),
      px.scatter(pairs,x='diff_rank_consensus_logit',y='pair_rank_median_residual',hover_data=['Team1ID','Team2ID','pair_rank_vote_logit'],title='All possible 2019 field pairs · matched-system residual, without outcomes'),
      px.line(metrics,x='Season',y='brier',color='recipe',markers=True,title='Fixed classifier · repeatedly-used historical main-draw games'),
      px.bar(effects.query("comparison=='pairwise_given_consensus'"),x='Season',y='delta_brier',title='Primary · two matchup features beyond the consensus control'),
      px.bar(effects.query("comparison!='pairwise_given_consensus'"),x='Season',y='delta_brier',color='comparison',barmode='group',title='Controlled add/drop comparisons · separate established-control effects'),
      px.line(cal,x='mean_probability',y='observed_fraction',color='recipe',markers=True,hover_data=['games'],title='Calibration · descriptive pooled historical bins'),
      px.bar(overlap,x='Season',y='training_correlation',color='feature',barmode='group',hover_data=['closest_reference'],title='Training-only overlap with the reference and consensus control'),
    ]
    plots[8].add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Ideal reference'))
    for fig in plots:fig.update_layout(height=485,margin=dict(l=65,r=40,t=95,b=75))
    return plots


def render(run: Path,evidence: Path) -> Path:
    run=Path(run); charts=figures(run,evidence)
    body=['<!doctype html><html><head><meta charset="utf-8"><title>March Mania · Shared-system ranking matchups</title>',
      '<style>body{font-family:Arial,sans-serif;max-width:1240px;margin:36px auto;padding:0 20px;line-height:1.55}h1{font-size:30px}pre{white-space:pre-wrap}table{border-collapse:collapse}td,th{padding:8px;text-align:right}section{margin:32px 0}</style></head><body>',
      '<h1>March Mania · Shared-system ranking matchups</h1><p>Milestone 12. An established consensus control and two matchup-level hypotheses. No new rating fits, no tournament-algorithm search.</p>',
      '<p>Repeatedly-used 2016–2019 validation; not an untouched test, a leaderboard improvement, or a reproduction of the production model. System votes are correlated and are not win probabilities.</p>',
      '<h2>Decision</h2><pre>'+html.escape(json.dumps(read_json(run/'decisions.json'),indent=2))+'</pre>']
    for i,fig in enumerate(charts):body.append('<section>'+fig.to_html(full_html=False,include_plotlyjs=True if i==0 else False)+'</section>')
    body+=['<h2>Measured historical scores</h2>',read_csv(run/'metrics.csv').round(7).to_html(index=False),
       '<h2>Publication coverage</h2>',read_csv(run/'panel_coverage.csv').to_html(index=False),
       '<p>Any favorable result requires later-era checks and transfer to a stronger fixed production recipe. No automatic feature promotion.</p></body></html>']
    path=run/'ranking_evidence.html';tmp=path.with_suffix('.html.partial')
    require(not path.is_symlink() and not tmp.is_symlink(),'Unsafe HTML output')
    tmp.write_text('\n'.join(body));tmp.replace(path);return path
