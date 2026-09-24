"""Render reviewed aggregate frontier evidence. No forecasting training or inference."""
from __future__ import annotations
import argparse, base64, hashlib, io, json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"reports/frontier_research/evidence.json"
NB=ROOT/"portfolio/frontier_research.ipynb"
RECEIPT=ROOT/"reports/frontier_research/publication.json"
FIGURES=["score_boundary","score_progression","family_gain","family_stability","candidate_scope","frontier_status"]

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def validate(d):
    if d["schema"]!=1: raise ValueError("Unknown schema")
    s=d["scores"]; c=d["latest_candidate"]; p=d["provenance"]
    if s["published_2026_winner"]!=0.1097454 or s["retained_private_champion"]!=0.1072824 or s["retained_submission_ref"]!="56500599": raise ValueError("Score identity changed")
    if s["stretch_target"]!=0.09 or s["remaining_absolute_reduction"]!=0.0172824: raise ValueError("Target boundary changed")
    if c["decision"]!="CANDIDATE_READY_NOT_SUBMITTED" or c["candidate_score"] is not None: raise ValueError("Candidate status changed")
    if c["selected_family"]!="volume_plus_differences": raise ValueError("Selected family changed")
    if abs(c["selection_gain"]-0.003781018951485665)>1e-15 or c["selection_wins"]!=5 or c["selection_seasons"]!=6: raise ValueError("Selection evidence changed")
    if abs(c["worst_season_gain"]+0.0011233103762186836)>1e-15: raise ValueError("Selected stability changed")
    if abs(c["all_residual_gain"]-0.004998188865624087)>1e-15 or abs(c["all_residual_worst_season_gain"]+0.0031221822937750054)>1e-15: raise ValueError("Rejected panel evidence changed")
    if c["changed_mens_rows"]!=2278 or c["protected_rows"]!=129855 or c["women_rows_byte_identical"]!=65703: raise ValueError("Preservation evidence changed")
    if c["known_2026_outcomes_used"] or c["market_inputs_used_for_selection"] or c["market_inputs_used_for_training"]: raise ValueError("Leakage boundary changed")
    if c["model_integrity_tests"]!=12 or c["inline_plotly_outputs"]!=6: raise ValueError("Validation evidence changed")
    if p["futures_classification"]!="PINNED_POST_COMPETITION_REPRODUCTION_NOT_PROSPECTIVELY_VERIFIED" or p["independently_rebuilt_raw_2026_market_observations"]: raise ValueError("Provenance boundary changed")
    if len(d["reproduction_matrix"])<12: raise ValueError("Frontier matrix unexpectedly incomplete")
    for h in [c["candidate_sha256"],d["source_return"]["sha256"]]:
        if len(h)!=64 or any(ch not in "0123456789abcdef" for ch in h): raise ValueError("Invalid checksum")
    return d

def load(): return validate(json.loads(DATA.read_text()))

