const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {playbackLabel}=require('../experience-model.cjs'),{backAction}=require('../experience.cjs');
test('playback status describes local readiness separately from room intent',()=>{
 const s={ready:true,playing:true,mode:1};
 for(const [change,label] of [[{},'Playing'],[{mode:3},'Buffering'],[{mode:2},'Tap to resume'],[{ready:false},'Loading'],[{ad:true},'Ad playing'],[{notice:'blocked'},'Tap to resume'],[{notice:'error'},'Playback unavailable'],[{connected:false},'Reconnecting'],[{recovering:true},'Reconnecting'],[{offline:true},'Offline'],[{playing:false,mode:2},'Paused']])assert.equal(playbackLabel({...s,...change}),label);
 assert.equal(fs.readFileSync(path.join(__dirname,'../experience-model.cjs'),'utf8'),fs.readFileSync(path.join(__dirname,'../../static/experience-model.js'),'utf8'));
});
test('back follows settings ancestry without clearing a reply on a hidden chat screen',()=>{
 const s={keyboardHeight:0,expanded:false,pickerMode:null,replyTo:{id:1},inRoom:true};
 assert.equal(backAction({...s,tab:'privacy'}),'settings');assert.equal(backAction({...s,tab:'settings'}),'people');assert.equal(backAction({...s,tab:'playlist'}),'chat');assert.equal(backAction({...s,tab:'chat'}),'reply');
});
