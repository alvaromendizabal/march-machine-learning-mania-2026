"""Copy only a report-only showcase into a separate initialized Git checkout."""
from pathlib import Path
import argparse,json,shutil,hashlib,subprocess,re
ALLOW={'README.md','RIGHTS.md','CITATION.cff','.gitignore','docs/CASE_STUDY.md','docs/EXPERIMENT_LEDGER.md','docs/DISCLOSURE.md',
 'data/validation_metrics.csv','data/evidence_sources.json','notebooks/portfolio_results.ipynb','results.html'}
def stage(source,dest):
    source=Path(source).absolute();dest=Path(dest).expanduser().absolute()
    if not (dest/'.git').is_dir() or dest.is_symlink():raise ValueError('Separate initialized public checkout required')
    def git(*a):return subprocess.check_output(['git','-C',str(dest),*a],text=True).strip()
    remote=git('remote','get-url','origin').removesuffix('.git')
    if remote not in ['https://github.com/alvaromendizabal/march-mania-portfolio','git@github.com:alvaromendizabal/march-mania-portfolio']:raise ValueError('Wrong public destination')
    if git('status','--porcelain'):raise ValueError('Destination has changes; review rather than overwrite')
    existing=set(git('ls-files').splitlines())
    if existing-ALLOW:raise ValueError('Unreviewed existing public files; do not use the original research repository')
    found={str(p.relative_to(source)) for p in source.rglob('*') if p.is_file() and '.ipynb_checkpoints' not in p.parts}
    if found-ALLOW:raise ValueError('Unexpected files in public source: '+str(found-ALLOW))
    for name in sorted(found):
        p=source/name
        if p.is_symlink() or any(a.is_symlink() for a in p.parents) or p.stat().st_size>15_000_000:raise ValueError('Unsafe public file')
        text=p.read_text(errors='replace')
        if re.search(r'(?:AKIA|ASIA)[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{20,}|X-Amz-Signature=[a-fA-F0-9]{32,}',text):raise ValueError('Possible credential in public material; stop')
        q=dest/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
    print('PUBLIC_FILES_COPIED_FOR_REVIEW; no Git stage/commit/push occurred.')
    print('\n'.join(sorted(found)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',default=str(Path(__file__).resolve().parents[1]/'public_portfolio'));p.add_argument('--destination',required=True);a=p.parse_args();stage(a.source,a.destination)