def chart(name,title,labels,values,ylabel,orientation="v"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import plotly.graph_objects as go
    from IPython.display import display
    labels=[str(x) for x in labels]; values=[float(x) for x in values]
    if orientation=="h":
        fig=go.Figure(go.Bar(x=values,y=labels,orientation="h",text=[f"{v:+.6f}" if abs(v)<.02 else f"{v:,.0f}" for v in values],textposition="auto"))
        png,ax=plt.subplots(figsize=(10,5.6),layout="constrained"); ax.barh(labels,values); ax.set_xlabel(ylabel)
    else:
        fig=go.Figure(go.Bar(x=labels,y=values,text=[f"{v:.7f}" if abs(v)<1 else f"{v:,.0f}" for v in values],textposition="outside"))
        png,ax=plt.subplots(figsize=(10,5.3),layout="constrained"); ax.bar(np.arange(len(labels)),values); ax.set_xticks(np.arange(len(labels)),labels,rotation=18,ha="right"); ax.set_ylabel(ylabel)
    fig.update_layout(title=title,width=960,height=530,xaxis_type="category" if orientation=="v" else None,yaxis_title=ylabel if orientation=="v" else None,font_size=13,margin=dict(l=90 if orientation=="v" else 220,r=30,t=85,b=115))
    ax.set_title(title,pad=18); ax.ticklabel_format(axis="x" if orientation=="h" else "y",useOffset=False,style="plain")
    stream=io.BytesIO(); png.savefig(stream,format="png",dpi=120); plt.close(png); image=stream.getvalue()
    dest=ROOT/"reports/frontier_research/figures"/(name+".png"); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(image)
    display({"application/vnd.plotly.v1+json":json.loads(fig.to_json()),"image/png":base64.b64encode(image).decode()},raw=True)

def build(kernel):
    import nbformat as nbf
    from nbclient import NotebookClient
    md,code=nbf.v4.new_markdown_cell,nbf.v4.new_code_cell
    cells=[
      md("# Frontier research update | NCAA tournament forecasting\n**Alvaro Mendizabal · employer-facing ML engineering and research case study**\n\nThe strongest retained private post-competition release is **0.1072824 Brier**, compared with the published 2026 winning benchmark of **0.1097454**. The active stretch target is **0.09**. These are retrospective benchmark comparisons, not original competition placements. This notebook publishes aggregate evidence only; it does not reproduce the private forecasting system."),
      code("from pathlib import Path\nimport sys, pandas as pd\nroot=Path.cwd()\nif not (root/'portfolio').is_dir(): root=root.parent\nsys.path.insert(0,str(root/'portfolio'))\nfrom frontier_research import load,chart\nd=load(); s=d['scores']; c=d['latest_candidate']; m=d['reproduction_matrix']\nprint({'champion':s['retained_private_champion'],'selected_family':c['selected_family'],'candidate_score':c['candidate_score']})"),
      md("## 1. Competitive boundary\nThe private research program is numerically below the published 2026 winning benchmark, but the comparison is retrospective. Moving from 0.1072824 to 0.09 still requires a **0.0172824** absolute Brier reduction, so the remaining program prioritizes structural capability gains rather than cosmetic tuning."),
      code("chart('score_boundary','Current score boundary and stretch target',['0.09 target','Private champion','Published winner'],[s['stretch_target'],s['retained_private_champion'],s['published_2026_winner']],'Brier (lower is better)')"),
      md("## 2. Verified score progression\nThe public case study previously stopped at 0.1089408. Private research subsequently reached 0.1072824. Scored improvements remain separate from unscored research candidates."),
      code("chart('score_progression','Verified post-competition score progression',['Simplified','Margin ensemble','Futures public','Private champion'],[0.1098691,0.1094899,0.1089408,s['retained_private_champion']],'Brier (lower is better)')"),
      md("## 3. Chronology-safe residual-family selection\nThe latest candidate adds a capability the prior system did not have: selection among coherent residual representations using season-grouped historical evidence only. Futures inputs do not fit the residual model or choose its representation."),
      code("families=['Base only','Absolute strength','Possession volume','Residual differences','Strength + differences','Strength + volume','Volume + differences','All residual']\ngains=[0.0,0.002425228446914063,0.0015206271330946985,0.0001331989475467643,0.0017326999586218805,0.003995815372199257,c['selection_gain'],c['all_residual_gain']]\nchart('family_gain','Residual-family historical gain',families,gains,'Brier improvement vs base',orientation='h')"),
      md("## 4. Stability over raw mean gain\nThe full residual panel had the largest mean gain but violated the predeclared worst-season guardrail. `volume_plus_differences` sacrificed some mean gain for better transfer stability and became the frozen challenger."),
      code("families=['Absolute strength','Possession volume','Volume + differences','Strength + volume','All residual']\nworst=[0.00007867586776166835,-0.0010937375543707273,c['worst_season_gain'],-0.002863295102808222,c['all_residual_worst_season_gain']]\nchart('family_stability','Worst recent-season movement by residual family',families,worst,'Worst-season Brier gain (higher is safer)',orientation='h')"),
      md("## 5. Frozen candidate scope\nThe candidate changes only the approved men’s scope, does not overwrite the scored champion, preserves every women’s row, and made no Kaggle submission in the candidate-build milestone."),
      code("chart('candidate_scope','Frozen candidate scope and preservation',['Changed men rows','Protected rows','Women rows preserved'],[c['changed_mens_rows'],c['protected_rows'],c['women_rows_byte_identical']],'Prediction rows')"),
      md("## 6. Leading-solution reproduction matrix\nA mechanism is not marked recreated merely because it was discussed. The public matrix distinguishes validated adaptations, rejected reproductions, operational prospective infrastructure, provenance-limited adaptations, and missing frontier capabilities."),
      code("from collections import Counter\nstatus=Counter(x['status'] for x in m)\ngroups={'Validated / adapted':sum(status[k] for k in ['ADAPTED_VALIDATED','VALIDATED_HISTORICALLY']),'Rejected':status['REJECTED'],'Operational prospective':sum(status[k] for k in ['OPERATIONAL','OPERATIONAL_GATED','OPERATIONAL_PARTIAL']),'Provenance-limited':status['ADAPTED_PROVENANCE_LIMITED'],'Missing frontier':status['MISSING_FRONTIER']}\nchart('frontier_status','Leading-solution reproduction and frontier status',list(groups),list(groups.values()),'Mechanisms')\ndisplay(pd.DataFrame(m)[['mechanism','status','public_note']])"),
      md("## 7. Provenance and next decision\nThe 2026 market transformations were independently rebuilt, but the original market observations were pinned from a post-competition public artifact rather than independently reconstructed from raw timestamped pre-deadline responses. They remain a fixed retrospective component and are excluded from residual training and selection.\n\nThe exact frozen challenger should be scored once. A gain promotes it and triggers error decomposition against the new champion. A non-improvement ends ordinary residual refinement and moves directly to women-specific reconstruction, prospective roster/availability data, and a heterogeneous OOF ensemble. The 2027 raw-first collector and cutoff-freeze design is the stronger prospective test."),
      code("assert c['decision']=='CANDIDATE_READY_NOT_SUBMITTED'\nassert c['candidate_score'] is None\nassert c['known_2026_outcomes_used'] is False\nassert c['market_inputs_used_for_selection'] is False and c['market_inputs_used_for_training'] is False\nprint('FRONTIER_REPORT_COMPLETE — aggregate evidence only; no training or submission')")
    ]
    nb=nbf.v4.new_notebook(cells=cells,metadata={"kernelspec":{"name":kernel,"display_name":"Python 3","language":"python"}})
    NotebookClient(nb,timeout=90,kernel_name=kernel,resources={"metadata":{"path":str(ROOT)}}).execute()
    NB.write_text(nbf.writes(nb)); r=inspect(); RECEIPT.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n"); return r

def inspect():
    import nbformat
    nb=nbformat.read(NB,as_version=4); nbformat.validate(nb)
    cells=[c for c in nb.cells if c.cell_type=="code"]; outs=[o for c in cells for o in c.get("outputs",[])]
    if [c.execution_count for c in cells]!=list(range(1,len(cells)+1)) or any(o.output_type=="error" for o in outs): raise ValueError("Incomplete notebook execution")
    plots=[o.data["application/vnd.plotly.v1+json"] for o in outs if "application/vnd.plotly.v1+json" in o.get("data",{})]
    png=sum("image/png" in o.get("data",{}) for o in outs)
    if len(plots)!=6 or png!=6 or "FRONTIER_REPORT_COMPLETE" not in str(nb.cells[-1].outputs): raise ValueError("Missing plot or sentinel")
    if any(p["layout"].get("width",0)<900 or p["layout"].get("height",0)<450 for p in plots): raise ValueError("Unreadable figure")
    return {"status":"PASS","scope":"Aggregate frontier case study; no forecasting implementation","source_sha256":digest(DATA),"builder_sha256":digest(__file__),"notebook_sha256":digest(NB),"code_cells":len(cells),"plotly_outputs":len(plots),"png_fallbacks":png,"model_fits":0,"submissions":0,"figures":{n:digest(ROOT/"reports/frontier_research/figures"/(n+".png")) for n in FIGURES}}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--build",action="store_true"); p.add_argument("--check",action="store_true"); p.add_argument("--kernel",default="python3"); a=p.parse_args(); load()
    if a.build: print(json.dumps(build(a.kernel),indent=2))
    elif a.check:
        r=inspect()
        if r!=json.loads(RECEIPT.read_text()): raise ValueError("Publication receipt mismatch")
        print(json.dumps(r,indent=2))
    else: p.error("Select --build or --check")
if __name__=="__main__": main()
