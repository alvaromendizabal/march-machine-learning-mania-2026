"""Collect two independent completed reports; no model fitting or Git operations."""
from pathlib import Path
import json,hashlib,zipfile,os

def package(kit):
    kit=Path(kit);reports=kit/'reports';payload={};status=[]
    for r in ['20','21']:
        path=reports/f'round{r}/milestone_{r}_return.zip';record=path.parent/'latest_report.json'
        if not path.is_file() or not record.is_file():status.append({'round':r,'status':'MISSING'});continue
        if path.is_symlink():raise ValueError('Symlink report refused')
        h=hashlib.sha256(path.read_bytes()).hexdigest()
        if h!=json.loads(record.read_text())['return_sha256']:raise ValueError('Published report changed')
        payload[path.name]=path;status.append({'round':r,'status':'COMPLETE','sha256':h})
    dest=reports/'rounds_20_21_return.zip';tmp=dest.with_suffix('.zip.partial')
    if dest.is_symlink() or tmp.is_symlink():raise ValueError('Unsafe return destination')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for n,p in payload.items():z.write(p,n)
        z.writestr('collection_status.json',json.dumps(status,indent=2))
    os.replace(tmp,dest);print(json.dumps(status,indent=2));print('Return:',dest);return dest
if __name__=='__main__':package(Path(__file__).resolve().parent)
