const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
const {buildApplyScript}=require('../sync.cjs');
test('native Resume wins over a stale paused sample while a request is in flight',async()=>{
 const source=fs.readFileSync(path.join(__dirname,'../App.tsx'),'utf8');
 const start=source.indexOf('async function publishState('),end=source.indexOf('  const {height,width}',start);
 const code=ts.transpileModule(source.slice(start,end),{compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText;
 const sent=[],resolvers=[];
 const context={Date,roomRef:{current:{id:'123456',can_control:true,updated:1}},localIntent:{current:null},sampleRef:{current:{position:40,playing:true}},playbackBusy:{current:false},playbackPending:{current:null},setConnected(){},request:async(url,body)=>{sent.push(body);await new Promise(resolve=>resolvers.push(resolve))}};
 vm.createContext(context);vm.runInContext(code,context);
 const pause=context.publishState(40,false);
 await context.publishState(40,false,true); // Delayed observer sample must not replace intent.
 await context.publishState(40,true);
 await context.publishState(40,false,true);
 assert.equal(sent.length,1);assert.equal(context.playbackPending.current.playing,true);
 resolvers.shift()();await pause;
 assert.equal(sent.length,2);assert.equal(sent[1].playing,true);
 resolvers.shift()();
});
test('guest applies pause, resume, and seek without repeated concurrent play attempts',async()=>{
 let plays=0,pauses=0,resolvePlay;
 const video={readyState:4,seeking:false,duration:200,currentTime:30,paused:false,pause(){pauses++;this.paused=true},play(){plays++;return new Promise(resolve=>{resolvePlay=()=>{this.paused=false;resolve()}})}};
 const context={location:{hostname:'m.youtube.com'},document:{querySelector:selector=>selector==='video'?video:null},window:{}};
 vm.createContext(context);
 vm.runInContext(buildApplyScript(30,false),context);assert.equal(pauses,1);
 vm.runInContext(buildApplyScript(30,true),context);vm.runInContext(buildApplyScript(30,true),context);assert.equal(plays,1);
 resolvePlay();await Promise.resolve();
 vm.runInContext(buildApplyScript(85,true),context);assert.equal(video.currentTime,85);assert.equal(video.paused,false);assert.equal(pauses,1);
});
test('web host polling does not replay an old pause after Resume',()=>{
 const source=fs.readFileSync(path.join(__dirname,'../../static/enhancements.js'),'utf8');
 const start=source.indexOf('synchronize=function('),end=source.indexOf('let hostSample',start);let pauses=0;
 const context={Date,Math,ready:true,state:{is_host:true,video:'same',position:40,playing:0,updated:1,server_time:1},lastVideo:'same',player:{pauseVideo(){pauses++},getPlayerState:()=>1},applyingUntil:0};
 vm.createContext(context);vm.runInContext(source.slice(start,end),context);context.synchronize();assert.equal(pauses,0);
});
