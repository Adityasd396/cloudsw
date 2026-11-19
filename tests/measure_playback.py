"""Real Chromium media decode against the disposable loopback server."""
import argparse,json,time,threading,os,sys
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from pathlib import Path
import requests,psutil
from playwright.sync_api import sync_playwright
from tools.benchmark_local import summary

BASE='http://127.0.0.1:8027'
INSTRUMENT='''()=>{window.metrics={waiting:0,stalled:0,errors:[],buffer_ms:0,rebuffer_count:0,rebuffer_ms:0,expected_waits:0};window.waitAt=null;const v=document.querySelector('video');v.addEventListener('waiting',()=>{metrics.waiting++;window.expectedWait=v.seeking||v.currentTime<.05;if(expectedWait)metrics.expected_waits++;else metrics.rebuffer_count++;waitAt=performance.now()});v.addEventListener('stalled',()=>metrics.stalled++);v.addEventListener('playing',()=>{if(waitAt!==null){metrics.buffer_ms+=performance.now()-waitAt;if(!expectedWait)metrics.rebuffer_ms+=performance.now()-waitAt;waitAt=null}});v.addEventListener('error',()=>metrics.errors.push({code:v.error?.code,message:v.error?.message}));window.v=v}'''

def main(output):
    assert requests.get(BASE+'/__audit__/info').json()['disposable']
    protocol=[]
    for range_,expected in [('bytes=0-1023',206),('bytes=-128',206),('bytes=999999999-',416)]:
        r=requests.get(BASE+'/__audit__/media/clip.mp4',headers={'Range':range_},timeout=5);assert r.status_code==expected
        protocol.append({'range':range_,'status':r.status_code,'content_range':r.headers.get('Content-Range'),'bytes':len(r.content)})
    for path,headers,status in [('/__audit__/protected.mp4',{},401),('/__audit__/protected.mp4',{'Authorization':'Bearer disposable-test','Range':'bytes=0-15'},206),('/__audit__/expired.mp4',{},403)]:
        r=requests.get(BASE+path,headers=headers,timeout=5);assert r.status_code==status;protocol.append({'case':path,'status':status})
    cached=requests.get(BASE+'/__audit__/media/clip.mp4',timeout=5);etag=cached.headers.get('ETag');conditional=requests.get(BASE+'/__audit__/media/clip.mp4',headers={'If-None-Match':etag},timeout=5);assert conditional.status_code==304;protocol.append({'case':'conditional ETag','status':304,'bytes':len(conditional.content)})
    hls=requests.get(BASE+'/__audit__/media/clip.m3u8',timeout=5);segments=[line for line in hls.text.splitlines() if line and not line.startswith('#')]
    assert segments and all(requests.get(BASE+'/__audit__/media/'+s,timeout=5).status_code==200 for s in segments)
    resources=[];stop=threading.Event();root=psutil.Process()
    def sample():
        while not stop.wait(.15):
            processes=root.children(recursive=True);rss=0
            for proc in processes:
                try:rss+=proc.memory_info().rss
                except psutil.Error:pass
            resources.append(rss/2**20)
    t=threading.Thread(target=sample,daemon=True);t.start()
    with sync_playwright() as p:
        browser=p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required']);context=browser.new_context();page=context.new_page()
        def setup(page):
            page.goto(BASE+'/__audit__/info');page.set_content('<video playsinline controls preload="auto" style="width:640px;max-width:100%"></video>');page.evaluate(INSTRUMENT)
        setup(page);startup=[];seeks=[];resume=[]
        for n in range(24):
            ms=page.evaluate('''url=>new Promise((resolve,reject)=>{const t=performance.now();v.onplaying=()=>{v.onplaying=null;resolve(performance.now()-t)};v.onerror=()=>reject(Error(v.error?.message));v.src=url;v.play().catch(reject)})''',BASE+'/__audit__/media/clip.mp4?sample='+str(n));startup.append(ms)
            seek=page.evaluate('''()=>new Promise(resolve=>{const t=performance.now();v.onseeked=()=>{v.onseeked=null;resolve(performance.now()-t)};v.currentTime=9})''');seeks.append(seek)
            page.evaluate('v.pause()');assert page.evaluate('v.paused')
            resumed=page.evaluate('''()=>new Promise((resolve,reject)=>{const t=performance.now();v.onplaying=()=>{v.onplaying=null;resolve(performance.now()-t)};v.play().catch(reject)})''');resume.append(resumed)
        page.wait_for_timeout(5000);normal=page.evaluate('({...metrics,current_time:v.currentTime,frames:v.getVideoPlaybackQuality?{total:v.getVideoPlaybackQuality().totalVideoFrames,dropped:v.getVideoPlaybackQuality().droppedVideoFrames}:null})');page.evaluate('v.pause()')
        concurrency=[]
        for count in [2,4]:
            group=[context.new_page() for _ in range(count)]
            for item in group:setup(item);item.evaluate('(url)=>{v.src=url;v.play().catch(()=>{})}',BASE+'/__audit__/media/clip.mp4?concurrent='+str(count))
            for item in group:item.wait_for_function('v.currentTime>.2')
            concurrency.append({'clients':count,'all_advanced':True,'errors':sum(len(item.evaluate('metrics.errors')) for item in group)})
            for item in group:item.close()
        failures=[]
        for path,status in [('bad.mp4',200),('media/missing.mp4',404),('expired.mp4',403)]:
            result=page.evaluate('''url=>new Promise(resolve=>{v.onerror=()=>resolve({code:v.error?.code,message:v.error?.message});v.src=url;v.load()})''',BASE+'/__audit__/'+path)
            failures.append({'case':path,'expected':'Media error, recoverable by loading a valid source','actual':result})
        page.evaluate('metrics={waiting:0,stalled:0,errors:[],buffer_ms:0,rebuffer_count:0,rebuffer_ms:0,expected_waits:0};waitAt=null');cdp=context.new_cdp_session(page);cdp.send('Network.enable');cdp.send('Network.setCacheDisabled',{'cacheDisabled':True});cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':100,'downloadThroughput':65536,'uploadThroughput':32768})
        started=time.perf_counter();page.evaluate('(url)=>{v.src=url;v.play().catch(()=>{})}',BASE+'/__audit__/media/clip.mp4?slow=1');page.wait_for_function('v.currentTime>.1',timeout=20000);slow_start=(time.perf_counter()-started)*1000;page.wait_for_timeout(3000);slow=page.evaluate('({time:v.currentTime,waiting:metrics.waiting,stalled:metrics.stalled,buffer_ms:metrics.buffer_ms,rebuffer_count:metrics.rebuffer_count,rebuffer_ms:metrics.rebuffer_ms})')
        cdp.send('Network.emulateNetworkConditions',{'offline':True,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1});page.wait_for_timeout(1000);offline=page.evaluate('({time:v.currentTime,buffered:v.buffered.length?v.buffered.end(v.buffered.length-1):0})')
        cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1});page.evaluate('(url)=>{v.src=url;v.play().catch(()=>{})}',BASE+'/__audit__/media/clip.mp4?recovery=1');page.wait_for_function('v.currentTime>.2',timeout=10000)
        hls_support=page.evaluate("v.canPlayType('application/vnd.apple.mpegurl')");hls_play=page.evaluate('''url=>new Promise(resolve=>{const timer=setTimeout(()=>resolve('timeout'),8000);v.onplaying=()=>{clearTimeout(timer);resolve('playing')};v.onerror=()=>{clearTimeout(timer);resolve('media-error-'+v.error?.code)};v.src=url;v.play().catch(()=>{})})''',BASE+'/__audit__/media/clip.m3u8')
        result={'source_fingerprint':requests.get(BASE+'/__audit__/info').json().get('source_fingerprint'),'startup_ms':summary(startup),'seek_ms':summary(seeks),'resume_ms':summary(resume),'normal_playback':normal,'concurrent_playback':concurrency,'http_tests':protocol,'media_failures':failures,'hls':{'manifest_and_segments':True,'real_playback':hls_play,'native_browser_support':hls_support or 'unsupported on this Chromium build'},'dash':'Not implemented by the application','slow_network':{'profile':'64 KiB/s, 100 ms RTT injection','startup_ms':round(slow_start,2),**slow},'interrupted_connection':{'buffered_state':offline,'reload_after_reconnect':'playing'},'browser':'Chromium, real H264/AAC decoding; autoplay allowed for measurements; no physical phones'}
        browser.close()
    stop.set();t.join();result['browser_tree_rss_mib']=summary(resources);Path(output).write_text(json.dumps(result,indent=2));print(json.dumps(result))

if __name__=='__main__':
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--base',default=BASE);args=parser.parse_args();BASE=args.base
    from urllib.parse import urlparse
    if urlparse(BASE).hostname not in ('127.0.0.1','localhost','::1'):raise ValueError('Loopback only')
    main(args.output)
