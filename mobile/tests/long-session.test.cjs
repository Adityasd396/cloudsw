const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),ts=require('typescript');
const {RecoveryGate,mergeRoomMessages,pollPath,AutoHideControls}=require('../session.cjs');
const {buildApplyScript}=require('../sync.cjs');
const flush=()=>new Promise(resolve=>setImmediate(resolve));

test('overlay controls hide without polling resets, reveal on touch, and remain accessible when paused/focused',()=>{
 const controls=new AutoHideControls(3000);assert.equal(controls.update(true,0),true);
 for(let now=500;now<3000;now+=500)assert.equal(controls.update(true,now),true);
 assert.equal(controls.update(true,3000),false);assert.equal(controls.toggle(4000),true);
 assert.equal(controls.update(true,7000),false);controls.focused=true;assert.equal(controls.update(true,8000),true);
 controls.focused=false;assert.equal(controls.update(false,20000),true);assert.equal(controls.update(false,23000),false);
 for(let second=21;second<=10800;second++)controls.update(true,second*1000);
 assert.equal(controls.visible,false);assert.equal(controls.toggle(10801000),true);
});

test('browser/native session rules match and history stays bounded for 3 hours of polling',()=>{
 assert.equal(fs.readFileSync(path.join(__dirname,'../session.cjs'),'utf8'),fs.readFileSync(path.join(__dirname,'../../static/session.js'),'utf8'));
 let state={id:'123456',messages:[]},last=0;
 for(let tick=0;tick<=21600;tick++){
  const fresh=tick%6===0?[{id:++last,body:'m'.repeat(500)}]:[];
  state=mergeRoomMessages(state,{id:'123456',messages_delta:true,messages:fresh});
  assert.ok(state.messages.length<=100);assert.equal(new Set(state.messages.map(m=>m.id)).size,state.messages.length);
 }
 assert.equal(state.messages.length,100);assert.equal(state.messages.at(-1).id,last);
 assert.equal(pollPath('123456',last),'/api/rooms/123456?after='+last);
 const unchanged=mergeRoomMessages(state,{id:'123456',messages_delta:true,messages:[]});assert.deepEqual(unchanged.messages,state.messages);
 const switched=mergeRoomMessages(state,{id:'654321',messages_delta:true,messages:[{id:1,body:'new room'}]});assert.equal(switched.messages.length,1);
});

test('recovery blocks background/stale publications and limits renderer restarts',()=>{
 const gate=new RecoveryGate();assert.equal(gate.canPublish(0),true);
 gate.suspend();assert.equal(gate.canPublish(1000),false);
 const first=gate.begin();gate.suspend();assert.equal(gate.complete(first,2000),false);
 const second=gate.begin();assert.equal(gate.complete(second,3000),true);assert.equal(gate.canPublish(4499),false);assert.equal(gate.canPublish(4500),true);
 for(let minute=0;minute<180;minute++){
  for(let attempt=0;attempt<3;attempt++)assert.equal(gate.allowReload(minute*60000+attempt),true);
  assert.equal(gate.allowReload(minute*60000+4),false);assert.ok(gate.reloads.length<=3);
 }
});

test('native publisher cannot broadcast a stale pause while suspended or recovering',async()=>{
 const source=fs.readFileSync(path.join(__dirname,'../App.tsx'),'utf8'),start=source.indexOf('async function publishState('),end=source.indexOf('  const {height,width}',start);
 const code=ts.transpileModule(source.slice(start,end),{compilerOptions:{target:ts.ScriptTarget.ES2020}}).outputText;
 const gate=new RecoveryGate(),sent=[];
 const context={Date,sessionGate:{current:gate},roomRef:{current:{id:'123456',can_control:true,updated:10}},localIntent:{current:null},sampleRef:{current:null},playbackBusy:{current:false},playbackPending:{current:null},setConnected(){},request:async(_,body)=>{sent.push(body);return {updated:11}}};
 vm.createContext(context);vm.runInContext(code,context);
 gate.suspend();await context.publishState(12,false,true);assert.equal(sent.length,0);
 const epoch=gate.begin();await context.publishState(12,false,true);assert.equal(sent.length,0);
 gate.complete(epoch,Date.now()-1600);await context.publishState(100,true,true);assert.equal(sent.length,1);assert.equal(sent[0].playing,true);
});

