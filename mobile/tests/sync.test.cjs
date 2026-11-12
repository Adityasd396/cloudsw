const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {parseVideo,isYoutubeUrl,buildApplyScript,buildVideoLayoutScript,OBSERVER_SCRIPT}=require('../sync.cjs');
test('only official HTTPS YouTube pages are accepted',()=>{
 assert.equal(isYoutubeUrl('https://m.youtube.com/results?search_query=music'),true);
 for(const url of ['http://youtube.com/watch?v=aqz-KE-bpKQ','https://youtube.com.evil.test/watch','javascript:alert(1)','https://evil.test'])assert.equal(isYoutubeUrl(url),false);
 assert.equal(parseVideo('https://m.youtube.com/watch?v=aqz-KE-bpKQ'),'aqz-KE-bpKQ');
 assert.equal(parseVideo('https://youtube.com/shorts/aqz-KE-bpKQ'),'aqz-KE-bpKQ');
 assert.equal(parseVideo('https://youtube.com/watch?v=invalid'),null);
});
test('sync script corrects drift, pauses, and leaves ads alone',()=>{
 const video={readyState:4,duration:100,currentTime:1,paused:false,pause(){this.paused=true},play(){this.paused=false;return Promise.resolve()}};
 let ad=false;
 const context={location:{hostname:'m.youtube.com'},document:{querySelector(selector){return selector==='video'?video:ad?{}:null}},window:{}};
 vm.runInNewContext(buildApplyScript(40,false),context);
 assert.equal(video.currentTime,40);assert.equal(video.paused,true);
 ad=true;vm.runInNewContext(buildApplyScript(80,true),context);
 assert.equal(video.currentTime,40);assert.equal(video.paused,true);
 assert.throws(()=>buildApplyScript(NaN,true));
 new vm.Script(OBSERVER_SCRIPT);
});
test('video layout fills the view, preserves player descendants, and restores the page',()=>{
 const attributes=new Set();
 const ancestor={parentElement:null,setAttribute(name){attributes.add(name)},removeAttribute(name){attributes.delete(name)}};
 const player={parentElement:ancestor,setAttribute(name){attributes.add(name)},removeAttribute(name){attributes.delete(name)},hasAttribute(name){return attributes.has(name)}};
 const video={closest(){return player}};
 let style=null;
 const document={querySelector(selector){return selector==='video'?video:null},querySelectorAll(){return [player,ancestor]},getElementById(){return style},createElement(){return {textContent:'',remove(){style=null}}},head:{appendChild(node){style=node}}};
 const context={location:{hostname:'m.youtube.com'},document};
 vm.runInNewContext(buildVideoLayoutScript(true),context);
 assert.ok(style.textContent.includes('height:100vh'));
 assert.ok(style.textContent.includes('[data-afterglow-player] *{visibility:visible'));
 assert.ok(attributes.has('data-afterglow-player'));
 vm.runInNewContext(buildVideoLayoutScript(false),context);
 assert.equal(style,null);
 assert.equal(attributes.size,0);
});
