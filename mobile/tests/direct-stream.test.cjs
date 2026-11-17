const test=require('node:test'),assert=require('node:assert/strict');
const {isDirectUrl,directHtml,mediaPage}=require('../direct-stream.cjs');
const {parseVideo,buildApplyScript,OBSERVER_SCRIPT}=require('../sync.cjs');
test('direct media is HTTPS-only and never accepts provider pages or credentials',()=>{
 const url='https://media.example/movie.mp4?signature=123';assert.ok(isDirectUrl(url));assert.equal(parseVideo(url),url);assert.equal(mediaPage(url),url);assert.equal(mediaPage('aqz-KE-bpKQ'),'https://m.youtube.com/watch?v=aqz-KE-bpKQ');
 for(const url of ['http://media.example/a.mp4','https://user:password@media.example/a.mp4','javascript:alert(1)','https://www.netflix.com/watch/1'])assert.equal(isDirectUrl(url),false);
 assert.throws(()=>directHtml('javascript:alert(1)'));assert.ok(directHtml(url).includes('playsinline'));assert.ok(OBSERVER_SCRIPT.includes('window.__solaceDirectSource||location.href'));assert.ok(buildApplyScript(20,true).includes('!window.__solaceDirectSource'));
});
