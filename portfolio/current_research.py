"""Execute a portable research report from committed aggregates; no model training."""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'reports/current_research/evidence.json'
PROGRESSION = ROOT / 'reports/current_research/progression.json'
NOTEBOOK = ROOT / 'portfolio/current_research.ipynb'
RECEIPT = ROOT / 'reports/current_research/publication.json'
FIGURES = ['scored','screen','pooled','years','seeds','ablation','women','women_years']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def valid_hash(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def validate_data(data):
    if data['schema'] != 1:
        raise ValueError('Unsupported evidence schema')
    r = data['robustness']
    if r['new_kaggle_score'] is not None or r['submissions'] != 0:
        raise ValueError('Historical evidence must not become a Kaggle score')
    if r['decision'] != 'CANDIDATE_BUILD_REVIEW' or not all(r['checks'].values()):
        raise ValueError('Recorded historical decision changed')
    rows = r['rows']
    if [x['year'] for x in rows] != [2023,2024,2025] or sum(x['games'] for x in rows) != 189 or len(r['seeds']) != 3:
        raise ValueError('Incomplete assessment evidence')
    for key in ['core','binary','margin']:
        values = [x[key] for x in rows] + [r['pooled'][key]]
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in values):
            raise ValueError('Invalid Brier')
        if abs(sum(x[key]*x['games'] for x in rows)/189-r['pooled'][key]) > 1e-12:
            raise ValueError('Season aggregation disagrees')
    if [x['seed'] for x in r['seeds']] != data['method']['seeds']:
        raise ValueError('Seed selection changed')
    if data['method']['margin_weight'] != .25:
        raise ValueError('Frozen blend changed')
    if r['new_tree_fits'] != sum(data['method']['inner_fold_counts'])*3*2:
        raise ValueError('Fit accounting disagrees')
    for x in data['screen']['rows']:
        if not all(math.isfinite(x[k]) and 0 <= x[k] <= 1 for k in ['core','candidate']):
            raise ValueError('Invalid screen metric')
    if not all(valid_hash(x['sha256']) for x in data['sources']):
        raise ValueError('Invalid source checksum')
    return data


def validate_progression(d):
    s,w=d['scored'],d['women_screen']
    if d['schema']!=1 or s['status']!='SCORED' or str(s['submission_ref'])!='56447505':
        raise ValueError('Scored identity changed')
    raw=s['raw_submission']
    if raw['status']!='SubmissionStatus.COMPLETE' or raw['ref']!=str(s['submission_ref']):
        raise ValueError('Submission not complete or identity mismatch')
    if s['candidate_score']!=.1094899 or any(float(raw[k])!=s['candidate_score'] for k in ['privatescore','publicscore']):
        raise ValueError('Score disagrees with observed receipt')
    if not valid_hash(s['candidate_sha256']) or s['candidate_sha256'] not in raw['description']:
        raise ValueError('Missing scored file identity')
    if abs(s['incumbent_score']-s['candidate_score']-s['gain_vs_incumbent'])>1e-12:
        raise ValueError('Score improvement arithmetic')
    if abs(s['candidate_score']-s['benchmark']-s['gap_to_published_benchmark'])>1e-12:
        raise ValueError('Benchmark arithmetic')
    if w['new_kaggle_score'] is not None or w['submissions'] or w['men_predictions_changed']:
        raise ValueError('Women screen is not a submission')
    if w['decision']!='FULL_RECIPE_REVIEW' or len(w['checks'])!=8 or not all(w['checks'].values()):
        raise ValueError('Screen decision changed')
    for group,expected,n in [('rows',[2017,2018,2019,2021,2022,2023,2024,2025],504),('binary_rows',[2017,2018,2019,2021,2022,2023,2024,2025],504),('full_reference_rows',[2023,2024,2025],189)]:
        rows=w[group]
        if [x['year'] for x in rows]!=expected or sum(x['games'] for x in rows)!=n:
            raise ValueError('Women evaluation population changed')
        for x in rows:
            if not all(math.isfinite(x[k]) and 0<=x[k]<=1 for k in ['baseline_brier','candidate_brier']):
                raise ValueError('Invalid women metric')
            if abs(x['baseline_brier']-x['candidate_brier']-x['gain'])>1e-12:
                raise ValueError('Women gain arithmetic')
        key='screen_margin_brier' if group=='rows' else 'screen_binary_brier' if group=='binary_rows' else 'full_reference_margin_brier'
        if abs(sum(x['candidate_brier']*x['games'] for x in rows)/n-w[key])>1e-12:
            raise ValueError('Women pooled arithmetic')
    if w['new_tree_fits']!=48 or w['feature_count']!=32 or sum(x['gain']>0 for x in w['rows'])!=6:
        raise ValueError('Women screen accounting')
    if abs(w['screen_binary_brier']-w['screen_margin_brier']-w['objective_gain'])>1e-12:
        raise ValueError('Objective ablation arithmetic')
    if not all(valid_hash(x['sha256']) for x in d['sources']):
        raise ValueError('Invalid progression provenance')
    return d


