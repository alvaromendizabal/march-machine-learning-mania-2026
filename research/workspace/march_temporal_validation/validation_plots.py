"""Interactive evidence, using ordinary DataFrame HTML (no optional Styler/Jinja2)."""
from __future__ import annotations
import html
import json
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, float_precision='round_trip')


def figures(run: Path, evidence: Path) -> list:
    run, evidence = Path(run), Path(evidence)
    prior = read(evidence/'metrics.csv').query("Gender == 'W' and recipe != 'anchor'")
    metrics = read(run/'replication_metrics.csv')
    changes = metrics.query("recipe == 'anchor_change'").copy()
    metrics['season_label'] = metrics.Season.astype(str)
    changes['season_label'] = changes.Season.astype(str)
    prior['season_label'] = prior.Season.astype(str)
    preds = read(run/'replication_predictions.csv')
    keys = ['Gender', 'Season', 'Team1ID', 'Team2ID']
    anchor = preds.query("recipe == 'anchor'")[keys+['y','probability','squared_error']]
    joined = preds.query("recipe == 'anchor_change'").merge(anchor, on=keys, suffixes=('', '_anchor'), validate='one_to_one')
    if not np.array_equal(joined.y, joined.y_anchor):
        raise ValueError('Paired prediction labels disagree')
    joined['paired_loss_delta'] = joined.squared_error - joined.squared_error_anchor
    joined['season_label'] = joined.Season.astype(str)
    joined['confidence_bin'] = pd.cut(joined.probability_anchor, np.linspace(0,1,6), include_lowest=True).astype(str)
    confidence = joined.groupby(['season_label','confidence_bin'], observed=True).agg(
        mean_delta=('paired_loss_delta','mean'), games=('paired_loss_delta','size')).reset_index()
    reliability = preds.copy()
    reliability['probability_bin'] = pd.cut(reliability.probability, np.linspace(0,1,6), include_lowest=True).astype(str)
    reliability = reliability.groupby(['recipe','probability_bin'], observed=True).agg(
        mean_probability=('probability','mean'), observed_rate=('y','mean'), games=('y','size')).reset_index()
    coverage = read(run/'coverage.csv'); coverage['season_label'] = coverage.Season.astype(str)
    coefs = read(run/'coefficients.csv'); coefs['season_label'] = coefs.Season.astype(str)
    redundancy = read(run/'training_redundancy.csv'); redundancy['season_label'] = redundancy.Season.astype(str)
    sensitivity = []
    for season in sorted(changes.Season.unique()):
        sensitivity.append({'omitted_season': str(season), 'remaining_mean_delta': changes.loc[changes.Season != season,'delta_vs_anchor'].mean()})
    plots = [
        px.bar(prior, x='season_label', y='delta_vs_anchor', color='recipe', barmode='group',
               title='Discovery evidence · women’s Brier change (negative is better)'),
        px.line(metrics, x='season_label', y='brier', color='recipe', markers=True,
                hover_data=['role','games'], title='Fixed reference versus unchanged two-feature family'),
        px.bar(changes, x='season_label', y='delta_vs_anchor', color='role',
               title='Season deltas · only 2016 and 2018 determine the replication gate'),
        px.ecdf(joined, x='paired_loss_delta', color='season_label',
                title='Paired game-loss changes · descriptive, not independent observations'),
        px.bar(confidence, x='confidence_bin', y='mean_delta', color='season_label', barmode='group',
               hover_data=['games'], title='Loss changes by reference probability range · sparse-bin caution'),
        px.scatter(reliability, x='mean_probability', y='observed_rate', color='recipe', size='games',
                   range_x=[0,1], range_y=[0,1], title='Four-season calibration · descriptive pooled view'),
        px.bar(coverage, x='season_label', y='late_physical_games', hover_data=['early_physical_games','teams'],
               title='Cached women’s regular-season support · no ratings rebuilt'),
        px.line(coefs, x='season_label', y='coefficient', color='feature', markers=True,
                title='Training-only RMS-standardized coefficients · not causal importance'),
        px.bar(redundancy, x='season_label', y='max_abs_anchor_correlation', color='feature', barmode='group',
               hover_data=['most_correlated_anchor'], title='Training-only overlap with existing reference features'),
        px.bar(pd.DataFrame(sensitivity), x='omitted_season', y='remaining_mean_delta',
               title='Leave-one-season-out average · sensitivity, not a confidence interval'),
    ]
    plots[5].add_shape(type='line', x0=0,y0=0,x1=1,y1=1, line={'dash':'dash'})
    comps = read(run/'component_metrics.csv')
    if not comps.empty:
        comps['season_label'] = comps.Season.astype(str)
        plots.append(px.bar(comps, x='season_label', y='delta_vs_full', color='removed_feature', barmode='group',
                           title='Drop-one effects · positive means removal worsened Brier'))
        means = comps.groupby('removed_feature',as_index=False).agg(mean_delta_vs_full=('delta_vs_full','mean'))
        plots.append(px.bar(means,x='removed_feature',y='mean_delta_vs_full',
                           title='Mean conditional component effect · post-gate exploratory comparison'))
    for fig in plots:
        fig.update_layout(height=440, margin={'l':45,'r':25,'t':70,'b':60}, font={'size':13})
    return plots


def make_report(run: Path, evidence: Path) -> tuple[Path, int]:
    plots = figures(run, evidence)
    summary = json.loads((run/'summary.json').read_text())
    metrics = read(run/'replication_metrics.csv')
    parts = ['<!doctype html><html><head><meta charset="utf-8"><title>March Mania · Temporal change replication</title>',
             '<style>body{font-family:Arial,sans-serif;max-width:1140px;margin:36px auto;padding:0 20px;line-height:1.55}table{border-collapse:collapse}td,th{padding:8px;text-align:right;border-bottom:1px solid #ccc}pre{white-space:pre-wrap}h1{font-size:30px}</style></head><body>',
             '<h1>Women’s temporal-change feature replication</h1>',
             '<p>Unchanged features; previously-used historical seasons; no new leaderboard score. ',
             'Discovery years 2017 and 2019 are excluded from the replication gate. No automatic promotion.</p>',
             '<h2>Decision and provenance</h2><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre>',
             '<h2>Measured results</h2>'+metrics.to_html(index=False,float_format=lambda n:f'{n:.7f}')]
    for i, fig in enumerate(plots):
        parts.append(pio.to_html(fig,full_html=False,include_plotlyjs=True if i==0 else False))
    parts.append('</body></html>')
    target = run/'temporal_validation.html'; tmp = target.with_suffix('.partial')
    tmp.write_text('\n'.join(parts)); tmp.replace(target)
    return target, len(plots)
