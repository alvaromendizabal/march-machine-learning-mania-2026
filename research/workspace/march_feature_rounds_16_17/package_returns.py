"""User-run packager: verifies both independent scientific reports, no fitting."""
from pathlib import Path
import hashlib,json,os,zipfile

def checked_members(path:Path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or len(names)>80:raise ValueError('Invalid report entries')
        if sum(i.file_size for i in z.infolist())>40_000_000:raise ValueError('Oversized report')
        for i in z.infolist():
            p=Path(i.filename)
            if p.is_absolute() or '..' in p.parts or i.file_size>20_000_000:raise ValueError('Unsafe report member')
        pins=json.loads(z.read('return_integrity.json'))['sha256']
        if set(names)!=set(pins)|{'return_integrity.json'}:raise ValueError('Integrity scope differs')
        for n,h in pins.items():
            if hashlib.sha256(z.read(n)).hexdigest()!=h:raise ValueError('Changed report: '+n)
        summary=json.loads(z.read('summary.json'))
        if summary.get('status')!='COMPLETE' or summary.get('total_comparisons')!=24:raise ValueError('Incomplete scientific experiment')
        return summary

def package(kit:Path|None=None)->Path:
    kit=Path(kit) if kit is not None else Path(__file__).resolve().parent
    reports=kit/'reports';files=[];meta={}
    for rid in ['16','17']:
        path=reports/f'round{rid}/milestone_{rid}_return.zip'
        if not path.is_file() or path.is_symlink():raise FileNotFoundError('Missing completed round '+rid)
        record=json.loads((path.parent/'latest_report.json').read_text())
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['return_sha256']:raise ValueError('Published archive changed')
        summary=checked_members(path)
        if str(summary['round'])!=rid:raise ValueError('Wrong experiment in archive')
        files.append(path);meta[rid]={'sha256':record['return_sha256'],'decision':summary['decision']}
    dest=reports/'rounds_16_17_return.zip';temp=dest.with_suffix('.zip.partial')
    if dest.is_symlink() or temp.is_symlink():raise ValueError('Unsafe output')
    with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
        for path in files:z.write(path,path.name)
        z.writestr('combined_integrity.json',json.dumps(meta,indent=2))
    os.replace(temp,dest);return dest

if __name__=='__main__':print(package())
