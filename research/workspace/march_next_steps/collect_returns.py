"""User-run collection of completed receipts only. No fitting or network requests."""
from pathlib import Path
import hashlib,json,os,zipfile

def main():
    root=Path(__file__).resolve().parent;out=root/'reports';out.mkdir(exist_ok=True)
    inputs={'research_rounds':root/'rounds_20_21/reports/rounds_20_21_return.zip',
            'publication':Path.home()/'march_publication/publication_return.zip',
            'publication_diagnostic':Path.home()/'march_publication/publication_diagnostic.zip'}
    status=[];members=[]
    for label,p in inputs.items():
        if not p.is_file():status.append({'component':label,'status':'MISSING'});continue
        if p.is_symlink() or p.stat().st_size>50_000_000:raise ValueError('Unsafe/oversized receipt archive')
        with zipfile.ZipFile(p) as z:
            if z.testzip() is not None:raise ValueError('Corrupt receipt archive')
        status.append({'component':label,'status':'PRESENT','sha256':hashlib.sha256(p.read_bytes()).hexdigest()});members.append(p)
    dest=out/'next_steps_return.zip';tmp=dest.with_suffix('.zip.partial')
    if dest.is_symlink() or tmp.is_symlink():raise ValueError('Unsafe collection output')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for p in members:z.write(p,p.name)
        z.writestr('collection_status.json',json.dumps(status,indent=2))
    os.replace(tmp,dest);print(json.dumps(status,indent=2));print('Return:',dest)
if __name__=='__main__':main()
