const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../../static/love.js'),'utf8');
function client(){
 const nodes=[],audio=[];
 const element=(tag)=>({tag,append(){},setAttribute(){},addEventListener(){},showModal(){this.open=true},focus(){},remove(){this.removed=true}});
 const context={Math,render(){},element,ready:true,player:{isMuted:()=>false,mute:()=>audio.push('mute'),unMute:()=>audio.push('unmute')},document:{activeElement:{focus(){}},body:{append(node){nodes.push(node)}}}};
 vm.createContext(context);vm.runInContext(source,context);
 return {nodes,audio,receive:(id,messages)=>context.render({id,messages}),close:()=>context.closeLove()};
}
test('love command reaches both viewers once without replaying joined history',()=>{
 const host=client(),guest=client();
 for(const c of [host,guest]){
  c.receive('123456',[{id:1,body:'/iloveyou'}]);assert.equal(c.nodes.length,0);
  c.receive('123456',[{id:1,body:'/iloveyou'},{id:2,body:' /ILOVEYOU '}]);assert.equal(c.nodes.length,1);
  c.receive('123456',[{id:2,body:' /ILOVEYOU '}]);assert.equal(c.nodes.length,1);
  c.close();assert.equal(c.nodes[0].removed,true);assert.deepEqual(c.audio,['mute','unmute']);
  c.receive('123456',[{id:2,body:' /ILOVEYOU '}]);assert.equal(c.nodes.length,1);
  c.receive('123456',[{id:3,body:'I typed /iloveyou in a sentence'}]);assert.equal(c.nodes.length,1);
  c.receive('123456',[{id:4,body:'/iloveyou'}]);assert.equal(c.nodes.length,2);
  c.receive('654321',[{id:5,body:'/iloveyou'}]);assert.equal(c.nodes[1].removed,true);assert.equal(c.nodes.length,2);
 }
});
