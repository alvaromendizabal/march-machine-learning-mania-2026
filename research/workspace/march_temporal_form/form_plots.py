"""Ten Plotly charts; no pandas Styler, Jinja2, Kaleido, or external assets."""
from pathlib import Path
import html,json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def frame(p):return pd.read_csv(p,float_precision='round_trip')

def figures(run,evidence):
    run,evidence=Path(run),Path(evidence)
    old=frame(evidence/'replication_metrics.csv').query("recipe=='anchor_record'")
    old['role']=old.Season.map(lambda x:'Discovery (selected)' if x==2018 else 'Additional season')
    figs=[]
    figs.append(px.bar(old,x='Season',y='delta_vs_anchor',color='role',title='01 · Previous record family: discovery gain did not replicate'))
    c=frame(run/'coverage.csv')
    figs.append(px.bar(c,x='Season',y='early_physical_games',color='Gender',barmode='group',title='02 · Games used to fit the frozen day-100 ratings'))
    figs.append(px.bar(c,x='Season',y='late_physical_games',color='Gender',barmode='group',title='03 · Later games scored against the earlier ratings'))
    teams=pd.concat([frame(p) for p in sorted((run/'snapshots').glob('*/features.csv'))],ignore_index=True)
    current=teams.query('Season==2019').copy()
    figs.append(px.scatter(current,x='late_offense_surprise',y='late_defense_surprise',color='Gender',
          hover_data=['TeamID','late_games','early_games'],title='04 · Late offensive and defensive surprises · 2019'))
    figs.append(px.scatter(current,x='late_offense_change',y='late_defense_change',color='Gender',
          hover_data=['TeamID','first_window_games','second_window_games'],title='05 · Residual change between the two late-season windows · 2019'))
    m=frame(run/'metrics.csv');m['population_season']=m.Gender+' '+m.Season.astype(str)
    figs.append(px.bar(m,x='population_season',y='brier',color='recipe',barmode='group',title='06 · Fixed-reference comparisons · historical Brier'))
    figs.append(px.bar(m.query("recipe!='anchor'"),x='population_season',y='delta_vs_anchor',color='recipe',
         barmode='group',title='07 · Added features: negative Brier delta is better'))
    a=frame(run/'ablations.csv');a['population_season']=a.Gender+' '+a.Season.astype(str)
    figs.append(px.bar(a,x='population_season',y='brier_delta',color='comparison',barmode='group',
         title='08 · Controlled family additions, without replacement feature selection'))
    r=frame(run/'training_redundancy.csv');r['population_season']=r.Gender+' '+r.Season.astype(str)
    matrix=r.pivot(index='feature',columns='population_season',values='max_abs_anchor_correlation')
    figs.append(go.Figure(go.Heatmap(z=matrix.to_numpy(),x=matrix.columns.tolist(),y=matrix.index.tolist(),zmin=0,zmax=1),
       layout={'title':'09 · Training-only overlap with existing reference inputs'}))
    p=frame(run/'predictions.csv');p['bin']=(p.probability*10).astype(int).clip(0,9)
    p['route']=p.Gender+' '+p.Season.astype(str)+' · '+p.recipe
    cal=p.groupby(['route','bin'],as_index=False).agg(probability=('probability','mean'),win_rate=('y','mean'),games=('y','size'))
    fig=px.line(cal,x='probability',y='win_rate',color='route',markers=True,hover_data=['games'],
                title='10 · Descriptive reliability · sparse bins, not a significance test')
    fig.add_trace(go.Scatter(x=[0,1],y=[0,1],mode='lines',name='Ideal reliability'));figs.append(fig)
    for fig in figs:
        fig.update_layout(height=470,margin={'l':65,'r':30,'t':80,'b':60},font={'size':13})
    return figs

def make_report(run,evidence):
    import plotly.io as pio
    run=Path(run);plots=figures(run,evidence)
    summary=json.loads((run/'summary.json').read_text())
    header='<h1>March Mania · Frozen-early-rating temporal form</h1><p>Exploratory historical feature investigation. No leaderboard result or automatic promotion.</p>'
    tables=frame(run/'metrics.csv').to_html(index=False,float_format=lambda x:f'{x:.7f}',escape=True)
    sections=[pio.to_html(f,full_html=False,include_plotlyjs=True if i==0 else False) for i,f in enumerate(plots)]
    body=header+tables+''.join(sections)+'<h2>Provenance and decisions</h2><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre>'
    page='<!doctype html><html><head><meta charset="utf-8"><title>March Mania · Temporal form</title><style>body{font-family:Arial,sans-serif;max-width:1250px;margin:40px auto;padding:0 20px}table{border-collapse:collapse;font-size:13px}td,th{padding:6px}pre{white-space:pre-wrap}</style></head><body>'+body+'</body></html>'
    out=run/'temporal_form_report.html';out.write_text(page)
    (run/'plot_manifest.json').write_text(json.dumps({'count':len(plots),'self_contained':True}))
    return out
