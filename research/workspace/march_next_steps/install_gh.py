"""Optional user-run GitHub CLI installation into ~/.local/bin, not the ML environment.
Fetches the current official stable Linux release and verifies its SHA-256 manifest.
No sudo, no token, no account operations, no execution of downloaded code here.
"""
from pathlib import Path
import hashlib,io,json,os,platform,re,tarfile,time,urllib.request

def fetch(url,limit):
    if not url.startswith(('https://api.github.com/repos/cli/cli/','https://github.com/cli/cli/releases/')):raise ValueError('Unexpected release URL')
    req=urllib.request.Request(url,headers={'User-Agent':'March-Mania-user-run-CLI-setup','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=30) as f:
        data=f.read(limit+1)
    if len(data)>limit:raise ValueError('Release download exceeds limit')
    return data

def main():
    dest=Path.home()/'.local/bin/gh'
    if dest.exists():raise SystemExit('Existing ~/.local/bin/gh preserved. Use it or review locally; no overwrite.')
    if platform.system()!='Linux':raise SystemExit('Use this script only in the existing AWS Linux JupyterLab terminal.')
    arch={'x86_64':'amd64','aarch64':'arm64'}.get(platform.machine())
    if not arch:raise SystemExit('Unsupported architecture')
    release=json.loads(fetch('https://api.github.com/repos/cli/cli/releases/latest',2_000_000))
    tag=release['tag_name']
    if not re.fullmatch(r'v\d+\.\d+\.\d+',tag) or release['prerelease'] or release['draft']:raise ValueError('Unexpected release metadata')
    stem='gh_'+tag[1:];archive=stem+'_linux_'+arch+'.tar.gz';checksum=stem+'_checksums.txt'
    assets={x['name']:x['browser_download_url'] for x in release['assets']}
    if archive not in assets or checksum not in assets:raise ValueError('Official release assets unavailable')
    raw=fetch(assets[archive],80_000_000);sums=fetch(assets[checksum],1_000_000).decode()
    entries={line.split()[-1].lstrip('*'):line.split()[0] for line in sums.splitlines() if len(line.split())==2}
    if entries.get(archive)!=hashlib.sha256(raw).hexdigest():raise ValueError('GitHub CLI checksum mismatch')
    member=stem+'_linux_'+arch+'/bin/gh'
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
        info=tar.getmember(member)
        if not info.isfile() or info.size>150_000_000:raise ValueError('Invalid CLI binary member')
        binary=tar.extractfile(info).read()
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.is_symlink() or any(p.is_symlink() for p in dest.parents):raise ValueError('Unsafe install path')
    # Exclusive creation prevents replacing an existing binary in concurrent runs.
    with dest.open('xb') as f:f.write(binary)
    dest.chmod(0o700)
    receipt={'release':tag,'archive_sha256':hashlib.sha256(raw).hexdigest(),'binary_sha256':hashlib.sha256(binary).hexdigest(),
             'source':'Official cli/cli stable release; checksum verification, not an attestation claim','installed':str(dest)}
    (dest.parent/'gh_install_receipt.json').write_text(json.dumps(receipt,indent=2))
    print('GITHUB_CLI_INSTALLED:',tag,'\nRun: export PATH="$HOME/.local/bin:$PATH"')
if __name__=='__main__':main()
