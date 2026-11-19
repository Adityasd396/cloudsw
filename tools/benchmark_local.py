"""Bounded loopback benchmark; never targets a remote deployment."""
import argparse,concurrent.futures,json,statistics,time,threading
from pathlib import Path
from urllib.parse import urlparse
import requests,psutil

def summary(values):
    values=sorted(values)
    return {'n':len(values),'p50':round(statistics.median(values),3),'p95':round(values[min(len(values)-1,int(.95*len(values)))],3) if len(values)>=20 else None,'max':round(max(values),3)}

def run(base,accounts=False):
    u=urlparse(base)
    if u.hostname not in ('127.0.0.1','localhost','::1') or u.scheme!='http':raise ValueError('Only local HTTP loopback is allowed')
    info=requests.get(base+'/__audit__/info',timeout=5).json()
    if not info.get('disposable'):raise ValueError('A disposable audit server is required')
    process=psutil.Process(info['pid']);samples=[];stop=threading.Event();process.cpu_percent()
    account_cookies=[]
    if accounts:
        for index in range(4):
            with requests.Session() as client:
                csrf=client.get(base+'/api/me',timeout=8).json()['csrf']
                response=client.post(base+'/api/auth/signup',json={'email':'benchmark-'+str(time.time_ns())+'@example.test','name':'Synthetic account','password':'local benchmark password only','accept_terms':'on'},headers={'X-CSRF-Token':csrf},timeout=8);response.raise_for_status();account_cookies.append(client.cookies.copy())
    def sample():
        while not stop.wait(.1):samples.append({'cpu_core_percent':process.cpu_percent(),'rss_mib':process.memory_info().rss/2**20})
    thread=threading.Thread(target=sample,daemon=True);thread.start();start_io=process.io_counters();start_net=psutil.net_io_counters();start_disk=psutil.disk_io_counters();cpu_begin=sum(process.cpu_times()[:2]);stages=[]
    for concurrency in [1,2,4]:
        def worker(index):
            with requests.Session() as session:
                if accounts:session.cookies.update(account_cookies[index])
                room=session.post(base+'/api/rooms',json={},timeout=8).json()['id'];path='/api/rooms/'+room;session.post(base+path,json={'action':'join','name':'Synthetic '+str(index)},timeout=8)
                result=[]
                try:
                    for turn in range(96):
                        kind=['media','room','game'][turn%3];url=base+('/__audit__/media/clip.mp4' if kind=='media' else path+'/game' if kind=='game' else path)
                        began=time.perf_counter();response=session.get(url,timeout=8);elapsed=(time.perf_counter()-began)*1000
                        result.append({'kind':kind,'ms':elapsed,'bytes':len(response.content),'status':response.status_code})
                finally:session.post(base+path+'/leave',json={},timeout=8)
                return result
        began=time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:rows=[r for batch in pool.map(worker,range(concurrency)) for r in batch]
        seconds=time.perf_counter()-began;errors=sum(r['status']!=200 for r in rows)
        stage={'concurrency':concurrency,'seconds':round(seconds,3),'errors':errors,'requests':len(rows),'payload_mib':round(sum(r['bytes'] for r in rows)/2**20,3),'payload_mib_per_second':round(sum(r['bytes'] for r in rows)/2**20/seconds,3),'latency_ms':{kind:summary([r['ms'] for r in rows if r['kind']==kind]) for kind in ['media','room','game']}}
        stages.append(stage)
        if errors/len(rows)>.02 or process.memory_info().rss>512*2**20 or (samples and samples[-1]['cpu_core_percent']>300):stage['stop_condition']='error/resource limit';break
    stop.set();thread.join();end_io=process.io_counters();end_net=psutil.net_io_counters();end_disk=psutil.disk_io_counters()
    return {'local_only':True,'media':'synthetic H264/AAC 640x360 18 seconds','media_bytes':info['media_bytes'],'source_fingerprint':info.get('source_fingerprint'),'stages':stages,'resources':{'server_cpu_seconds':round(sum(process.cpu_times()[:2])-cpu_begin,3),'host_disk_io_bytes_delta':{'read':end_disk.read_bytes-start_disk.read_bytes,'write':end_disk.write_bytes-start_disk.write_bytes},'cpu_core_percent':summary([s['cpu_core_percent'] for s in samples]),'rss_mib':summary([s['rss_mib'] for s in samples]),'process_io_bytes_delta':{'read':end_io.read_bytes-start_io.read_bytes,'write':end_io.write_bytes-start_io.write_bytes},'host_network_bytes_delta':{'received':end_net.bytes_recv-start_net.bytes_recv,'sent':end_net.bytes_sent-start_net.bytes_sent},'notes':'CPU is percent of one logical core. Process I/O includes network on Windows. Host NIC counters include unrelated activity and may exclude loopback; payload bytes are separately measured.'}}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',default='http://127.0.0.1:8027');p.add_argument('--output',required=True);p.add_argument('--accounts',action='store_true');args=p.parse_args();result=run(args.base,args.accounts);result['authenticated']=args.accounts;Path(args.output).write_text(json.dumps(result,indent=2));print(json.dumps(result))
