const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function harness(visual=true){
 let now=0,id=0,position=0;const timers=new Map(),frames=new Map(),handlers={},viewportHandlers={},inputHandlers={};
 const listHandlers={};const list={setAttribute(){},addEventListener:(name,fn)=>listHandlers[name]=fn,getBoundingClientRect:()=>({top:0,bottom:350}),querySelectorAll:()=>[],scrollHeight:1800,clientHeight:350,get scrollTop(){return position},set scrollTop(n){position=Math.max(0,Math.min(n,this.scrollHeight-this.clientHeight))}};
 const composer={value:'Unsent reply ♡',addEventListener:(name,fn)=>inputHandlers[name]=fn,focus(){throw Error('Scrolling must not focus the page')}};
 let mutations,resize;const fail=()=>{throw Error('Chat touched playback or network')};
 const formHandlers={};const document={activeElement:null};const context={document,state:{},$:name=>name==='messages'?list:name==='message'?composer:{addEventListener:(name,fn)=>formHandlers[name]=fn},typingLine:{},replyPreview:{},api:fail,player:new Proxy({},{get:fail}),requestAnimationFrame:fn=>{frames.set(++id,fn);return id},cancelAnimationFrame:n=>frames.delete(n),setTimeout:(fn,delay)=>{timers.set(++id,{fn,at:now+delay});return id},clearTimeout:n=>timers.delete(n),MutationObserver:class{constructor(fn){mutations=fn}observe(){}},ResizeObserver:class{constructor(fn){resize=fn}observe(){}},window:{ResizeObserver:true,visualViewport:visual?{addEventListener:(name,fn)=>viewportHandlers[name]=fn}:undefined,addEventListener:(name,fn)=>handlers[name]=fn}};
 vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../../static/chat-scroll.js'),'utf8'),context);
 const flush=()=>{const work=[...frames.values()];frames.clear();work.forEach(fn=>fn())};
 function advance(ms){now+=ms;const due=[...timers].filter(([,t])=>t.at<=now);for(const [key,t] of due){timers.delete(key);t.fn()}flush()}
 return {document,listHandlers,context,list,composer,inputHandlers,viewportHandlers,handlers,formHandlers,mutate:()=>mutations(),resize:()=>resize(),flush,advance,timers,frames};
}
for(const platform of ['iPhone visual viewport','Android resized viewport'])test(platform+': open, type, incoming message, close and delayed layout stay pinned',()=>{
 const h=harness();h.flush();assert.equal(h.list.scrollTop,1450);
 h.inputHandlers.focus();h.list.clientHeight=180;h.viewportHandlers.resize();h.flush();assert.equal(h.list.scrollTop,1620);
 h.list.scrollHeight+=100;h.mutate();h.inputHandlers.input();h.flush();assert.equal(h.list.scrollTop,1720);
 h.inputHandlers.blur();h.flush();
 // Closing the keyboard may change layout after blur without a final resize event.
 h.list.clientHeight=350;h.advance(120);assert.equal(h.list.scrollTop,1550);
 h.list.scrollHeight+=60;h.advance(180);assert.equal(h.list.scrollTop,1610);
 h.list.clientHeight=400;h.advance(300);assert.equal(h.list.scrollTop,1560);
 assert.equal(h.composer.value,'Unsent reply ♡');assert.equal(h.timers.size,0);
});
test('keyboard animation event storms have bounded work and pagehide cancels pending scrolls',()=>{
 const h=harness();for(let i=0;i<1000;i++){h.viewportHandlers.resize();h.viewportHandlers.scroll();h.resize();h.inputHandlers.input()}
 assert.equal(h.timers.size,3);assert.equal(h.frames.size,1);h.flush();assert.equal(h.list.scrollTop,1450);
 h.handlers.pagehide();assert.equal(h.timers.size,0);assert.equal(h.frames.size,0);
});
test('no visual viewport support still follows ordinary window resize and blur',()=>{
 const h=harness(false);h.flush();h.list.clientHeight=150;h.handlers.resize();h.flush();assert.equal(h.list.scrollTop,1650);
 h.list.clientHeight=350;h.inputHandlers.blur();h.advance(600);assert.equal(h.list.scrollTop,1450);
});

test('reading older messages keeps position until New messages is selected',()=>{
 const h=harness();h.flush();h.list.scrollTop=200;h.listHandlers.scroll();h.context.window.SolaceChat.beforeUpdate();h.list.scrollHeight+=100;h.mutate();h.flush();assert.equal(h.list.scrollTop,300);
 const button={hidden:true};h.context.window.SolaceChat.setButton(button);assert.equal(button.hidden,false);button.onclick();h.flush();assert.equal(h.list.scrollTop,1550);assert.equal(button.hidden,true);
});

test('keyboard layout scroll events cannot unpin latest chat during blur and closing',()=>{
 const h=harness();h.flush();h.inputHandlers.blur();h.flush();h.list.clientHeight=150;h.listHandlers.scroll();h.list.scrollHeight+=90;h.mutate();h.flush();assert.equal(h.list.scrollTop,1740);
 h.listHandlers.pointerdown();h.list.scrollTop=200;h.listHandlers.scroll();h.list.scrollHeight+=80;h.mutate();h.flush();assert.equal(h.list.scrollTop,200);
});

test('touching Send preserves composer focus without blocking other controls',()=>{
 const h=harness();h.document.activeElement=h.composer;let prevented=0;
 h.formHandlers.pointerdown({target:{closest:()=>true},preventDefault:()=>prevented++});assert.equal(prevented,1);
 h.formHandlers.pointerdown({target:{closest:()=>false},preventDefault:()=>prevented++});assert.equal(prevented,1);
 h.document.activeElement=null;h.formHandlers.pointerdown({target:{closest:()=>true},preventDefault:()=>prevented++});assert.equal(prevented,1);
});
