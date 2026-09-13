"""Combine the two small, integrity-verified scientific reports, without private data."""
import hashlib,json,os,zipfile
from pathlib import Path

def package(kit=None):
    kit=Path(kit or Path(__file__).resolve().parent);reports=kit/'reports'
    paths=[reports/f'round{r}'/f'milestone_{r}_return.zip' for r in ['14','15']]
    for p in paths:
        if not p.is_file() or p.is_symlink():raise ValueError('Missing/unsafe report: '+str(p))
        record=json.loads((p.parent/'latest_report.json').read_text())
        if hashlib.sha256(p.read_bytes()).hexdigest()!=record['return_sha256']:raise ValueError('Report checksum changed')
        with zipfile.ZipFile(p) as z:
            pins=json.loads(z.read('return_integrity.json'))['sha256']
            if set(z.namelist())!=set(pins)|{'return_integrity.json'}:raise ValueError('Report scope changed')
            for n,h in pins.items():
                if hashlib.sha256(z.read(n)).hexdigest()!=h:raise ValueError('Report member changed')
    dest=reports/'rounds_14_15_return.zip';tmp=dest.with_suffix('.zip.partial')
    if dest.is_symlink() or tmp.is_symlink():raise ValueError('Unsafe combined output')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,p.name)
    os.replace(tmp,dest);return dest
if __name__=='__main__':print(package())
