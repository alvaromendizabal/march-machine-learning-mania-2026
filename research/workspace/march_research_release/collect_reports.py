"""Package independently complete reports; never retrain to obtain an archive."""
from pathlib import Path
import hashlib,json,zipfile,io,os

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(p):
    if p.is_symlink() or not p.is_file():raise ValueError('Missing/unsafe archive: '+str(p))
    if p.stat().st_size>50_000_000:raise ValueError('Archive exceeds collection budget')
    with zipfile.ZipFile(p) as z:
        infos=z.infolist();names=z.namelist()
        if len(names)!=len(set(names)) or sum(i.file_size for i in infos)>100_000_000:raise ValueError('Unsafe archive size/list')
        for n in names:
            if '\\' in n or Path(n).is_absolute() or '..' in Path(n).parts:raise ValueError('Unsafe archive path')
        pins=json.loads(z.read('return_integrity.json'))['sha256']
        if set(names)!=set(pins)|{'return_integrity.json'}:raise ValueError('Incomplete integrity scope')
        for n,h in pins.items():
            if hashlib.sha256(z.read(n)).hexdigest()!=h:raise ValueError('Corrupt archive member '+n)
    return digest(p)
def collect(root=None,home=None):
    root=Path(root or Path(__file__).resolve().parent);home=Path(home or Path.home());dest=root/'reports/research_return.zip';dest.parent.mkdir(parents=True,exist_ok=True)
    selections={
      '16':root/'repair_16_17/reports/round16/milestone_16_return.zip',
      '17':home/'march_feature_rounds_16_17/reports/round17/milestone_17_return.zip',
      '18':root/'rounds_18_19/reports/round18/milestone_18_return.zip',
      '19':root/'rounds_18_19/reports/round19/milestone_19_return.zip'}
    status={'complete':[],'missing':[],'scope':'Only finished individual reports are included; missing is never scored as success'}
    tmp=dest.with_suffix('.zip.partial')
    if dest.is_symlink() or tmp.is_symlink():raise ValueError('Unsafe destination')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for rid,p in selections.items():
            if not p.exists():status['missing'].append(rid);continue
            h=verify(p)
            with zipfile.ZipFile(p) as report:
                summary=json.loads(report.read('summary.json'))
                if summary.get('status')!='COMPLETE' or str(summary.get('round'))!=rid:raise ValueError('Report is not a completed expected round '+rid)
            z.write(p,'milestone_'+rid+'_return.zip');status['complete'].append({'round':rid,'sha256':h})
        z.writestr('collection_status.json',json.dumps(status,indent=2))
    os.replace(tmp,dest);return dest,status
if __name__=='__main__':
    p,s=collect();print(json.dumps(s,indent=2));print(p)