def load_evidence():
    return validate_data(json.loads(EVIDENCE.read_text()))


def load_progression():
    return validate_progression(json.loads(PROGRESSION.read_text()))


def chart(name,title,labels,series,ylabel,reference=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    import plotly.graph_objects as go
    from IPython.display import display
    fig=go.Figure(); mpl,ax=plt.subplots(figsize=(10,5.2),layout='constrained')
    x=np.arange(len(labels));width=.78/len(series)
    for i,(label,values) in enumerate(series.items()):
        fig.add_bar(name=label,x=labels,y=values)
        ax.bar(x+(i-(len(series)-1)/2)*width,values,width,label=label)
    if reference is not None:
        fig.add_hline(y=reference,line_dash='dot');ax.axhline(reference,linestyle=':',label='Published benchmark')
    fig.update_layout(title=title,width=960,height=540,barmode='group',yaxis_title=ylabel,font_size=13,margin=dict(l=75,r=25,t=85,b=100),legend=dict(orientation='h',y=-.25))
    ax.set_xticks(x,labels);ax.set_ylabel(ylabel);ax.set_title(title,pad=18);ax.ticklabel_format(axis='y',style='plain',useOffset=False)
    if len(series)>1 or reference is not None:ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=3,frameon=False)
    stream=io.BytesIO();mpl.savefig(stream,format='png',dpi=130);plt.close(mpl)
    image=stream.getvalue();dest=ROOT/'reports/current_research/figures'/f'{name}.png';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(image)
    display({'application/vnd.plotly.v1+json':json.loads(fig.to_json()),'image/png':base64.b64encode(image).decode()},raw=True)


