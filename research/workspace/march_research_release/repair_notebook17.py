"""Replace only the failed packaging cell; keep executed science and charts intact."""
from pathlib import Path
import json,hashlib,datetime,os
OLD="""from package_returns import package
combined = package(KIT)
display(FileLink(str(combined.relative_to(KIT))))
print("Return:", combined)
print("Save this notebook and keep both private run directories.")
"""
NEW="""# Independent scientific report: do not rerun completed work to package it.
individual = KIT / 'reports/round17/milestone_17_return.zip'
assert individual.is_file(), 'Expected saved round 17 report is missing.'
display(FileLink(str(individual.relative_to(KIT))))
print('Round 17 is complete. Combined export is optional and may be partial.')
# Run march_research_release/collect_reports.py to collect all available reports.
"""
def update(home=None):
    home=Path(home or Path.home());kit=home/'march_feature_rounds_16_17';p=kit/'17_blocks_and_foul_pressure.ipynb'
    if not p.is_file() or p.is_symlink():raise ValueError('Canonical notebook missing/unsafe')
    raw=p.read_bytes();n=json.loads(raw);hits=[c for c in n['cells'] if c['cell_type']=='code' and ''.join(c['source'])==OLD]
    if not hits:
        if any(''.join(c.get('source',[]))==NEW for c in n['cells']):return {'status':'ALREADY_UPDATED','models_fitted':0}
        raise ValueError('Packaging source differs; preserve manual edits and inspect')
    if len(hits)!=1:raise ValueError('Expected exactly one packaging cell')
    digest=hashlib.sha256(raw).hexdigest();backup=kit/'reports/notebook_backups'/digest;backup.mkdir(parents=True,exist_ok=True)
    dest=backup/p.name
    if dest.exists() and dest.read_bytes()!=raw:raise ValueError('Backup collision')
    dest.write_bytes(raw)
    hits[0].update(source=NEW.splitlines(True),execution_count=None,outputs=[])
    temp=p.with_suffix('.ipynb.partial')
    if temp.is_symlink():raise ValueError('Unsafe temporary notebook')
    temp.write_text(json.dumps(n,indent=1)+'\n');os.replace(temp,p)
    return {'status':'PACKAGING_CELL_UPDATED','original_notebook_sha256':digest,
        'scientific_code_changed':False,'existing_charts_preserved':True,'models_fitted':0}
if __name__=='__main__':print(json.dumps(update(),indent=2))
