const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {backAction,videoHeight,freshAdAlerts}=require('../experience.cjs');
test('back closes room surfaces and stays in the app at the root',()=>{
 const home={keyboardHeight:0,expanded:false,pickerMode:null,replyTo:null,tab:'chat',inRoom:true,entryMode:null};
 assert.equal(backAction(home),'stay');assert.equal(backAction({...home,keyboardHeight:300,expanded:true}),'keyboard');assert.equal(backAction({...home,expanded:true}),'fullscreen');assert.equal(backAction({...home,pickerMode:'add'}),'picker');assert.equal(backAction({...home,replyTo:{id:1}}),'reply');assert.equal(backAction({...home,inRoom:false,entryMode:'join'}),'home');
});
test('keyboard fitting reserves visible space above chat on both platforms',()=>{
 const ios=videoHeight({expanded:false,width:390,height:844,keyboardHeight:340,platform:'ios',ratio:16/9});
 const android=videoHeight({expanded:false,width:390,height:504,keyboardHeight:340,platform:'android',ratio:16/9});
 assert.equal(ios,android);assert.ok(ios>=90&&ios<160);assert.ok(videoHeight({expanded:false,width:390,height:844,keyboardHeight:0,platform:'ios',ratio:16/9})>ios);
});
test('ad alerts exclude self, deduplicate renewals and allow a later ad',()=>{
 const seen=new Set(),alerts=[{member_id:'me',started:1,you:true},{member_id:'friend',name:'Friend',started:2,you:false}];
 assert.equal(freshAdAlerts(alerts,seen).length,1);assert.equal(freshAdAlerts(alerts,seen).length,0);assert.equal(freshAdAlerts([{...alerts[1],started:3}],seen).length,1);
});
test('a completed reply swipe selects the message but a cancelled swipe does not',()=>{
 const source=fs.readFileSync(path.join(__dirname,'../../static/room-experience.js'),'utf8');const start=source.indexOf('function finishReplySwipe'),end=source.indexOf("for(const name of ['pointerup'",start);let selected=null;
 const context={Math,swipe:{id:7,dx:50,row:{style:{transform:'translateX(50px)'},dataset:{messageId:'1'}}},state:{messages:[{id:1,body:'hello'}]},chooseReply:message=>selected=message};
 vm.createContext(context);vm.runInContext(source.slice(start,end),context);context.finishReplySwipe({pointerId:7,type:'pointerup'});assert.equal(selected.id,1);
 selected=null;context.swipe={id:8,dx:50,row:{style:{},dataset:{messageId:'1'}}};context.finishReplySwipe({pointerId:8,type:'pointercancel'});assert.equal(selected,null);
});
