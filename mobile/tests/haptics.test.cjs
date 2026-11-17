const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {Controller,BeatClock,preferences}=require('../haptic-core.cjs');
test('haptics preferences are bounded, music starts off and web/native rules match',()=>{
 assert.deepEqual(preferences(),{enabled:true,music:false,bpm:90});assert.equal(preferences({bpm:300}).bpm,160);assert.equal(preferences({bpm:-1}).bpm,60);assert.equal(preferences({bpm:NaN}).bpm,90);
 assert.equal(fs.readFileSync(path.join(__dirname,'../haptic-core.cjs'),'utf8'),fs.readFileSync(path.join(__dirname,'../../static/haptic-core.js'),'utf8'));
});
test('master off, background and rate limits prevent unwanted pulses without queues',()=>{
 let now=1000;const calls=[],controller=new Controller(kind=>calls.push(kind),()=>now);
 assert.equal(controller.pulse('beat'),false);assert.equal(controller.pulse('chat'),true);assert.equal(controller.pulse('game'),false);
 now+=120;controller.configure({enabled:false,music:true,bpm:90});assert.equal(controller.pulse('goal'),false);
 controller.configure({enabled:true,music:true,bpm:90});controller.foreground=false;assert.equal(controller.pulse('beat'),false);controller.foreground=true;assert.equal(controller.pulse('beat'),true);
 now+=120;assert.equal(controller.pulse('beat'),false);now+=500;assert.equal(controller.pulse('beat'),true);assert.equal(controller.pulse('unknown'),false);assert.deepEqual(calls,['chat','beat','beat']);
});
test('rhythm follows alternate media beats and skips startup, pause, seeks and source/tempo changes',()=>{
 const clock=new BeatClock();assert.equal(clock.sample(0,true,'a',90),false);assert.equal(clock.sample(.7,true,'a',90),false);assert.equal(clock.sample(1.4,true,'a',90),true);
 assert.equal(clock.sample(1.41,true,'a',90),false);assert.equal(clock.sample(120,true,'a',90),false);assert.equal(clock.sample(1,true,'a',90),false);
 assert.equal(clock.sample(1.4,false,'a',90),false);assert.equal(clock.sample(1.4,true,'a',90),false);assert.equal(clock.sample(2.1,true,'b',90),false);assert.equal(clock.sample(3,true,'b',120),false);
});
test('emitter failures do not break chat, games or playback callers',async()=>{
 const c=new Controller(()=>{throw Error('Unavailable device')});assert.doesNotThrow(()=>c.pulse('chat'));
 const p=new Controller(()=>Promise.reject(Error('Unsupported')));assert.doesNotThrow(()=>p.pulse('game'));await new Promise(resolve=>setImmediate(resolve));
});
test('web wrapper persists off and disables emission on hide without using permission APIs',()=>{
 const calls=[],events={},storage=new Map();const window={addEventListener:(name,fn)=>events[name]=fn,dispatchEvent(){}};const context={window,SolaceHapticCore:{Controller},navigator:{userActivation:{hasBeenActive:true},vibrate:n=>calls.push(n)},document:{hidden:false,addEventListener:(name,fn)=>events[name]=fn},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},JSON,Event:class{}};
 vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../../static/haptics.js'),'utf8'),context);
 window.SolaceHaptics.set({enabled:false,music:true,bpm:90});window.SolaceHaptics.pulse('chat');assert.deepEqual(calls,[0]);assert.equal(JSON.parse(storage.get('solace-haptics-v1')).enabled,false);
 context.document.hidden=true;events.visibilitychange();assert.deepEqual(calls,[0,0]);
});
