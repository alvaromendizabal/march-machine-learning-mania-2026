"""Plotly evidence from saved records; no pandas Styler/Jinja2 dependency."""
from pathlib import Path
import html
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio


def frame(path):
    return pd.read_csv(path,float_precision='round_trip')


def figures(run, evidence):
    run,evidence=Path(run),Path(evidence)
    metrics=frame(run/'replication_metrics.csv')
    prior=frame(evidence/'metrics.csv');prior=prior.loc[prior.recipe!='anchor']
    records=metrics.loc[metrics.recipe=='anchor_record'].copy()
    pred=frame(run/'replication_predictions.csv')
    keys=['Gender','Season','Team1ID','Team2ID']
    a=pred.loc[pred.recipe=='anchor',keys+['y','probability']].rename(columns={'probability':'anchor_probability'})
    b=pred.loc[pred.recipe=='anchor_record',keys+['probability']]
    paired=a.merge(b,on=keys,validate='one_to_one')
    paired['loss_delta']=(paired.probability-paired.y)**2-(paired.anchor_probability-paired.y)**2
    coeff=frame(run/'record_coefficients.csv')
    redundancy=frame(run/'training_redundancy.csv')
    result=[
        px.bar(prior,x='recipe',y='delta_vs_anchor',color='Gender',barmode='group',
               title='01 · Completed 2018 experiment: record features warranted women-only replication',
               labels={'delta_vs_anchor':'Brier change; negative is better'}),
        px.line(metrics,x='Season',y='brier',color='recipe',markers=True,
                title='02 · Fixed reference versus the unchanged four-feature family',
                hover_data=['games','train_games','role']),
        px.bar(records,x='Season',y='delta_vs_anchor',color='role',
               title='03 · Per-season effect; discovery year 2018 is excluded from the gate',
               labels={'delta_vs_anchor':'Brier change; negative is better'}),
        px.box(paired,x='Season',y='loss_delta',points='outliers',
               title='04 · Paired game-loss changes (descriptive; games are not independent)',
               labels={'loss_delta':'Record-model loss minus reference loss'}),
        px.imshow(redundancy.pivot(index='feature',columns='Season',values='max_abs_anchor_correlation'),
                  aspect='auto',zmin=0,zmax=1,
                  title='05 · Training-only maximum absolute correlation with reference inputs'),
        px.line(coeff,x='Season',y='standardized_coefficient',color='feature',markers=True,
                title='06 · Record-feature coefficients; correlated inputs complicate interpretation')]
    reliability=[]
    for (season,recipe),group in pred.groupby(['Season','recipe'],sort=True):
        group=group.copy();group['bin']=pd.cut(group.probability,np.linspace(0,1,6),include_lowest=True)
        for label,h in group.groupby('bin',observed=True):
            if len(h):reliability.append({'Season':str(season),'recipe':recipe,'mean_probability':h.probability.mean(),
                'observed_win_rate':h.y.mean(),'games':len(h)})
    f=px.scatter(pd.DataFrame(reliability),x='mean_probability',y='observed_win_rate',color='recipe',
                 symbol='Season',size='games',title='07 · Calibration by season; small bins are noisy')
    f.add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Perfect calibration'))
    result.append(f)
    gate=json.loads((run/'gate.json').read_text())
    new=records.loc[records.Season.isin([2016,2017,2019])].sort_values('Season').copy()
    new['running_mean_delta']=new.delta_vs_anchor.expanding().mean()
    f=px.line(new,x='Season',y='running_mean_delta',markers=True,
              title='08 · Additional-season mean only (2018 not included)')
    f.add_hline(y=gate['thresholds']['mean_delta_at_most'],line_dash='dash',annotation_text='Compute gate threshold')
    result.append(f)
    ablations=frame(run/'ablation_metrics.csv') if (run/'ablation_metrics.csv').exists() else pd.DataFrame()
    if not ablations.empty:
        result.append(px.imshow(ablations.pivot(index='removed_feature',columns='Season',values='delta_vs_full'),
            aspect='auto',title='09 · Drop-one effects: positive means removal hurt the full family'))
        means=ablations.loc[ablations.Season!=2018].groupby('removed_feature',as_index=False).delta_vs_full.mean()
        result.append(px.bar(means,x='removed_feature',y='delta_vs_full',
            title='10 · Additional-season mean drop-one effects; descriptive, not automatic selection'))
    for f in result:
        f.update_layout(height=510,margin=dict(l=65,r=30,t=90,b=90),font=dict(size=12))
    return result


def make_report(run, evidence):
    run=Path(run);plots=figures(run,evidence)
    summary=json.loads((run/'summary.json').read_text())
    heading='<h1>March Mania | Record-feature replication</h1>'
    caution='<p>Previously consumed historical seasons. 2018 selected the family; it is excluded from the replication gate. No leaderboard result or feature promotion.</p>'
    info='<pre>'+html.escape(json.dumps(summary,indent=2))+'</pre>'
    contents=[pio.to_html(f,full_html=False,include_plotlyjs=True if i==0 else False) for i,f in enumerate(plots)]
    metrics=frame(run/'replication_metrics.csv').to_html(index=False,float_format=lambda x:f'{x:.7f}',escape=True)
    destination=run/'record_validation.html'
    destination.write_text('<!doctype html><html><head><meta charset="utf-8"><title>Record feature evidence</title>'
      '<style>body{font-family:Arial,sans-serif;max-width:1200px;margin:32px auto;padding:0 24px;line-height:1.5}pre{white-space:pre-wrap}table{border-collapse:collapse;font-size:12px}td,th{padding:6px;border-bottom:1px solid #ddd}</style>'
      '</head><body>'+heading+caution+metrics+''.join(contents)+info+'</body></html>')
    (run/'plot_manifest.json').write_text(json.dumps({'count':len(plots),'source':'saved historical experiment artifacts',
        'jinja2_required':False},indent=2))
    return destination
