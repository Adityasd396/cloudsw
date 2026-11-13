const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../../static/fullscreen.js'),'utf8');
test('iPhone fallback enters and exits when element fullscreen is missing or denied',async()=>{
 const classes=new Set(),events={};
 const context={document:{body:{classList:{contains:name=>classes.has(name),add:name=>classes.add(name),remove:name=>classes.delete(name)}},addEventListener:(name,fn)=>events[name]=fn}};
 vm.createContext(context);vm.runInContext(source,context);
 await context.toggleSolaceFullscreen({});assert.equal(classes.has('solace-fullscreen'),true);
 await context.toggleSolaceFullscreen({});assert.equal(classes.has('solace-fullscreen'),false);
 await context.toggleSolaceFullscreen({requestFullscreen:()=>Promise.reject(Error('unsupported'))});assert.equal(classes.has('solace-fullscreen'),true);
 events.keydown({key:'Escape'});assert.equal(classes.has('solace-fullscreen'),false);
 let calls=0;await context.toggleSolaceFullscreen({webkitRequestFullscreen(){calls++}});assert.equal(calls,1);
 events.webkitfullscreenchange();assert.equal(classes.has('solace-fullscreen'),false);
});