def build(kernel='python3'):
    import nbformat as nbf
    from nbclient import NotebookClient
    md,code=nbf.v4.new_markdown_cell,nbf.v4.new_code_cell
    cells=[
        md('# NCAA tournament probability forecasting\n## From controlled research to a scored margin ensemble\n**Alvaro Mendizabal | September 2026**\n\nThis clean-kernel report reads committed aggregate evidence only. No fitting, downloads, cloud access or submissions occur. The achieved late score and the unsubmitted women’s experiment are kept separate.'),
        code("from pathlib import Path\nimport sys\nroot=Path.cwd()\nif not (root/'portfolio').is_dir(): root=root.parent\nsys.path.insert(0,str(root/'portfolio'))\nfrom current_research import load_evidence,load_progression,chart\nimport pandas as pd\nfrom IPython.display import display\ne=load_evidence();d=load_progression();r=e['robustness'];s=d['scored'];w=d['women_screen']\ndisplay(pd.DataFrame([{'Evaluation':'Recorded late submission','Brier':s['candidate_score'],'Status':'COMPLETE; not an original placement'},{'Evaluation':'Women screen: 504 historical games','Brier':w['screen_margin_brier'],'Status':'Unsubmitted; fuller-ensemble review'}]))"),
        md('## 1. What actually improved the scored result?\nThe fixed men’s margin blend scored **0.1094899**, versus its predecessor’s **0.1098691**. The first-place author reports **0.1097454 on 126 games**. Our late score is numerically lower by **0.0002555**; this is not retroactive first place or statistically established prospective superiority. The source receipt identifies submission **56447505** and the exact prediction-file hash.'),
        code("display(pd.DataFrame([{'Improvement over predecessor':s['gain_vs_incumbent'],'Amount below published number':-s['gap_to_published_benchmark'],'Submission reference':s['submission_ref']}]))\nchart('scored','Recorded late submissions — lower Brier is better',['Two-feature predecessor','Scored margin ensemble'],{'Brier':[s['incumbent_score'],s['candidate_score']]},'Brier',s['benchmark'])"),
        md('The build made one upload. Its 132,133-row output changed only 2,278 seeded-men matchups, preserving 129,855 other lines, including all 65,703 women’s lines. The scored CSV stays outside this publication. Its hash and the aggregate verification record are committed; no credential or raw training data is published.'),
        md('## 2. Negative findings narrowed the hypothesis\nFull feature union, residual PCA, nested subset selection and frozen-core correction failed to improve the common men’s historical screen. We then changed the target from signed win/loss to actual point margin, keeping representation and training matched. A close win and a large win no longer give identical supervision. This is a tested mechanism, not an assumption that regression always helps.'),
        code("screen=pd.DataFrame(e['screen']['rows']);screen['gain']=screen['core']-screen['candidate']\ndisplay(screen)\nchart('screen','Men’s eight-season screen: retained positive and negative findings',['Full bundle','Residual PCA','Nested subsets','Feature correction','Margin blend'],{'Brier reduction':screen['gain'].tolist()},'Core minus candidate Brier')"),
        md('## 3. Historical support before the score test\nThe men’s fuller ensemble uses 33 inputs, three predeclared seeds, whole-season inner omissions, fold-local transformations, and a fixed 75% core / 25% auxiliary blend. A matched binary target controls for added model capacity. Outer years remain excluded from fitting; reused development years are not independent confirmation.'),
        code("p=r['pooled'];display(pd.DataFrame([p]))\nchart('pooled','Men’s fuller ensemble — 189 historical main-bracket games',['Frozen core','Binary blend','Margin blend'],{'Brier':[p['core'],p['binary'],p['margin']]},'Brier')"),
        code("years=pd.DataFrame(r['rows']);display(years)\nchart('years','Men’s historical improvement by assessment year',years.year.astype(str).tolist(),{'Binary blend':(years.core-years.binary).tolist(),'Margin blend':(years.core-years.margin).tolist()},'Core minus blend Brier')"),
        code("seeds=pd.DataFrame(r['seeds']);seeds['gain']=p['core']-seeds.brier;display(seeds)\nchart('seeds','All three predeclared men’s seeds retained',seeds.seed.astype(str).tolist(),{'Brier reduction':seeds.gain.tolist()},'Core minus margin-blend Brier')"),
        code("chart('ablation','Does margin supervision beat the matched binary target?',years.year.astype(str).tolist(),{'Margin advantage':(years.binary-years.margin).tolist()},'Binary-blend minus margin-blend Brier')"),
        md('The margin blend improves the stronger core in all three years and for all three seeds. It beats the matched binary blend in two of three years, not uniformly. The 360-fit robustness result preceded a 66-fit candidate build and a single score test. None of those model fits is repeated by this report.'),
        md('## 4. Can the mechanism transfer to women?\nThe separate women’s experiment uses its own four-feature core plus 28 auxiliary differences. No women’s Massey or men-only AP inputs are invented. One fixed 25% margin blend is compared with its matched binary-target control on **504 games across eight historical seasons**. Existing scored predictions remain untouched.'),
        code("display(pd.DataFrame([{'Core':w['screen_core_brier'],'Binary blend':w['screen_binary_brier'],'Margin blend':w['screen_margin_brier'],'Gain':w['screen_gain'],'Gain over binary':w['objective_gain']}]))\nchart('women','Women’s screen — 504 games; not a Kaggle score',['Frozen women core','Binary blend','Margin blend'],{'Brier':[w['screen_core_brier'],w['screen_binary_brier'],w['screen_margin_brier']]},'Historical Brier')"),
        code("wy=pd.DataFrame(w['rows']);display(wy)\nchart('women_years','Women’s margin blend improves six of eight historical years',wy.year.astype(str).tolist(),{'Brier reduction':wy.gain.tolist()},'Core minus margin-blend Brier')\ndisplay(pd.DataFrame(w['full_reference_rows']))"),
        md('The women’s screen improves Brier by **0.0017536** and beats its matched binary control by **0.0014509**. Against the retained stronger 2023–2025 core, the same screened margin forecasts improve Brier from **0.1292138 to 0.1282181**, with gains in all three years. That is not yet a full margin ensemble: it motivates the next fuller-ensemble test. All eight screening checks passed in an 18.80-second run with 48 tree fits and 46 regression tests.'),
        code("display(pd.DataFrame([{'Check':k,'Passed':v} for k,v in w['checks'].items()]))\nprint('Women decision:',w['decision'])\nprint('Women candidate Kaggle score:',w['new_kaggle_score'])"),
        md('## 5. Limits, provenance and the next decision\nHistorical years were reused, hypotheses were selected sequentially, and inner held-out scores served early stopping and calibration. Bootstrap support is conditional, not selection-adjusted. Seeds measure numerical stability, not independent tournaments. The men’s late score motivated the women’s hypothesis, but 2026 outcomes are excluded from fitting.\n\n**Completed:** scored men’s margin release, protected-row validation, women’s bounded screen and this publication. **Next:** three-seed, whole-season-omission women’s robustness at the same fixed blend. A later candidate build and separately authorized scoring require that decision first. No worthy new submission is claimed before it exists.\n\nGitHub contains the evidence, report code, tests and saved plots. AWS retains full experiment sources, authorized raw records, feature caches, models and local changes. Re-executing this report reproduces aggregate analyses, not model training. Historical evidence.json is preserved; progression.json records the newer score and women’s result. Credit and limitations are in docs/current_research.md.'),
        code("print('REPORT_COMPLETE — aggregate evidence only; zero training or submissions')")]
    nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'name':kernel,'display_name':'Python 3','language':'python'}})
    NotebookClient(nb,timeout=90,kernel_name=kernel,resources={'metadata':{'path':str(ROOT)}}).execute()
    NOTEBOOK.write_text(nbf.writes(nb));receipt=inspect_notebook();RECEIPT.write_text(json.dumps(receipt,indent=2)+'\n');return receipt


