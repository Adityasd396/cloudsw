(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.SolaceSession=factory()})(typeof globalThis!=='undefined'?globalThis:this,function(){
 function pollPath(room,cursor,generation){const hasCursor=Number.isSafeInteger(cursor)&&cursor>=0;return '/api/rooms/'+encodeURIComponent(room)+(hasCursor?'?after='+cursor:'')+(generation?(hasCursor?'&':'?')+'generation='+encodeURIComponent(generation):'')}
 function mergeRoomMessages(previous,next){
  if(!next.messages_delta)return next;
  const messages=new Map();if(previous?.id===next.id&&(!previous.storage_generation||!next.storage_generation||previous.storage_generation===next.storage_generation))for(const message of previous.messages||[])messages.set(message.id,message);
  for(const message of next.messages||[])messages.set(message.id,message);
  return {...next,messages:[...messages.values()].sort((a,b)=>a.id-b.id).slice(-100)};
 }
 function isOlderSnapshot(previous,next){if(!previous||previous.id!==next.id)return false;if(previous.storage_generation&&next.storage_generation&&previous.storage_generation!==next.storage_generation)return false;const before=previous.playback_revision||0,after=next.playback_revision||0;return after<before||after===before&&next.server_time<previous.server_time}
 class RecoveryGate{
  constructor(onRecovered){this.onRecovered=onRecovered;this.active=true;this.recovering=false;this.epoch=0;this.readyAt=0;this.reloads=[]}
  suspend(){this.active=false;this.recovering=true;this.epoch++}
  begin(){this.active=true;this.recovering=true;return ++this.epoch}
  complete(epoch,now=Date.now()){if(this.active&&epoch===this.epoch&&this.recovering){this.recovering=false;this.readyAt=now+1500;try{this.onRecovered?.()}catch{}return true}return false}
  canPublish(now=Date.now()){return this.active&&!this.recovering&&now>=this.readyAt}
  allowReload(now=Date.now()){this.reloads=this.reloads.filter(time=>now-time<60000);if(this.reloads.length>=3)return false;this.reloads.push(now);return true}
  reset(){this.active=true;this.recovering=false;this.readyAt=0;this.epoch++;this.reloads=[]}
 }
 class AutoHideControls{
  constructor(delay=3000){this.delay=delay;this.visible=true;this.playing=false;this.focused=false;this.lastInput=0}
  show(now=Date.now()){this.visible=true;this.lastInput=now;return true}
  toggle(now=Date.now()){if(this.visible&&this.playing&&!this.focused)this.visible=false;else this.show(now);return this.visible}
  update(playing,now=Date.now()){if(this.playing!==playing){this.playing=playing;this.show(now)}if(this.focused)this.show(now);else if(now-this.lastInput>=this.delay)this.visible=false;return this.visible}
 }
 return {pollPath,mergeRoomMessages,RecoveryGate,AutoHideControls,isOlderSnapshot};
});
