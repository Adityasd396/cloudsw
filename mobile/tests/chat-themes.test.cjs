const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {themes,valid}=require('../chat-themes.cjs');
test('saved chat themes accept known choices and keep message text readable on both clients',()=>{
 const luminance=hex=>{const c=hex.slice(1).match(/../g).map(n=>parseInt(n,16)/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);return .2126*c[0]+.7152*c[1]+.0722*c[2]};
 for(const key of Object.keys(themes)){assert.equal(valid(key),key);for(const color of [themes[key].mine,themes[key].received])assert.ok((luminance('#f5edf8')+.05)/(luminance(color)+.05)>=4.5,key+' contrast')}
 assert.equal(valid('__proto__'),'solace');assert.equal(valid(null),'solace');
 assert.equal(fs.readFileSync(path.join(__dirname,'../chat-themes.cjs'),'utf8'),fs.readFileSync(path.join(__dirname,'../../static/chat-themes.js'),'utf8'));
});
