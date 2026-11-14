const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(){
 const source=fs.readFileSync(path.join(__dirname,'../../static/room-experience.js'),'utf8');
 const start=source.indexOf('let restingViewportHeight='),end=source.indexOf('// Back closes',start);
 const frames=new Map(),events={},viewportEvents={},documentEvents={},styles={},composer={},classes=new Set();let id=0,writes=0;
 const c={innerHeight:844,innerWidth:390,Math,$:()=>composer,document:{activeElement:null,documentElement:{style:{setProperty:(key,value)=>{styles[key]=value;writes++}}},body:{classList:{toggle:(key,on)=>on?classes.add(key):classes.delete(key)}},addEventListener:(key,fn)=>documentEvents[key]=fn},window:{visualViewport:{height:844,offsetTop:0,scale:1,addEventListener:(key,fn)=>viewportEvents[key]=fn},addEventListener:(key,fn)=>events[key]=fn},requestAnimationFrame:fn=>{frames.set(++id,fn);return id},cancelAnimationFrame:key=>frames.delete(key)};
 vm.createContext(c);vm.runInContext(source.slice(start,end),c);
 const flush=()=>{const work=[...frames.values()];frames.clear();work.forEach(fn=>fn())};
 return {c,composer,classes,styles,events,viewportEvents,documentEvents,frames,flush,writes:()=>writes};
}
test('iPhone keyboard follows viewport frames and waits for closing before restoring footer',()=>{
 const h=harness();h.c.document.activeElement=h.composer;h.documentEvents.focusin();h.c.window.visualViewport.height=504;h.c.window.visualViewport.offsetTop=20;h.viewportEvents.resize();h.flush();assert.ok(h.classes.has('keyboard-open'));assert.equal(h.styles['--room-top'],'20px');
 h.c.document.activeElement=null;h.documentEvents.focusout();h.flush();assert.ok(h.classes.has('keyboard-open'));
 for(const height of [580,680,780]){h.c.window.visualViewport.height=height;h.viewportEvents.resize();h.flush();assert.ok(h.classes.has('keyboard-open'))}
 h.c.window.visualViewport.height=844;h.viewportEvents.resize();h.flush();assert.ok(!h.classes.has('keyboard-open'));assert.equal(h.styles['--room-top'],'0px');
});
test('Android resized viewport, rotation and event storms keep layout work bounded',()=>{
 const h=harness();h.c.document.activeElement=h.composer;h.c.innerHeight=504;h.c.window.visualViewport.height=504;
 for(let i=0;i<1000;i++){h.viewportEvents.resize();h.viewportEvents.scroll()}assert.equal(h.frames.size,1);h.flush();assert.ok(h.classes.has('keyboard-open'));const before=h.writes();h.viewportEvents.scroll();h.flush();assert.equal(h.writes(),before);
 h.c.innerWidth=844;h.c.innerHeight=390;h.c.window.visualViewport.height=390;h.events.resize();h.flush();assert.ok(!h.classes.has('keyboard-open'));
 h.events.resize();h.events.pagehide();assert.equal(h.frames.size,0);
});
test('search fields and pinch zoom do not shift the watch layout into keyboard mode',()=>{
 const h=harness();h.c.document.activeElement={};h.c.window.visualViewport.height=500;h.documentEvents.focusin();h.flush();assert.ok(!h.classes.has('keyboard-open'));
 const before=h.writes();h.c.window.visualViewport.scale=2;h.c.window.visualViewport.height=250;h.viewportEvents.resize();h.flush();assert.equal(h.writes(),before);
});
