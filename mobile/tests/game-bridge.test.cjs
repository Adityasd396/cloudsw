const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm');
const {buildGameBridge}=require('../game-bridge.cjs');
test('native game bridge keeps room authentication in native requests and restricts API paths',async()=>{
 const sent=[],page={ReactNativeWebView:{postMessage:body=>sent.push(JSON.parse(body))},fetch:()=>Promise.resolve('asset')};const context={window:page,location:{href:'https://solace.test/static/game.html?room=123456',origin:'https://solace.test'},URL,Map,JSON,Promise,Error,Object};vm.createContext(context);vm.runInContext(buildGameBridge('123456'),context);
 const result=page.fetch('/api/rooms/123456/basketball',{body:JSON.stringify({action:'join'})});assert.equal(sent[0].path,'/api/rooms/123456/basketball');assert.deepEqual(sent[0].data,{action:'join'});page.__solaceGameReply(sent[0].id,{status:200,body:{scores:{X:1}}});assert.equal((await (await result).json()).scores.X,1);
 await assert.rejects(()=>page.fetch('/api/rooms/999999/basketball'));await assert.rejects(()=>page.fetch('https://evil.test/api/rooms/123456/game'));assert.equal(sent.length,1);
});
