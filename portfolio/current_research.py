"""Render the approved employer-facing research evidence. No forecasting training or inference."""
from __future__ import annotations
import argparse, base64, hashlib, io, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"reports/current_research/release_decision.json"
NB=ROOT/"portfolio/current_research.ipynb"
RECEIPT=ROOT/"reports/current_research/publication.json"
FIGURES=["release_scores","gains","market_components","scope","score_gap","research_boundary"]

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def validate(d):
    if d["schema"]!=1: raise ValueError("Unknown schema")
    s=d["scored"]; c=s["champion"]
    if c["score"]!=0.1089408 or c["ref"]!="56479241" or c["decision"]!="RETAIN":
        raise ValueError("Unsupported champion identity")
    if s["full_market"]["score"]!=0.1098037 or s["r1_market"]["score"]!=0.1103527:
        raise ValueError("Component score identity changed")
    if not d["decomposition"]["scored_consistent"] or not d["decomposition"]["disjoint"]:
        raise ValueError("Decomposition evidence changed")
    expected=s["margin_release"]["score"]+s["full_market"]["score"]-s["r1_market"]["score"]
    if abs(expected-d["decomposition"]["inferred_score"])>1e-12: raise ValueError("Decomposition arithmetic changed")
    lo,hi=d["decomposition"]["inferred_interval"]
    if [lo,hi] != [0.10894075,0.10894105] or not (lo<=c["score"]<=hi):
        raise ValueError("Scored result or inferred interval changed")
    i=d["integrity"]
    if i["rows"]!=132133 or i["changed_rows"]!=1986 or i["protected_rows"]!=130147 or i["women_rows_unchanged"]!=65703:
        raise ValueError("Row protection evidence changed")
    if i["tree_fits"]!=0 or i["probability_model_fits"]!=0:
        raise ValueError("Latest score test must remain zero-fit")
    if i["upload_attempts"]!=1 or i["automatic_followups"]!=0:
        raise ValueError("Submission discipline evidence changed")
    for h in [c["sha256"],d["source"]["return_sha256"]]:
        if len(h)!=64 or any(x not in "0123456789abcdef" for x in h): raise ValueError("Invalid checksum")
    return d

def load(): return validate(json.loads(DATA.read_text()))

def chart(name,title,labels,series,ylabel):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import plotly.graph_objects as go
    from IPython.display import display
    labels=[str(x) for x in labels]; x=np.arange(len(labels)); width=.78/len(series)
    fig=go.Figure(); png,ax=plt.subplots(figsize=(10,5.3),layout="constrained")
    for j,(label,values) in enumerate(series.items()):
        fig.add_bar(name=label,x=labels,y=values)
        ax.bar(x+(j-(len(series)-1)/2)*width,values,width,label=label)
    fig.update_layout(title=title,width=960,height=530,barmode="group",xaxis_type="category",yaxis_title=ylabel,font_size=13,margin=dict(l=80,r=30,t=85,b=105),legend=dict(orientation="h",y=-.23))
    ax.set_xticks(x,labels); ax.set_title(title,pad=18); ax.set_ylabel(ylabel); ax.ticklabel_format(axis="y",useOffset=False,style="plain")
    if len(series)>1: ax.legend(loc="upper center",bbox_to_anchor=(.5,-.12),ncol=3,frameon=False)
    stream=io.BytesIO(); png.savefig(stream,format="png",dpi=130); plt.close(png); image=stream.getvalue()
    dest=ROOT/"reports/current_research/figures"/(name+".png"); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(image)
    display({"application/vnd.plotly.v1+json":json.loads(fig.to_json()),"image/png":base64.b64encode(image).decode()},raw=True)

