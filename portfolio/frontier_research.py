"""Validate and re-execute the public-safe owned-data frontier notebook."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"reports/frontier_research/evidence.json"
EXP=ROOT/"portfolio/post_merge_experiments.csv"
OWN=ROOT/"portfolio/supplemental_source_ownership.csv"
NB=ROOT/"portfolio/frontier_research.ipynb"
RECEIPT=ROOT/"reports/frontier_research/publication.json"

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load():
    import pandas as pd
    d=json.loads(DATA.read_text())
    exp=pd.read_csv(EXP)
    own=pd.read_csv(OWN)
    return validate(d,exp,own)

def validate(d,exp,own):
    if d.get("schema")!=2: raise ValueError("Unknown schema")
    s=d["scores"]; q=d["scope"]; pub=d["publication"]
    expected={
      "published_2026_winner":0.1097454,
      "previous_retained":0.1051853186,
      "owned_external_consensus":0.1043512820,
      "canonical_aws_reproduced":0.1033437336,
      "pending_local_candidate":0.1027974461,
      "stretch_target":0.09,
      "remaining_absolute_reduction":0.0133437336,
    }
    for k,v in expected.items():
        if abs(float(s[k])-v)>1e-12: raise ValueError(f"Score boundary changed: {k}")
    if q["men_first_season"]!=2003 or q["women_first_season"]!=2010 or not q["post_competition_research"] or q["pending_candidate_promoted"]:
        raise ValueError("Scope boundary changed")
    if pub["model_fits"]!=0 or pub["submissions"]!=0 or pub["private_predictions_published"] or pub["private_weights_published"]:
        raise ValueError("Public/private boundary changed")
    canonical=exp.loc[exp["canonical"].astype("string").str.lower().eq("true")]
    if len(canonical)!=1 or abs(float(canonical.iloc[0]["audit_brier"])-s["canonical_aws_reproduced"])>1e-12:
        raise ValueError("Canonical experiment mismatch")
    pending=exp.loc[exp["status"].eq("PENDING_AWS")]
    if len(pending)!=1 or abs(float(pending.iloc[0]["audit_brier"])-s["pending_local_candidate"])>1e-12:
        raise ValueError("Pending candidate mismatch")
    needed={"AP Poll","Dated BartTorvik","ESPN game predictor/BPI","WNCAA NET","KenPom exact"}
    if not needed.issubset(set(own["source"])): raise ValueError("Ownership matrix incomplete")
    if not {"OWNED","OPEN_GAP","TIMING_BLOCKED"}.issubset(set(own["state"])): raise ValueError("Ownership state coverage incomplete")
    return d,exp,own

def inspect():
    import nbformat
    nb=nbformat.read(NB,as_version=4); nbformat.validate(nb)
    cells=[c for c in nb.cells if c.cell_type=="code"]
    outs=[o for c in cells for o in c.get("outputs",[])]
    if [c.execution_count for c in cells]!=list(range(1,len(cells)+1)): raise ValueError("Incomplete execution counts")
    if any(o.output_type=="error" for o in outs): raise ValueError("Notebook contains errors")
    plots=[o for o in outs if "application/vnd.plotly.v1+json" in o.get("data",{})]
    if len(plots)!=4: raise ValueError("Expected four Plotly outputs")
    if "PUBLIC_OWNED_DATA_FRONTIER_COMPLETE" not in str(nb.cells[-1].outputs): raise ValueError("Missing publication sentinel")
    return {
      "status":"PASS",
      "scope":"Aggregate owned-data frontier case study; no forecasting implementation",
      "evidence_sha256":digest(DATA),
      "experiments_sha256":digest(EXP),
      "ownership_sha256":digest(OWN),
      "code_cells":len(cells),
      "plotly_outputs":len(plots),
      "model_fits":0,
      "submissions":0
    }

def build(kernel):
    import nbformat
    from nbclient import NotebookClient
    nb=nbformat.read(NB,as_version=4)
    NotebookClient(nb,timeout=120,kernel_name=kernel,resources={"metadata":{"path":str(ROOT)}}).execute()
    NB.write_text(nbformat.writes(nb))
    r=inspect(); RECEIPT.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n"); return r

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--build",action="store_true")
    p.add_argument("--check",action="store_true")
    p.add_argument("--kernel",default="python3")
    a=p.parse_args(); load()
    if a.build: print(json.dumps(build(a.kernel),indent=2))
    elif a.check:
        r=inspect(); saved=json.loads(RECEIPT.read_text())
        if r!=saved: raise ValueError("Publication receipt mismatch")
        print(json.dumps(r,indent=2))
    else: p.error("Select --build or --check")
if __name__=="__main__": main()
