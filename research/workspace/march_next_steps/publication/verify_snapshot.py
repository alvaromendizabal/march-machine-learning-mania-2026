"""Read-only verification of listed source/staged files; no remote query or Git writes."""
from pathlib import Path
import hashlib,json,argparse,subprocess

def verify(checkout,home):
 c=Path(checkout).expanduser().resolve();h=Path(home).expanduser().resolve()
 receipt=json.loads((c/'PRIVATE_SNAPSHOT.json').read_text());bad=[]
 for row in receipt['files']:
  rel=Path(row['path'])
  if rel.is_absolute() or '..' in rel.parts or rel.parts[0]!='research':raise ValueError('Invalid snapshot path')
  out=c/rel;src=h/Path(*rel.parts[1:])
  for label,p,key in [('staged',out,'staged_sha256'),('live_source',src,'source_sha256')]:
   if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=row[key]:bad.append({'path':str(rel),'check':label})
 def git(*a):return subprocess.check_output(['git','-C',str(c),*a],text=True).strip()
 result={'listed_source_files':len(receipt['files']),'mismatches':bad,'head':git('rev-parse','HEAD'),
 'fetched_origin_main':git('rev-parse','origin/main'),'working_tree_clean':not bool(git('status','--porcelain')),
 'scope':'Listed source files only; new unlisted files, raw data, model storage, current remote status and permissions are not certified'}
 print(json.dumps(result,indent=2))
 if bad or not result['working_tree_clean'] or result['head']!=result['fetched_origin_main']:raise SystemExit('REVIEW_REQUIRED')
 print('LISTED_SOURCE_SNAPSHOT_MATCHES')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--checkout',required=True);p.add_argument('--home',default=str(Path.home()));a=p.parse_args();verify(a.checkout,a.home)
