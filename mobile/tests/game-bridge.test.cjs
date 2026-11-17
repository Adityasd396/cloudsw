const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm');
const {buildGameBridge}=require('../game-bridge.cjs');
test('native game bridge keeps room authentication in native requests and restricts API paths',async()=>{
 const sent=[],page={ReactNativeWebView:{postMessage:body=>sent.push(JSON.parse(body))},fetch:()=>Promise.resolve('asset')};const context={window:page,location:{href:'https://solace.test/static/game.html?room=123456',origin:'https://solace.test'},URL,Map,JSON,Promise,Error,Object};vm.createContext(context);vm.runInContext(buildGameBridge('123456'),context);
 const result=page.fetch('/api/rooms/123456/basketball',{body:JSON.stringify({action:'join'})});assert.equal(sent[0].path,'/api/rooms/123456/basketball');assert.deepEqual(sent[0].data,{action:'join'});page.__solaceGameReply(sent[0].id,{status:200,body:{scores:{X:1}}});assert.equal((await (await result).json()).scores.X,1);
 const ludo=page.fetch('/api/rooms/123456/ludo',{body:JSON.stringify({action:'roll',revision:2})});assert.equal(sent[1].path,'/api/rooms/123456/ludo');page.__solaceGameReply(sent[1].id,{status:200,body:{dice:6}});assert.equal((await (await ludo).json()).dice,6);
 await assert.rejects(()=>page.fetch('/api/rooms/999999/basketball'));await assert.rejects(()=>page.fetch('https://evil.test/api/rooms/123456/game'));await assert.rejects(()=>page.fetch('/api/rooms/999999/ludo'));assert.equal(sent.length,2);
});
