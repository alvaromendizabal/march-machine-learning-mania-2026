"""Small supervisor: one stage, exclusive lock, hard wall limit, 15-second heartbeats."""
from __future__ import annotations
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def run_stage(stage:str,phase:str='win_strength',max_seconds:int=120) -> None:
    if stage not in ('prepare','evaluate','report') or phase != 'win_strength':
        raise ValueError('Invalid stage or phase')
    limits={'prepare':300,'evaluate':180,'report':120}
    if not 1<=max_seconds<=limits[stage]:
        raise ValueError(f'Stage limit must be 1..{limits[stage]} seconds')
    kit=Path(__file__).resolve().parent
    reports=kit/'reports'
    if reports.is_symlink() or any(p.is_symlink() for p in reports.parents):
        raise ValueError('Unsafe report directory')
    reports.mkdir(exist_ok=True)
    if (reports/'execution.lock').is_symlink():
        raise ValueError('Unsafe lock file')
    with (reports/'execution.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another stage is running; do not launch a second copy')
        env=os.environ.copy()
        for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
            env[k]='2'
        command=[sys.executable,'-u',str(kit/'strength_workflow.py'),stage]
        path=reports/f'{phase}_{stage}.log'
        began=time.monotonic();last=began
        # Inherited stdout streams progress live into the notebook/terminal; log captures stderr too.
        p=subprocess.Popen(command,env=env,cwd=kit,start_new_session=True,
                           stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=0)
        import selectors
        selector=selectors.DefaultSelector();selector.register(p.stdout,selectors.EVENT_READ)
        with path.open('ab',buffering=0) as log:
            try:
                while p.poll() is None:
                    now=time.monotonic()
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
                            log.write(b);print(b.decode(errors='replace'),end='',flush=True)
                    if now-last>=15:
                        msg=json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'event':'heartbeat','stage':stage,'phase':phase,
                                        'elapsed_seconds':round(now-began,1),'hard_limit_seconds':max_seconds})+'\n'
                        print(msg,end='',flush=True);log.write(msg.encode());last=now
                b=p.stdout.read()
                if b:log.write(b);print(b.decode(errors='replace'),end='',flush=True)
                if p.returncode:
                    if not (reports/'failure.json').exists():
                        (reports/'failure.json').write_text(json.dumps({'status':'STOP','stage':stage,'exit_code':p.returncode,'log':str(path)}))
                    raise RuntimeError(f'{stage} failed (exit {p.returncode}). See {path} and reports/failure.json.')
            finally:
                selector.close()
                if p.poll() is None:
                    os.killpg(p.pid,signal.SIGTERM)
                    try:p.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=3)
                p.stdout.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['prepare','evaluate','report'])
    parser.add_argument('--phase',choices=['win_strength'],default='win_strength')
    parser.add_argument('--max-seconds',type=int,default=120)
    a=parser.parse_args();run_stage(a.stage,a.phase,a.max_seconds)
