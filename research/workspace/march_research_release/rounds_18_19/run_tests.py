"""User-run test gate. Only temporary synthetic fixtures; no project data or accounts."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time,zipfile
SOURCES=['feature_rounds.py','round_workflow.py','round_plots.py','run_round.py','research_io.py',
         'frozen/research_workflow.py','frozen/shot_features.py','frozen/consensus_reference.py']

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write_json(path,record):
    temp=path.with_suffix('.json.partial')
    if path.is_symlink() or temp.is_symlink():raise ValueError('Unsafe test receipt')
    temp.write_text(json.dumps(record,indent=2));temp.replace(path)

def main():
    kit=Path(__file__).resolve().parent;reports=kit/'reports'
    if reports.is_symlink():raise ValueError('Unsafe report directory')
    reports.mkdir(exist_ok=True)
    for p in [reports/'execution.lock',reports/'test_receipt.json',reports/'tests.log',reports/'test_return.zip']:
        if p.is_symlink():raise ValueError('Unsafe test output')
    import fcntl
    with (reports/'execution.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another test or experiment is running')
        source={n:digest(kit/n) for n in SOURCES}
        suite={str(p.relative_to(kit)):digest(p) for p in sorted((kit/'tests').glob('*.py'))}
        pins=json.loads((kit/'MANIFEST.json').read_text())['sha256']
        for n,h in {**source,**suite}.items():
            if pins.get(n)!=h:raise ValueError('Downloaded source/test changed: '+n)
        receipt={'status':'RUNNING','source_sha256':source,'suite_sha256':suite,'project_data_used':False}
        write_json(reports/'test_receipt.json',receipt)
        env=os.environ.copy()
        for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:env[k]='2'
        started=time.monotonic();print('Running temporary-fixture tests. Hard ceiling: 300 seconds.',flush=True)
        with (reports/'tests.log').open('w') as log:
            child=subprocess.Popen([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=kit,env=env,
                          stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            failure=None
            try:
                last=started
                while child.poll() is None:
                    now=time.monotonic()
                    if now-started>300:raise TimeoutError('Test ceiling reached')
                    if now-last>=15:
                        lines=(reports/'tests.log').read_text(errors='replace').splitlines()
                        print(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'event':'test_progress',
                            'elapsed_seconds':round(now-started,1),'last_test_output':lines[-1] if lines else 'test setup'}),flush=True);last=now
                    time.sleep(.2)
            except BaseException as exc:failure=exc
            finally:
                if child.poll() is None:
                    os.killpg(child.pid,signal.SIGTERM)
                    try:child.wait(timeout=3)
                    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=3)
                changed=any(digest(kit/n)!=h for n,h in {**source,**suite}.items())
                receipt.update(status='PASS' if child.returncode==0 and failure is None and not changed else 'FAIL',
                    returncode=child.returncode,elapsed_seconds=round(time.monotonic()-started,3),
                    error=None if failure is None else str(failure),source_changed_during_tests=changed,
                    utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
                write_json(reports/'test_receipt.json',receipt)
                with zipfile.ZipFile(reports/'test_return.zip','w',zipfile.ZIP_DEFLATED) as z:
                    z.write(reports/'test_receipt.json','test_receipt.json');z.write(reports/'tests.log','tests.log')
        print((reports/'tests.log').read_text());print('TEST_GATE:',receipt['status'])
        if failure is not None:raise failure
        if receipt['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
