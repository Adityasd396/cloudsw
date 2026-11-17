const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ts=require('typescript');
test('rotation preference survives a late initial read and serializes rapid changes',async()=>{
 let finishRead,finishWrite;const writes=[],listeners=[];
 const storage={getItem:()=>new Promise(resolve=>finishRead=resolve),setItem:(_,value)=>{writes.push(value);return writes.length===1?new Promise(resolve=>finishWrite=resolve):Promise.resolve()}};
 const exports={},context={exports,require:()=>storage,Promise,Set};
 const source=fs.readFileSync(require('node:path').join(__dirname,'../ExperiencePreferences.ts'),'utf8');
 vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,context);
 const unsubscribe=exports.subscribeRotation(()=>listeners.push(exports.getAutoFullscreen()));
 exports.setAutoFullscreen(false);exports.setAutoFullscreen(true);finishRead('false');
 for(let i=0;i<8;i++)await Promise.resolve();
 assert.equal(exports.getAutoFullscreen(),true);assert.deepEqual(writes,['false']);assert.deepEqual(listeners,[false,true]);
 finishWrite();for(let i=0;i<8;i++)await Promise.resolve();assert.deepEqual(writes,['false','true']);unsubscribe();
 exports.setAutoFullscreen(false);assert.deepEqual(listeners,[false,true]);
});
