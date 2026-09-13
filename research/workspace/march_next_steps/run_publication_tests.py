"""User-run publication regression gate. Temporary fixtures, no GitHub writes."""
from __future__ import annotations
import json
import os
import signal
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from publication.review_support import atomic,lock,public_test_fingerprints,safe_path

def main():
    root=Path(__file__).resolve().parent;home=Path.home();reports=safe_path(home/'march_publication')
    reports.mkdir(exist_ok=True,mode=0o700)
    with lock(home):
        before=public_test_fingerprints(root);start=time.monotonic()
        record={'status':'RUNNING','source_sha256':before,'account_calls':0,'project_scientific_tests_run':False}
        receipt=reports/'publication_test_receipt.json';atomic(receipt,record)
        log=safe_path(reports/'publication_tests.log');child=None;problem=None
        print('Temporary publication tests only. Hard ceiling: 120 seconds.',flush=True)
        try:
            with log.open('w') as out:
                child=subprocess.Popen([sys.executable,'-m','unittest','discover','-s','tests','-v','-b'],cwd=root,
                    stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
                last=start
                while child.poll() is None:
                    now=time.monotonic()
                    if now-start>120:raise TimeoutError('Publication tests exceeded 120 seconds')
                    if now-last>=15:
                        print(json.dumps({'event':'publication_tests_running','elapsed_seconds':round(now-start,1)}),flush=True);last=now
                    time.sleep(.2)
        except BaseException as exc:problem=exc
        finally:
            if child is not None and child.poll() is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=3)
            unchanged=public_test_fingerprints(root)==before
            record.update(status='PASS' if child is not None and child.returncode==0 and problem is None and unchanged else 'FAIL',
                elapsed_seconds=round(time.monotonic()-start,3),returncode=None if child is None else child.returncode,
                source_unchanged=unchanged,error_type=None if problem is None else type(problem).__name__)
            atomic(receipt,record)
            path=safe_path(reports/'publication_test_return.zip')
            with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
                z.write(receipt,'publication_test_receipt.json')
                if log.exists():z.write(log,'publication_tests.log')
        if log.exists():print(log.read_text())
        print('PUBLICATION_TEST_GATE:',record['status'])
        print('Receipt:',receipt)
        if record['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
