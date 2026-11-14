const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(){
 let id=0,now=10000,mutation,writes=0;const timers=new Map(),events={},input={},reports=[];const classes=new Set();
 const navigator={onLine:true,platform:'iPhone',language:'en',connection:{effectiveType:'4g',rtt:40,downlink:10}};
 for(const key of ['geolocation','mediaDevices','permissions','getBattery'])Object.defineProperty(navigator,key,{get(){throw Error('Permission API accessed')}});
 const c={navigator,devicePixelRatio:2,innerWidth:390,innerHeight:844,Intl,JSON,Math,Date:{now:()=>now},performance:{now:()=>now},AbortController,state:{id:'123456',release_version:'test',position:20,playing:true,server_time:10,updated:10},roomId:'123456',roomReceivedAt:now,activeScreen:'watch',ready:true,pollFailures:0,playerNotice:{hidden:true},player:new Proxy({getPlayerState:()=>1,getCurrentTime:()=>20,getDuration:()=>100,isMuted:()=>false,getVolume:()=>50},{get(target,key){if(key in target)return target[key];writes++;throw Error('Unexpected media access')}}),document:{hidden:false,body:{dataset:{screen:'watch'},classList:{contains:name=>classes.has(name)}},addEventListener:(name,fn)=>events[name]=fn},window:{visualViewport:{width:390,height:504},addEventListener:(name,fn)=>events[name]=fn},$:()=>({value:'private typed secret',addEventListener:(name,fn)=>input[name]=fn}),render(){},fetch:async(path,options)=>{reports.push({path,body:JSON.parse(options.body)});return {}},setInterval(){},setTimeout:(fn,delay)=>{timers.set(++id,{fn,delay});return id},clearTimeout:key=>timers.delete(key),MutationObserver:class{constructor(fn){mutation=fn}observe(){}}};
 vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(__dirname,'../../static/client-diagnostics.js'),'utf8'),c);
 return {c,input,events,reports,timers,mutate:()=>mutation(),writes:()=>writes,advance:n=>now+=n};
}
test('client snapshots exclude typed text and use no permission or playback-write APIs',async()=>{
 const h=harness();await h.c.sendDiagnostics();assert.equal(h.reports.length,1);const data=h.reports[0].body;
 assert.equal(data.typing,true);assert.equal(data.playback,'playing');assert.equal(data.width,390);assert.equal(data.network_rtt_ms,40);assert.equal(h.writes(),0);assert.ok(!JSON.stringify(data).includes('private typed secret'));
});
test('typing and unchanged render class mutations coalesce without continuous diagnostic polling',async()=>{
 const h=harness();for(let i=0;i<1000;i++){h.input.input();h.mutate()}assert.equal(h.timers.size,1);
 await h.c.sendDiagnostics();assert.equal(h.timers.size,0);for(let i=0;i<1000;i++)h.mutate();assert.equal(h.timers.size,0);
 await h.c.sendDiagnostics();assert.equal(h.reports.length,1);assert.equal(h.timers.size,1);
 h.advance(2200);await h.c.sendDiagnostics();assert.equal(h.reports.length,2);assert.equal(h.timers.size,0);
});
