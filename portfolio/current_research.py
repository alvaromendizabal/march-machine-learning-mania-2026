"""Employer-facing aggregate review. No forecasting implementation or training."""
from __future__ import annotations
import argparse, base64, hashlib, io, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'reports/current_research/release_decision.json'
NB=ROOT/'portfolio/current_research.ipynb'
RECEIPT=ROOT/'reports/current_research/publication.json'
FIGURES=['release_scores','men_research','women_historical','women_years','women_target_control','protected_rows']
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate(d):
    if d['schema']!=1:raise ValueError('Unknown evidence schema')
    s,r,w=d['scored'],d['replay'],d['women_historical']
    if s['champion']!=.1094899 or s['women_candidate']!=.1105237 or s['decision']!='KEEP_CHAMPION_REJECT_WOMEN':raise ValueError('Unsupported score or promotion')
    if s['champion_ref']!='56447505' or s['women_ref']!='56469094':raise ValueError('Submission identity changed')
    if r['new_tree_fits']!=0 or r['new_submissions']!=0 or r['reused_tree_fits']!=45:raise ValueError('Replay must not become a new experiment')
    for h in [s['champion_sha256'],s['women_sha256'],d['source']['sha256']]:
        if len(h)!=64 or any(c not in '0123456789abcdef' for c in h):raise ValueError('Invalid checksum')
    if [x['year'] for x in w['years']]!=[2023,2024,2025]:raise ValueError('Incomplete historical years')
    for k in ['core','binary','margin']:
        if not all(math.isfinite(x[k]) and 0<=x[k]<=1 for x in w['years']):raise ValueError('Invalid historical metric')
        if abs(sum(x[k] for x in w['years'])/3-w[k])>1e-12:raise ValueError('Pooled historical metric disagrees')
    p=d['preservation']
    if p!={'total_rows':132133,'changed_women_rows':2278,'protected_rows':129855,'men_rows':66430}:raise ValueError('Preservation evidence changed')
    return d

def load():return validate(json.loads(DATA.read_text()))
def chart(name,title,labels,series,ylabel):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    import plotly.graph_objects as go
    from IPython.display import display
    labels=[str(x) for x in labels];fig=go.Figure();png,ax=plt.subplots(figsize=(10,5.3),layout='constrained');x=np.arange(len(labels));width=.78/len(series)
    for i,(label,values) in enumerate(series.items()):
        fig.add_bar(name=label,x=labels,y=values)
        ax.bar(x+(i-(len(series)-1)/2)*width,values,width,label=label)
    fig.update_layout(title=title,width=960,height=530,barmode='group',xaxis_type='category',yaxis_title=ylabel,font_size=13,margin=dict(l=80,r=30,t=80,b=110),legend=dict(orientation='h',y=-.24))
    ax.set_xticks(x,labels);ax.set_title(title,pad=18);ax.set_ylabel(ylabel);ax.ticklabel_format(axis='y',useOffset=False,style='plain')
    if len(series)>1:ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=3,frameon=False)
    stream=io.BytesIO();png.savefig(stream,format='png',dpi=130);plt.close(png);image=stream.getvalue()
    dest=ROOT/'reports/current_research/figures'/(name+'.png');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(image)
    display({'application/vnd.plotly.v1+json':json.loads(fig.to_json()),'image/png':base64.b64encode(image).decode()},raw=True)

