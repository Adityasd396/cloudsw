const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {parse,Stream}=require('../gestures.cjs');
test('gesture commands match exactly, preserve the love command and match web/native',()=>{
 assert.equal(parse(' /HUG ').emoji,'🫂');assert.equal(parse('/kiss').emoji,'😘');assert.equal(parse('/iloveyou'),null);assert.equal(parse('please /hug'),null);assert.equal(parse('/hug extra'),null);assert.equal(parse('toString'),null);
 assert.equal(fs.readFileSync(path.join(__dirname,'../gestures.cjs'),'utf8'),fs.readFileSync(path.join(__dirname,'../../static/gestures.js'),'utf8'));
});
test('both users receive gestures once without replay on join, polling or restore',()=>{
 for(const stream of [new Stream(),new Stream()]){
  const data={id:'123456',storage_generation:'a',messages:[{id:1,body:'/hug'}]};assert.equal(stream.receive(data).length,0);
  data.messages.push({id:2,name:'Jaanu',body:'/kiss'});assert.equal(stream.receive(data)[0].name,'Jaanu');assert.equal(stream.receive(data).length,0);
  data.storage_generation='b';data.messages=[{id:1,body:'/cuddle'}];assert.equal(stream.receive(data).length,0);
  data.messages.push({id:2,body:'/cheer'});assert.equal(stream.receive(data)[0].command,'/cheer');data.id='654321';assert.equal(stream.receive(data).length,0);
 }
});
