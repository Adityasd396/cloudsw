const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {shouldBlock,appleRules,BLOCKER_SCRIPT}=require('../blocker.cjs');
const {patchAndroid,patchApple}=require('../scripts/install-content-blocker.cjs');
test('ad filters match host boundaries and leave content, login and media alone',()=>{
 for(const url of ['https://googleads.g.doubleclick.net/pagead/ads','https://ads.googleadservices.com/pagead/a','https://m.youtube.com/pagead/adview','https://www.youtube.com/api/stats/ads?x=1'])assert.equal(shouldBlock(url),true,url);
 for(const url of ['https://m.youtube.com/watch?v=aqz-KE-bpKQ','https://m.youtube.com/youtubei/v1/player','https://rr1---sn-example.googlevideo.com/videoplayback','https://accounts.google.com/signin','https://i.ytimg.com/vi/a/default.jpg','https://notdoubleclick.net/a','https://doubleclick.net.evil.test/a','data:text/plain,hello'])assert.equal(shouldBlock(url),false,url);
 for(const rule of appleRules())new RegExp(rule.trigger['url-filter']);
 new vm.Script(BLOCKER_SCRIPT);
});
test('native installer is repeatable and refuses unknown upstream layouts',()=>{
 const root=path.dirname(require.resolve('react-native-webview/package.json'));
 const android=fs.readFileSync(path.join(root,'android/src/main/java/com/reactnativecommunity/webview/RNCWebViewClient.java'),'utf8');
 const apple=fs.readFileSync(path.join(root,'apple/RNCWebViewImpl.m'),'utf8');
 const a=patchAndroid(android),i=patchApple(apple);
 assert.equal(patchAndroid(a),a);assert.equal(patchApple(i),i);
 assert.equal((a.match(/public WebResourceResponse shouldInterceptRequest/g)||[]).length,1);
 assert.ok(a.includes('!request.isForMainFrame()'));
 assert.ok(i.includes('WKContentRuleListStore'));
 assert.throws(()=>patchAndroid('unknown layout'));
 assert.throws(()=>patchApple('unknown layout'));
});
test('page filter blocks ad fetches and removes only ad fields from player responses',async()=>{
 let calls=0;
 const originalData={adPlacements:[{ad:1}],playerAds:[{}],adSlots:[{}],videoDetails:{videoId:'aqz-KE-bpKQ'},streamingData:{formats:[{url:'https://example.googlevideo.com/content'}]}};
 const context={location:{hostname:'m.youtube.com',href:'https://m.youtube.com/'},URL,Response,Headers,setInterval(){},document:{head:null},window:{ytInitialPlayerResponse:structuredClone(originalData),fetch:async()=>{calls++;return new Response(JSON.stringify(originalData),{status:200,headers:{'content-type':'application/json'}})}}};
 vm.runInNewContext(BLOCKER_SCRIPT,context);
 const blocked=await context.window.fetch('https://googleads.g.doubleclick.net/pagead/ads');
 assert.equal(blocked.status,204);assert.equal(calls,0);
 const filtered=await context.window.fetch('https://m.youtube.com/youtubei/v1/player?prettyPrint=false');
 const data=await filtered.json();assert.equal(data.adPlacements,undefined);assert.deepEqual(data.streamingData,originalData.streamingData);assert.deepEqual(data.videoDetails,originalData.videoDetails);
 assert.equal(context.window.ytInitialPlayerResponse.playerAds,undefined);
 const untouched=await context.window.fetch('https://m.youtube.com/youtubei/v1/browse');
 assert.deepEqual((await untouched.json()).adSlots,originalData.adSlots);
});