def build(kernel):
    import nbformat as nbf
    from nbclient import NotebookClient
    md,code=nbf.v4.new_markdown_cell,nbf.v4.new_code_cell
    cells=[
      md("# NCAA forecasting | scored research progression\n**Alvaro Mendizabal · employer-facing ML engineering case study**\n\nThe current post-competition release scored **0.1089408 Brier**, numerically below the published 2026 winning benchmark of **0.1097454**. This is benchmark-informed late research, not an original competition placement. The notebook renders approved aggregate evidence only; it cannot reproduce the private forecasting system."),
      code("from pathlib import Path\nimport sys\nroot=Path.cwd()\nif not (root/'portfolio').is_dir(): root=root.parent\nsys.path.insert(0,str(root/'portfolio'))\nfrom current_research import load,chart\nimport pandas as pd\nfrom IPython.display import display\nd=load();s=d['scored'];i=d['integrity'];dc=d['decomposition']\ndisplay(pd.DataFrame([{'Release':'Margin ensemble','Brier':s['margin_release']['score']},{'Release':'Full market overlay','Brier':s['full_market']['score']},{'Release':'Round-1-only overlay','Brier':s['r1_market']['score']},{'Release':'Retained futures release','Brier':s['champion']['score']}]))"),
      md("## 1. Recorded score progression\nThe retained release improves the preceding margin ensemble by **0.0005491 Brier** and is **0.0008046** numerically below the published winning benchmark. The broad market and Round-1 variants both lost, so the research record includes those negative results rather than only the successful submission."),
      code("chart('release_scores','Recorded post-competition score progression',['Margin ensemble','Full market','Round-1 only','Futures release'],{'Brier':[s['margin_release']['score'],s['full_market']['score'],s['r1_market']['score'],s['champion']['score']]},'Brier (lower is better)')"),
      code("chart('gains','Improvement relative to the margin-ensemble release',['Full market','Round-1 only','Futures release'],{'Brier reduction':[s['margin_release']['score']-s['full_market']['score'],s['margin_release']['score']-s['r1_market']['score'],s['margin_release']['score']-s['champion']['score']]},'Positive is better')"),
      md("## 2. Why the futures component could be isolated\nThe full market and Round-1-only files changed disjoint components. The 32 Round-1 predictions were identical across both variants. Removing that component from the full overlay therefore isolates the remaining 1,986-row championship-strength layer. The resulting implied interval contained the later scored value. This is strong arithmetic consistency, but the component choice is still post-hoc because two late scores informed the decision."),
      code("chart('market_components','Market component scope',['Round-1 information','Championship-strength information'],{'Rows changed':[dc['r1_rows'],dc['futures_rows']]},'Prediction rows')\nprint('Implied score:',dc['inferred_score'])\nprint('Observed futures-only score:',s['champion']['score'])"),
      md("## 3. Engineering protected the existing system\nThe final score test changed only the isolated men’s component. All other predictions were copied exactly from the preceding champion, and the prior scored artifact was never overwritten. The run performed zero model fits and made exactly one upload."),
      code("chart('scope','Final candidate scope',['Changed rows','Protected rows'],{'CSV rows':[i['changed_rows'],i['protected_rows']]},'Rows')\ndisplay(pd.DataFrame([i]))"),
      md("## 4. Competitive context\nThe official winner scored 0.1097454. The retained late score is lower, but it came after the competition and after public solution information was available. The correct portfolio claim is an improved **post-competition benchmark**, not an original rank, medal, or prize."),
      code("chart('score_gap','Distance to benchmark and stretch target',['Published winner','Retained late score','0.09 stretch target'],{'Brier':[s['benchmark'],s['champion']['score'],s['stretch_target']]},'Brier (lower is better)')"),
      md("## 5. What changed technically\nThe strongest scored system combines a compact tournament reference, a complementary score-margin ensemble, and a bounded championship-strength information layer. The public case study communicates those capabilities and the decision process without distributing the current private training or inference implementation."),
      code("chart('research_boundary','Research boundary',['Model fits in latest score test','Rows changed','Women rows changed'],{'Count':[i['tree_fits']+i['probability_model_fits'],i['changed_rows'],0]},'Count')"),
      md("## 6. Limitations and 2027\nThe 2026 late-submission loop is development research on a completed event. Multiple hypotheses and scored variants were explored, so this result is not independent confirmation. The next stronger generalization claim should come from a frozen 2027 process with timestamped inputs and predictions recorded before outcomes. Existing public history and licenses remain; new private implementation details are intentionally excluded from this release."),
      code("print('Retained submission:',s['champion']['ref'])\nprint('Retained Brier:',s['champion']['score'])\nprint('Model fits performed by this report:',0)\nprint('REPORT_COMPLETE — aggregate evidence only; no training or submission')")
    ]
    nb=nbf.v4.new_notebook(cells=cells,metadata={"kernelspec":{"name":kernel,"display_name":"Python 3","language":"python"}})
    NotebookClient(nb,timeout=90,kernel_name=kernel,resources={"metadata":{"path":str(ROOT)}}).execute()
    NB.write_text(nbf.writes(nb)); r=inspect(); RECEIPT.write_text(json.dumps(r,indent=2)+"\n"); return r

def inspect():
    import nbformat
    nb=nbformat.read(NB,as_version=4); nbformat.validate(nb)
    cells=[c for c in nb.cells if c.cell_type=="code"]; outs=[o for c in cells for o in c.get("outputs",[])]
    if [c.execution_count for c in cells]!=list(range(1,len(cells)+1)) or any(o.output_type=="error" for o in outs): raise ValueError("Incomplete execution")
    plots=[o.data["application/vnd.plotly.v1+json"] for o in outs if "application/vnd.plotly.v1+json" in o.get("data",{})]
    png=sum("image/png" in o.get("data",{}) for o in outs)
    if len(plots)!=6 or png!=6 or "REPORT_COMPLETE" not in str(nb.cells[-1].outputs): raise ValueError("Missing figure or sentinel")
    if any(p["layout"].get("width",0)<900 or p["layout"].get("height",0)<450 for p in plots): raise ValueError("Unreadable figure")
    return {"status":"PASS","scope":"Aggregate employer case study; no forecasting implementation","source_sha256":digest(DATA),"builder_sha256":digest(__file__),"notebook_sha256":digest(NB),"code_cells":len(cells),"plotly_outputs":len(plots),"png_fallbacks":png,"model_fits":0,"figures":{n:digest(ROOT/"reports/current_research/figures"/(n+".png")) for n in FIGURES}}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--build",action="store_true"); p.add_argument("--check",action="store_true"); p.add_argument("--kernel",default="python3"); a=p.parse_args(); load()
    if a.build: print(json.dumps(build(a.kernel),indent=2))
    elif a.check:
        r=inspect()
        if r!=json.loads(RECEIPT.read_text()): raise ValueError("Publication receipt mismatch")
        print(json.dumps(r,indent=2))
    else: p.error("Select --build or --check")
if __name__=="__main__": main()
