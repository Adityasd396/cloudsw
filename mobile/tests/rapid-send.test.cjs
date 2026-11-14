const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
test('rapid Enter sends once while pending and keeps the next draft and reply',async()=>{
 const source=fs.readFileSync(path.join(__dirname,'../../static/room-experience.js'),'utf8');const start=source.indexOf('let chatSendPending='),end=source.indexOf('let swipe=',start);let finish,calls=0;
 const button={disabled:false},input={value:'First message'},form={querySelector:()=>button},list={scrollTop:0,scrollHeight:200};const c={state:{},replyTarget:{id:1},replyPreview:{hidden:false},$:id=>id==='chatForm'?form:id==='message'?input:list,action:()=>{calls++;return new Promise(resolve=>finish=resolve)}};vm.createContext(c);vm.runInContext(source.slice(start,end),c);
 const event={preventDefault(){}};const first=form.onsubmit(event);for(let i=0;i<20;i++)form.onsubmit(event);assert.equal(calls,1);assert.equal(button.disabled,true);
 input.value='My next draft';c.replyTarget={id:2};finish({});await first;assert.equal(input.value,'My next draft');assert.equal(c.replyTarget.id,2);assert.equal(button.disabled,false);
 const retry=form.onsubmit(event);finish(null);await retry;assert.equal(input.value,'My next draft');assert.equal(button.disabled,false);
});
