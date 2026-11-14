const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {requestJson,pollDelay}=require('../transport.cjs');
test('lost mutation response retries exactly the same request identity and body',async()=>{
 const calls=[];const result=await requestJson(async(_,options)=>{calls.push(options);if(calls.length===1)throw new TypeError('Lost response');return {ok:true,json:async()=>({ok:true})}},'/room',{data:{action:'chat',body:'once'}});
 assert.equal(result.ok,true);assert.equal(calls.length,2);assert.equal(calls[0].headers['X-Request-ID'],calls[1].headers['X-Request-ID']);assert.equal(calls[0].body,calls[1].body);
});
test('conflicts are returned without replaying a stale playback command',async()=>{
 let calls=0;await assert.rejects(()=>requestJson(async()=>{calls++;return {ok:false,status:409,json:async()=>({error:'Changed',code:'stale_playback'})}},'/room',{data:{action:'playback'}}),error=>error.status===409);assert.equal(calls,1);
});
test('polling backs off while retaining responsive playing intervals and browser/native parity',()=>{
 assert.ok(pollDelay({playing:true})<pollDelay({playing:false}));assert.equal(pollDelay({failures:100}),15000);assert.equal(pollDelay({hidden:true}),20000);
 assert.equal(fs.readFileSync(path.join(__dirname,'../transport.cjs'),'utf8'),fs.readFileSync(path.join(__dirname,'../../static/transport.js'),'utf8'));
});

test('restored storage can reset an old playback revision without retaining stale messages',()=>{
 const {isOlderSnapshot,mergeRoomMessages,pollPath}=require('../session.cjs');
 const before={id:'123456',storage_generation:'old',playback_revision:20,server_time:10,messages:[{id:99,body:'later'}]},next={id:'123456',storage_generation:'new',playback_revision:4,server_time:20,messages_delta:true,messages:[{id:5,body:'restored'}]};
 assert.equal(isOlderSnapshot(before,next),false);assert.equal(isOlderSnapshot(before,{...next,storage_generation:'old'}),true);assert.equal(mergeRoomMessages(before,next).messages.length,1);assert.match(pollPath('123456',99,'old'),/generation=old/);assert.equal(pollPath('123456',null,'old'),'/api/rooms/123456?generation=old');
});

test('recovery telemetry runs once and cannot break playback publication readiness',()=>{
 const {RecoveryGate}=require('../session.cjs');let samples=0;const gate=new RecoveryGate(()=>{samples++;throw Error('Telemetry unavailable')});const epoch=gate.begin();assert.equal(gate.complete(epoch,100),true);assert.equal(gate.complete(epoch,200),false);assert.equal(samples,1);assert.equal(gate.canPublish(1600),true);
});
