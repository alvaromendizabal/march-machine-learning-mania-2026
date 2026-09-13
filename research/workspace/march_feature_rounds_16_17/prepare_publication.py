"""Optional user-run archival copy AFTER both experiments, never changes Git itself."""
from pathlib import Path
import argparse,hashlib,json,shutil
from package_returns import package

def main():
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');a=p.parse_args()
    kit=Path(__file__).resolve().parent
    dest=Path.home()/'march-machine-learning-mania-2026/research_kits/march_feature_rounds_16_17'
    names=json.loads((kit/'MANIFEST.json').read_text())['sha256']
    selected=[n for n in names if Path(n).suffix in {'.py','.ipynb','.md','.json','.csv'}]
    print('Code-only publication destination:',dest)
    for n in selected:print(n)
    if not a.write:
        print('Preview only. Review paths and both experiment reports before --write.');return
    package(kit)  # verifies both completed reports without fitting; no performance gate required
    if dest.exists() or dest.is_symlink():raise ValueError('Destination exists; do not overwrite archived work')
    if any(p.is_symlink() for p in dest.parents):raise ValueError('Unsafe publication destination')
    dest.mkdir(parents=True)
    try:
        for n in selected:
            src=kit/n;out=dest/n
            if src.is_symlink() or '..' in Path(n).parts:raise ValueError('Unsafe source')
            out.parent.mkdir(parents=True,exist_ok=True)
            if src.suffix=='.ipynb':
                nb=json.loads(src.read_text())
                for c in nb['cells']:
                    if c['cell_type']=='code':c['outputs']=[];c['execution_count']=None
                out.write_text(json.dumps(nb,indent=1,ensure_ascii=False)+'\n')
            else:
                if hashlib.sha256(src.read_bytes()).hexdigest()!=names[n]:raise ValueError('Edited source requires review: '+n)
                shutil.copy2(src,out)
        (dest/'MANIFEST.json').write_text(json.dumps({'sha256':{n:hashlib.sha256((dest/n).read_bytes()).hexdigest() for n in selected}},indent=2))
        print('Archival copy prepared. Review git diff and file list; no commit or push performed.')
    except BaseException:
        print('Partial publication copy preserved at',dest,'; review rather than overwriting automatically.')
        raise
if __name__=='__main__':main()