def inspect_notebook():
    import nbformat
    nb=nbformat.read(NOTEBOOK,as_version=4);nbformat.validate(nb);count=plots=png=0
    for cell in nb.cells:
        if cell.cell_type!='code':continue
        count+=1
        if cell.execution_count!=count:raise ValueError('Unresolved execution')
        for out in cell.outputs:
            if out.output_type=='error':raise ValueError('Notebook error')
            data=out.get('data',{})
            if 'application/vnd.plotly.v1+json' in data:
                layout=data['application/vnd.plotly.v1+json']['layout']
                if layout.get('width',0)<900 or layout.get('height',0)<450:raise ValueError('Unreadable dimensions')
                plots+=1
            if 'image/png' in data:
                image=base64.b64decode(data['image/png']);
                if not image.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Invalid PNG fallback')
                png+=1
    if plots!=8 or png!=8 or 'REPORT_COMPLETE' not in str(nb.cells[-1].outputs):raise ValueError('Incomplete visual evidence')
    if NOTEBOOK.stat().st_size>2*1024*1024:raise ValueError('Notebook too large')
    return {'status':'PASS','scope':'Executed aggregate report; no training','evidence_sha256':digest(EVIDENCE),'progression_sha256':digest(PROGRESSION),'notebook_sha256':digest(NOTEBOOK),'builder_sha256':digest(__file__),'executed_code_cells':count,'plotly_outputs':plots,'embedded_png_fallbacks':png,'report_model_fits':0,'figure_sha256':{n+'.png':digest(ROOT/'reports/current_research/figures'/f'{n}.png') for n in FIGURES}}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',action='store_true');p.add_argument('--check',action='store_true');p.add_argument('--kernel',default='python3');a=p.parse_args();load_evidence();load_progression()
    if a.build:print(json.dumps(build(a.kernel),indent=2))
    elif a.check:
        actual=inspect_notebook()
        if actual!=json.loads(RECEIPT.read_text()):raise ValueError('Publication receipt differs')
        print(json.dumps(actual,indent=2))
    else:p.error('Choose --build or --check')

if __name__=='__main__':main()
