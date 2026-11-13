const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
const {buildApplyScript}=require('../sync.cjs');
const {RecoveryGate}=require('../session.cjs');
test('native Resume wins over a stale paused sample while a request is in flight',async()=>{
 const source=fs.readFileSync(path.join(__dirname,'../App.tsx'),'utf8');
 const start=source.indexOf('async function publishState('),end=source.indexOf('  const {height,width}',start);
 const code=ts.transpileModule(source.slice(start,end),{compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText;
 const sent=[],resolvers=[];
 const context={Date,sessionGate:{current:new RecoveryGate()},roomRef:{current:{id:'123456',can_control:true,updated:1}},localIntent:{current:null},sampleRef:{current:{position:40,playing:true}},playbackBusy:{current:false},playbackPending:{current:null},setConnected(){},request:async(url,body)=>{sent.push(body);await new Promise(resolve=>resolvers.push(resolve))}};
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
 const context={Date,Math,localControlUntil:Date.now()+3000,confirmedControlUpdated:0,controlBusy:false,ready:true,state:{is_host:true,video:'same',position:40,playing:0,updated:1,server_time:1},lastVideo:'same',lastPlaybackId:undefined,player:{pauseVideo(){pauses++},getPlayerState:()=>1},applyingUntil:0};
 vm.createContext(context);vm.runInContext(source.slice(start,end),context);context.synchronize();assert.equal(pauses,0);
});

test('a confirmed newer participant command applies to the host during the intent window',()=>{
 const source=fs.readFileSync(path.join(__dirname,'../../static/enhancements.js'),'utf8');
 const start=source.indexOf('synchronize=function('),end=source.indexOf('let hostSample',start);let pauses=0;
 const context={Date,Math,localControlUntil:Date.now()+3000,confirmedControlUpdated:10,controlBusy:false,ready:true,state:{is_host:true,video:'same',position:40,playing:0,updated:11,server_time:11},lastVideo:'same',lastPlaybackId:undefined,playerNotice:{hidden:true},player:{getDuration:()=>200,getVideoData:()=>({}),getCurrentTime:()=>40,getPlayerState:()=>1,pauseVideo(){pauses++}}};
 vm.createContext(context);vm.runInContext(source.slice(start,end),context);context.synchronize();assert.equal(pauses,1);
});

test('a repeated video starts from zero for a new playback instance',()=>{
 const source=fs.readFileSync(path.join(__dirname,'../../static/enhancements.js'),'utf8');
 const start=source.indexOf('synchronize=function('),end=source.indexOf('let hostSample',start);const loads=[];
 const context={Date,Math,ready:true,state:{video:'same',playback_id:'new',position:0,playing:1,updated:10,server_time:10},lastVideo:'same',lastPlaybackId:'old',playerNotice:{hidden:false},$:()=>({}),player:{loadVideoById:data=>loads.push(data)}};
 vm.createContext(context);vm.runInContext(source.slice(start,end),context);context.synchronize();assert.equal(loads.length,1);assert.equal(loads[0].startSeconds,0);
});

test('duplicate end callbacks do not repeatedly advance an empty queue',async()=>{
 const source=fs.readFileSync(path.join(__dirname,'../../static/player-room.js'),'utf8');let calls=0,complete;
 const context={state:{can_control:true,playing:1,playback_id:'one'},pageRecovery:{canPublish:()=>true},roomId:'123456',setInterval(){},toast(){},api:async(path,data)=>{calls++;assert.equal(data.expected_playback_id,'one');return new Promise(resolve=>complete=resolve)}};
 context.render=next=>context.state=next;vm.createContext(context);vm.runInContext(source.slice(source.indexOf('let advancingPlayback=')),context);
 const first=context.advanceFinishedVideo();await context.advanceFinishedVideo();assert.equal(calls,1);
 complete({can_control:true,playing:0,playback_id:'two'});await first;await context.advanceFinishedVideo();assert.equal(calls,1);
});
