const test=require('node:test'),assert=require('node:assert/strict');
const {Controller}=require('../../static/direct-playback.js');
const flush=async()=>{for(let i=0;i<8;i++)await Promise.resolve()};
function clock(){let now=0,id=0;const jobs=new Map();return {schedule:(fn,ms)=>{jobs.set(++id,{fn,at:now+ms});return id},cancel:id=>jobs.delete(id),tick:ms=>{now+=ms;for(const [key,job]of [...jobs])if(job.at<=now){jobs.delete(key);job.fn()}}}}
test('pending direct play requests coalesce and pause cancels stale retries',async()=>{
 const time=clock();let calls=0,reject;const notices=[];
 const c=new Controller({play:()=>{calls++;return new Promise((_,r)=>reject=r)},pause(){},notify:(...args)=>notices.push(args),...time});
 c.play();c.play();c.play();await flush();assert.equal(calls,1);c.pause();reject({name:'AbortError'});await flush();time.tick(5000);assert.equal(calls,1);assert.equal(notices.length,0);
 c.arm();c.play();c.pause();await flush();assert.equal(calls,1,'pause before the play microtask must prevent starting');
});
test('transient abort retries are bounded and autoplay denial waits for user intent',async()=>{
 const time=clock();let calls=0;const c=new Controller({play:()=>{calls++;return Promise.reject({name:'AbortError'})},pause(){},...time});
 c.play();await flush();time.tick(150);await flush();time.tick(450);await flush();c.play();await flush();assert.equal(calls,3);assert.equal(c.blocked,true);
 let allowed=false;const d=new Controller({play:()=>allowed?Promise.resolve():Promise.reject({name:'NotAllowedError'}),pause(){},...time});d.play();await flush();assert.equal(d.blocked,true);allowed=true;d.arm();d.play();await flush();assert.equal(d.blocked,false);assert.equal(d.pending,false);
});
test('a timed-out old source cannot change a replacement source',async()=>{
 const time=clock(),notices=[];let finish;
 const c=new Controller({play:()=>new Promise(r=>finish=r),pause(){},notify:()=>notices.push(1),timeoutMs:3000,...time});c.play();await flush();time.tick(3000);assert.equal(c.blocked,true);assert.equal(notices.length,1);c.reset();finish();await flush();assert.equal(c.blocked,false);assert.equal(c.pending,false);
});
