"""Five isolated process startups, loopback only, with no user storage."""
import subprocess,sys,time,argparse,json
from pathlib import Path
import requests,psutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.benchmark_local import summary
p=argparse.ArgumentParser();p.add_argument('--source',choices=['release','workspace'],required=True);p.add_argument('--output',required=True);args=p.parse_args()
values=[]
for _ in range(5):
    began=time.perf_counter();process=subprocess.Popen([sys.executable,'-B',str(ROOT/'tests/run_stream_audit.py'),'--port','8028','--source',str(ROOT/'release' if args.source=='release' else ROOT)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        while time.perf_counter()-began<15:
            if process.poll() is not None:raise RuntimeError('Audit server failed to start')
            try:
                result=requests.get('http://127.0.0.1:8028/__audit__/info',timeout=.25).json()
                owned={process.pid}|{child.pid for child in psutil.Process(process.pid).children(recursive=True)}
                if result['pid'] in owned:values.append((time.perf_counter()-began)*1000);break
            except requests.RequestException:pass
            time.sleep(.025)
        else:raise TimeoutError('Startup timeout')
    finally:
        try:
            children=psutil.Process(process.pid).children(recursive=True)
            for child in children:child.terminate()
            psutil.wait_procs(children,timeout=5)
        except psutil.NoSuchProcess:pass
        if process.poll() is None:process.terminate()
        process.wait(timeout=10)
result={'source':args.source,'startup_ms':summary(values),'samples_ms':values,'definition':'Process creation through application import, disposable schema initialization and first successful HTTP response; not PythonAnywhere cold-start timing.'}
Path(args.output).write_text(json.dumps(result,indent=2));print(json.dumps(result))
