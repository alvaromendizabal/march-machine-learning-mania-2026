"""Plotly evidence: replication first, no decorative performance claims."""
from __future__ import annotations
from pathlib import Path
import json
import html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def figures(run: Path, evidence: Path):
    run,evidence=Path(run),Path(evidence)
    old=pd.read_csv(evidence/'metrics.csv');m=pd.read_csv(run/'metrics.csv');a=pd.read_csv(run/'ablations.csv')
    oldwide=old.pivot(index='Season',columns='recipe',values='brier')
    discovery=pd.DataFrame({'Season':oldwide.index,'delta_brier':oldwide.anchor_consensus-oldwide.anchor,
                            'era':'2016–2019 discovery (excluded from gate)'}).reset_index(drop=True)
    later=a[['Season','delta_brier']].copy();later['era']='2022–2025 replication'
    eras=pd.concat([discovery,later],ignore_index=True);eras['Season']=eras.Season.astype(str)
    plots=[px.bar(eras,x='Season',y='delta_brier',color='era',barmode='group',
                  title='01 · Consensus contribution: discovery and later years are separate',labels={'delta_brier':'Brier change; lower is better'})]
    plots.append(px.line(m,x='Season',y='brier',color='recipe',markers=True,title='02 · Later-era Brier: unchanged classifier, one feature difference'))
    panel=pd.read_csv(run/'panel_coverage.csv')
    plots.append(px.bar(panel,x='Season',y='systems',hover_data=['teams','min_publication_day','max_publication_day'],title='03 · Number and publication dates of available ranking systems'))
    cov=pd.read_csv(run/'coverage.csv')
    plots.append(px.bar(cov,x='Season',y='minimum_common_systems',title='04 · Minimum shared-system support over all potential seeded pairs'))
    profile=pd.read_csv(run/'team_profiles.csv');latest=profile.loc[profile.Season.eq(2025)].copy()
    plots.append(px.scatter(latest,x='strength',y='consensus_percentile',hover_data=['TeamID','seed','system_count'],
                   title='05 · 2025 input profiles: margin strength versus ranking consensus'))
    cal=pd.read_csv(run/'calibration.csv')
    fig=px.line(cal,x='mean_probability',y='observed_fraction',color='recipe',markers=True,hover_data=['games'],title='06 · Later-era calibration; pooled descriptive bins')
    fig.add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Ideal calibration'));plots.append(fig)
    coeff=pd.read_csv(run/'coefficients.csv');coeff=coeff.loc[coeff.feature.eq('diff_rank_consensus_logit')]
    plots.append(px.bar(coeff,x='Season',y='standardized_coefficient',title='07 · Consensus coefficient fitted using earlier seasons only'))
    ov=pd.read_csv(run/'training_overlap.csv')
    plots.append(px.bar(ov,x='Season',y='training_correlation',hover_data=['closest_reference'],title='08 · Training-only overlap with the closest reference input'))
    bins=pd.read_csv(run/'paired_loss_bins.csv')
    plots.append(px.bar(bins,x='confidence_bin',y='total_delta',hover_data=['games','mean_delta'],title='09 · Added loss by reference-probability bin; negative is better'))
    sensitivity=pd.read_csv(run/'season_sensitivity.csv');sensitivity['omitted_season']=sensitivity.omitted_season.astype(str)
    plots.append(px.bar(sensitivity,x='omitted_season',y='remaining_mean_delta',title='10 · Does one season dominate the average contribution?'))
    for f in plots:
        if f.layout.xaxis.title.text == 'Season':
            f.update_xaxes(dtick=1, tickformat='d')
        f.update_layout(font={'family':'Arial','size':14},title={'font':{'size':19}},height=510,margin={'l':60,'r':35,'t':90,'b':65},legend={'orientation':'h','y':1.1})
    return plots


def render(run: Path,evidence: Path):
    run=Path(run);plots=figures(run,evidence);summary=json.loads((run/'summary.json').read_text());d=summary['decision']
    texts=['<!doctype html><html><head><meta charset="utf-8"><title>March Mania · Consensus replication</title>',
           '<style>body{font-family:Arial,sans-serif;max-width:1150px;margin:40px auto;line-height:1.6;padding:0 24px}h1{font-size:34px}table{border-collapse:collapse;width:100%}th,td{padding:9px;border-bottom:1px solid;text-align:right}.chart{margin:35px 0}pre{white-space:pre-wrap}</style></head><body>',
           '<p>FEATURE EVIDENCE / MILESTONE 13</p><h1>Does ranking consensus survive later seasons?</h1>',
           '<p><strong>Exploratory 2022–2025 main-draw results.</strong> These years were already used elsewhere in the project. This is neither untouched testing nor a leaderboard score. No new feature definitions or production-model changes.</p>',
           '<h2>'+html.escape(d['decision'])+'</h2>',
           f'<p>Mean Brier change: {d["mean_delta"]:+.7f}. Improved seasons: {d["improved_seasons"]}/4. No automatic promotion.</p>',
           pd.read_csv(run/'metrics.csv')[['Season','recipe','games','train_games','brier','log_loss','delta_vs_anchor']].to_html(index=False,border=0,float_format=lambda x:f'{x:.7f}'),
           '<h2>Training-label audit</h2><p>First Four games are identified by matching seed stems; the 2021 no-contest is excluded. No 2020 or 2026 labels enter fitting.</p>',
           pd.read_csv(run/'label_audit.csv')[['Season','first_four_excluded','no_contest_rows_excluded','played_main_draw_games','main_draw_min_day']].rename(columns={'first_four_excluded':'First Four excluded','no_contest_rows_excluded':'Administrative rows excluded','played_main_draw_games':'Played main-draw games','main_draw_min_day':'First main-draw day'}).to_html(index=False,border=0)]
    for i,f in enumerate(plots):texts.append('<section class="chart">'+f.to_html(full_html=False,include_plotlyjs=True if i==0 else False)+'</section>')
    texts+=['<h2>Limits and provenance</h2><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre></body></html>']
    out=run/'results.html';temp=out.with_suffix('.html.partial');temp.write_text('\n'.join(texts));temp.replace(out)
    return out