test('chat mutations do not suppress the independent native polling loop',async()=>{
 const source=fs.readFileSync(path.join(__dirname,'../App.tsx'),'utf8'),start=source.indexOf('  useEffect(()=>{const timer=setInterval(async()=>'),end=source.indexOf('  const leaving=',start);
 let tick,reads=0,received=0;const gate=new RecoveryGate();
 const context={Date,useEffect:fn=>fn(),setInterval:fn=>(tick=fn,1),clearInterval(){},leaving:{current:false},active:{current:true},roomRef:{current:{id:'123456'}},pollBusy:{current:false},mutating:{current:12},pollDue:{current:0},pollErrors:{current:0},pollDelay:()=>650,lastMessage:{current:100},sessionGate:{current:gate},pollPath,request:async url=>{reads++;assert.ok(url.endsWith('?after=100'));return {}},receive(){received++},setConnected(){},setRoom(){},setEntryMode(){},sampleRef:{current:null}};
 vm.createContext(context);vm.runInContext(ts.transpileModule(source.slice(start,end),{}).outputText,context);await tick();assert.equal(reads,1);assert.equal(received,1);
});

test('transient media aborts retry, but actual autoplay denial waits for user intent',async()=>{
 let count=0,denied=false;
 const video={readyState:4,seeking:false,duration:1000,currentTime:0,paused:true,play(){count++;if(denied)return Promise.reject({name:'NotAllowedError'});if(count===1)return Promise.reject({name:'AbortError'});this.paused=false;return Promise.resolve()},pause(){this.paused=true}};
 const context={location:{hostname:'m.youtube.com'},document:{querySelector:s=>s==='video'?video:null},window:{}};vm.createContext(context);
 vm.runInContext(buildApplyScript(0,true),context);await flush();assert.equal(context.window.__afterglowBlocked,false);
 vm.runInContext(buildApplyScript(0,true),context);await flush();assert.equal(video.paused,false);
 video.paused=true;denied=true;vm.runInContext(buildApplyScript(1,true),context);await flush();const attempts=count;
 vm.runInContext(buildApplyScript(1,true),context);assert.equal(count,attempts);assert.equal(context.window.__afterglowBlocked,true);
 denied=false;vm.runInContext(buildApplyScript(1,true,true),context);await flush();assert.equal(video.paused,false);
});

test('an unresolved play promise times out without an old completion corrupting the new attempt',async()=>{
 let now=0,calls=0;const resolves=[];
 const video={readyState:4,seeking:false,duration:1000,currentTime:0,paused:true,play(){calls++;return new Promise(resolve=>resolves.push(resolve))},pause(){this.paused=true}};
 const context={Date:{now:()=>now},location:{hostname:'m.youtube.com'},document:{querySelector:s=>s==='video'?video:null},window:{}};vm.createContext(context);
 vm.runInContext(buildApplyScript(0,true),context);vm.runInContext(buildApplyScript(0,true),context);assert.equal(calls,1);
 now=10001;vm.runInContext(buildApplyScript(10,true),context);assert.equal(calls,2);
 resolves[0]();await flush();assert.equal(context.window.__afterglowPlayPending,true);
 resolves[1]();await flush();assert.equal(context.window.__afterglowPlayPending,false);
});

for(const platform of ['android-model','iphone-model'])test(platform+': 3-hour media correction replay',async t=>{
 let now=0,plays=0,pauses=0,ad=false;
 const makeVideo=()=>({readyState:4,seeking:false,duration:20000,currentTime:0,paused:true,play(){plays++;this.paused=false;return Promise.resolve()},pause(){pauses++;this.paused=true}});
 let video=makeVideo();const context={Date:{now:()=>now},location:{hostname:platform==='android-model'?'m.youtube.com':'www.youtube.com'},document:{querySelector:s=>s==='video'?video:ad?{}:null},window:{}};
 vm.createContext(context);
 for(let second=0;second<=10800;second++){
  now=second*1000;if(second&&second%1800===0)video=makeVideo();
  ad=second%900>=880&&second%900<890;const playing=second%600>2;
  video.currentTime=Math.max(0,second-(second%37===0?3:0));
  vm.runInContext(buildApplyScript(second,playing),context);await Promise.resolve();
  if(!ad){assert.ok(Math.abs(video.currentTime-second)<.01);assert.equal(video.paused,!playing)}
 }
 await flush();assert.equal(context.window.__afterglowPlayPending,false);assert.ok(plays>0&&pauses>0);
 t.diagnostic(JSON.stringify({simulated_seconds:10800,play_calls:plays,pause_calls:pauses,physical_device:false}));
});
