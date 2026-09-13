"""Small supervisor: one stage, exclusive lock, hard wall limit, 15-second heartbeats."""
from __future__ import annotations
import argparse
import hashlib
import zipfile
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def failure_bundle(kit:Path, stage:str, error:BaseException, round_id:str) -> Path:
    """Export bounded diagnostics only; never include data, models, or environment secrets."""
    reports=kit/'reports'/('round'+round_id)
    dest=reports/f'milestone_{round_id}_failure.zip';tmp=dest.with_suffix('.zip.partial')
    if dest.is_symlink() or tmp.is_symlink():raise ValueError('Unsafe diagnostic output')
    record={'stage':stage,'error_type':type(error).__name__,'error':str(error),
        'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'python':sys.version,
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in kit.glob('*.py') if not p.is_symlink()}}
    with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('runtime.json',json.dumps(record,indent=2))
        for name in ['failure.json','latest_run.json',f'round{round_id}_{stage}.log']:
            p=reports/name
            if p.is_file() and not p.is_symlink():
                data=p.read_bytes()
                z.writestr(name,data[-2_000_000:])
    tmp.replace(dest)
    return dest


def run_stage(round_id:str,stage:str,max_seconds:int=120) -> None:
    phase='round'+round_id
    if stage not in ('audit','smoke','prepare','evaluate','report') or round_id not in ('18','19'):
        raise ValueError('Invalid stage or phase')
    limits={'audit':120,'smoke':90,'prepare':300,'evaluate':180,'report':120}
    if not 1<=max_seconds<=limits[stage]:
        raise ValueError(f'Stage limit must be 1..{limits[stage]} seconds')
    kit=Path(__file__).resolve().parent
    reports=kit/'reports'/('round'+round_id)
    if reports.is_symlink() or any(p.is_symlink() for p in reports.parents):
        raise ValueError('Unsafe report directory')
    reports.mkdir(parents=True,exist_ok=True)
    if (kit/'reports'/'execution.lock').is_symlink():
        raise ValueError('Unsafe lock file')
    with (kit/'reports'/'execution.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another stage is running; do not launch a second copy')
        env=os.environ.copy()
        for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
            env[k]='2'
        command=[sys.executable,'-u',str(kit/'round_workflow.py'),round_id,stage]
        path=reports/f'{phase}_{stage}.log'
        for leaf in [path,reports/'stage_telemetry.json',reports/'stage_telemetry.json.partial',reports/'failure.json']:
            if leaf.is_symlink():raise ValueError('Unsafe telemetry/log output')
        began=time.monotonic();last=began;last_progress={};partial_line=''
        old_stats=reports/'stage_telemetry.json'
        telemetry=json.loads(old_stats.read_text()) if old_stats.is_file() else {}
        prior_elapsed=sum(v.get('elapsed_seconds',0) for v in telemetry.values())
        peak_rss=0
        # Inherited stdout streams progress live into the notebook/terminal; log captures stderr too.
        p=subprocess.Popen(command,env=env,cwd=kit,start_new_session=True,
                           stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=0)
        import selectors
        selector=selectors.DefaultSelector();selector.register(p.stdout,selectors.EVENT_READ)
        with path.open('ab',buffering=0) as log:
            try:
                while p.poll() is None:
                    now=time.monotonic()
                    try:
                        stat=Path(f'/proc/{p.pid}/status').read_text()
                        rss=int(next(line.split()[1] for line in stat.splitlines() if line.startswith('VmRSS:')))*1024
                        peak_rss=max(peak_rss,rss)
                        if rss>6*1024**3:raise MemoryError('Worker RSS exceeds 6 GiB budget')
                    except (OSError,StopIteration):pass
                    if now-began>max_seconds:
                        os.killpg(p.pid,signal.SIGTERM)
                        try:p.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=3)
                        failure={'status':'TIME_LIMIT','stage':stage,'phase':phase,'limit_seconds':max_seconds,
                                 'completed_checkpoints_preserved':True}
                        (reports/'failure.json').write_text(json.dumps(failure,indent=2))
                        raise TimeoutError(f'Stage stopped at {max_seconds}s; inspect the last completed checkpoint. Do not blindly retry.')
                    for key,_ in selector.select(timeout=.2):
                        b=os.read(key.fd,65536)
                        if b:
                            log.write(b);decoded=b.decode(errors='replace');print(decoded,end='',flush=True)
                            partial_line+=decoded
                            while '\n' in partial_line:
                                line,partial_line=partial_line.split('\n',1)
                                try:
                                    obj=json.loads(line)
                                    if isinstance(obj,dict) and obj.get('event'):last_progress=obj
                                except (ValueError,TypeError):pass
                    if now-last>=15:
                        msg=json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'event':'heartbeat','stage':stage,'phase':phase,
                                        'elapsed_seconds':round(now-began,1),'total_recorded_stage_seconds':round(prior_elapsed+now-began,1),
                                        'worker_peak_rss_mib':round(peak_rss/1024**2,1),'last_worker_progress':last_progress,'hard_limit_seconds':max_seconds})+'\n'
                        print(msg,end='',flush=True);log.write(msg.encode());last=now
                b=p.stdout.read()
                if b:log.write(b);print(b.decode(errors='replace'),end='',flush=True)
                if p.returncode:
                    if not (reports/'failure.json').exists():
                        (reports/'failure.json').write_text(json.dumps({'status':'STOP','stage':stage,'exit_code':p.returncode,'log':str(path)}))
                    raise RuntimeError(f'{stage} failed (exit {p.returncode}). See {path} and reports/failure.json.')
            except BaseException as error:
                try:
                    print('Diagnostic archive:', failure_bundle(kit,stage,error,round_id),flush=True)
                except Exception as bundle_error:
                    print('Diagnostic export failed:',type(bundle_error).__name__,flush=True)
                raise
            finally:
                telemetry[stage]={'elapsed_seconds':round(time.monotonic()-began,3),'peak_worker_rss_mib':round(peak_rss/1024**2,2),
                                  'returncode':p.poll(),'last_progress':last_progress}
                temp=old_stats.with_suffix('.json.partial');temp.write_text(json.dumps(telemetry,indent=2));temp.replace(old_stats)
                selector.close()
                if p.poll() is None:
                    os.killpg(p.pid,signal.SIGTERM)
                    try:p.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=3)
                p.stdout.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('round',choices=['18','19'])
    parser.add_argument('stage',choices=['audit','smoke','prepare','evaluate','report'])
    parser.add_argument('--max-seconds',type=int,default=120)
    a=parser.parse_args();run_stage(a.round,a.stage,a.max_seconds)