def build(kernel):
    import nbformat as nbf
    from nbclient import NotebookClient
    md,code=nbf.v4.new_markdown_cell,nbf.v4.new_code_cell
    cells=[md('# NCAA forecasting | achieved release and research judgment\n**Alvaro Mendizabal · employer-facing ML engineering case study**\n\nA recorded late-submission Brier of **0.1094899** is numerically below the published 2026 winning benchmark of **0.1097454**. This is not an original first-place finish. The notebook renders approved aggregates only; it does not distribute or execute the forecasting system.'),
    code("from pathlib import Path\nimport sys\nroot=Path.cwd()\nif not (root/'portfolio').is_dir(): root=root.parent\nsys.path.insert(0,str(root/'portfolio'))\nfrom current_research import load,chart\nimport pandas as pd\nfrom IPython.display import display\nd=load();s=d['scored'];w=d['women_historical']\ndisplay(pd.DataFrame([{'Release':'Retained champion','Brier':s['champion'],'Status':'Scored'}, {'Release':'Women extension','Brier':s['women_candidate'],'Status':'Scored; rejected'}]))"),
    md('## 1. The achieved result and the rejected extension\nThe existing men’s margin-based release improved the predecessor. A later women’s extension had encouraging historical results, but its recorded late score was **0.1105237**, worse by **0.0010338**. It was rejected; the **0.1094899** champion is unchanged. These three observations belong to post-competition scoring, not a new prospective trial.'),
    code("chart('release_scores','Recorded late scores — lower is better',['Prior release','Retained champion','Women extension'],{'Brier':[s['predecessor'],s['champion'],s['women_candidate']]},'Brier')\nprint('Published benchmark:',s['benchmark'])\nprint('Champion below benchmark:',round(s['benchmark']-s['champion'],7))"),
    md('## 2. More features were not automatically better\nSeveral plausible approaches were tested and rejected. Learning actual score margins gave the auxiliary information a different role and produced a useful men’s ensemble. Selection results from a win/loss model cannot establish that selection is exhausted for a different objective. The next private question is model-specific rather than another blanket claim about thousands of columns.'),
    code("m=d['men_historical']\nchart('men_research','Same 503-game men’s historical screen',['Full bundle','Nested binary selection','Margin approach'],{'Gain vs screening core':[m['core']-m['full_feature_fusion'],m['core']-m['nested_binary_selection'],m['core']-m['margin_blend']]},'Brier reduction; positive is better')"),
    md('## 3. Why validation and actual scoring must remain separate\nThe women’s robustness result improved on the same 189 historical main-bracket games from 2023–2025. Whole-year exclusion, matched targets and fixed random repeats constrained the experiment, but these were reused development years. The later score did not validate a gain. No single cause is established without further evidence.'),
    code("chart('women_historical','Women’s reused historical assessment — 189 games',['Frozen reference','Binary control','Margin candidate'],{'Brier':[w['core'],w['binary'],w['margin']]},'Historical Brier; not Kaggle score')"),
    code("years=pd.DataFrame(w['years'])\ndisplay(years)\nchart('women_years','Historical gains did not guarantee a later score gain',years.year.tolist(),{'Gain vs reference':(years.core-years.margin).tolist()},'Core minus margin Brier')"),
    code("chart('women_target_control','Matched target comparison — not uniform by year',years.year.tolist(),{'Margin advantage':(years.binary-years.margin).tolist()},'Binary minus margin Brier')"),
    md('## 4. Engineering protected the achieved release\nOnly 2,278 women’s matchup lines changed in the rejected candidate. All 66,430 men’s lines and 129,855 total protected lines were identical. The latest replay reused all 45 candidate models, made zero new fits and zero new uploads, and recovered the existing score. A negative scientific outcome is not an execution crash.'),
    code("p=d['preservation']\nchart('protected_rows','Candidate scope — original champion was not overwritten',['Changed women','Protected lines'],{'CSV lines':[p['changed_women_rows'],p['protected_rows']]},'Prediction lines')\ndisplay(pd.DataFrame([d['replay']]))"),
    md('## 5. What remains unresolved\nThe work is a benchmark-informed applied ML result, not evidence of universal state-of-the-art performance. Top-solution coverage is not complete. Dated external information, richer representations and objective-specific selection remain research questions. A lower 2026 late score is not proof of a 2027 advantage. Future forecasts need timestamped input snapshots and a frozen evaluation protocol.\n\nInner held-out predictions informed both early stopping and calibration; previous research reused the outer years. Additional random repeats do not create independent tournaments. No 0.09 result is claimed or implied.'),
    md('## 6. Ownership and public scope\nPublic material demonstrates the result, reasoning, controls and engineering. The current detailed implementation, feature definitions, tuning recipes and model files stay outside this publication. Previously published source and license terms still exist; this update does not erase history.\n\nThe compact reference is attributed to Harrison Horan’s public first-place solution. The retained score is supported by submission identity and prediction hashes in the aggregate evidence. Private repeatability is preserved for the owner, without adding a public retraining kit.'),
    code("print('Release decision:',s['decision'])\nprint('New score produced by this report:',None)\nprint('REPORT_COMPLETE — approved aggregates; no training or submission')")]
    nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'name':kernel,'display_name':'Python 3','language':'python'}})
    NotebookClient(nb,timeout=90,kernel_name=kernel,resources={'metadata':{'path':str(ROOT)}}).execute();NB.write_text(nbf.writes(nb));receipt=inspect();RECEIPT.write_text(json.dumps(receipt,indent=2)+'\n');return receipt

def inspect():
    import nbformat
    nb=nbformat.read(NB,as_version=4);nbformat.validate(nb);cells=[c for c in nb.cells if c.cell_type=='code'];outs=[o for c in cells for o in c.get('outputs',[])]
    if [c.execution_count for c in cells]!=list(range(1,len(cells)+1)) or any(o.output_type=='error' for o in outs):raise ValueError('Incomplete notebook execution')
    plots=[o.data['application/vnd.plotly.v1+json'] for o in outs if 'application/vnd.plotly.v1+json' in o.get('data',{})]
    png=sum('image/png' in o.get('data',{}) for o in outs)
    if len(plots)!=6 or png!=6 or 'REPORT_COMPLETE' not in str(nb.cells[-1].outputs):raise ValueError('Missing plot or sentinel')
    if any(x['layout'].get('width',0)<900 or x['layout'].get('height',0)<450 for x in plots):raise ValueError('Unreadable figure')
    if NB.stat().st_size>2*1024**2:raise ValueError('Oversized notebook')
    return {'status':'PASS','scope':'Aggregate employer case study; no training','source_sha256':digest(DATA),'builder_sha256':digest(__file__),'notebook_sha256':digest(NB),'code_cells':len(cells),'plotly_outputs':len(plots),'png_fallbacks':png,'model_fits':0,'figures':{n:digest(ROOT/'reports/current_research/figures'/(n+'.png')) for n in FIGURES}}

def main():
    a=argparse.ArgumentParser();a.add_argument('--build',action='store_true');a.add_argument('--check',action='store_true');a.add_argument('--kernel',default='python3');args=a.parse_args();load()
    if args.build:print(json.dumps(build(args.kernel),indent=2))
    elif args.check:
        r=inspect()
        if r!=json.loads(RECEIPT.read_text()):raise ValueError('Publication receipt changed')
        print(json.dumps(r,indent=2))
    else:a.error('Select --build or --check')
if __name__=='__main__':main()
