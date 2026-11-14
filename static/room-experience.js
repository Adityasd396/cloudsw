let replyTarget=null,experienceRoom=state?.id||null,experienceCursor=state?Math.max(0,...state.messages.map(m=>m.id)):null;
const replyPreview=element('div','reply-preview');replyPreview.hidden=true;
const replyText=element('span'),cancelReply=element('button','subtle','×');cancelReply.type='button';cancelReply.setAttribute('aria-label','Cancel reply');
cancelReply.onclick=()=>{replyTarget=null;replyPreview.hidden=true};replyPreview.append(replyText,cancelReply);$('chatForm').before(replyPreview);
function chooseReply(message){replyTarget=message;replyText.textContent='Reply to '+message.name+' · '+message.body.slice(0,120);replyPreview.hidden=false;$('message').focus()}
let chatSendPending=false;
$('chatForm').onsubmit=async event=>{event.preventDefault();if(!state||chatSendPending)return;const body=$('message').value.trim();if(!body)return;chatSendPending=true;const send=$('chatForm').querySelector('.send');send.disabled=true;const replying=replyTarget;
 try{if(await action({action:'chat',body,...(replying?{reply_to:replying.id}:{})})){if($('message').value.trim()===body)$('message').value='';if(replyTarget===replying){replyTarget=null;replyPreview.hidden=true}$('messages').scrollTop=$('messages').scrollHeight}}
 finally{chatSendPending=false;send.disabled=false}
};
let swipe=null;
$('messages').addEventListener('pointerdown',event=>{const row=event.target.closest('.chat-message');if(!row||event.target.closest('button')||event.pointerType==='mouse'&&event.button!==0)return;swipe={row,id:event.pointerId,x:event.clientX,y:event.clientY,dx:0}});
$('messages').addEventListener('pointermove',event=>{if(!swipe||event.pointerId!==swipe.id)return;const dx=event.clientX-swipe.x,dy=event.clientY-swipe.y;if(Math.abs(dx)>12&&Math.abs(dx)>Math.abs(dy)*1.5){swipe.dx=dx;try{swipe.row.setPointerCapture(event.pointerId)}catch{}swipe.row.style.transform='translateX('+Math.max(-55,Math.min(55,dx))+'px)';if(event.cancelable)event.preventDefault()}});
function finishReplySwipe(event){if(!swipe||event.pointerId!==swipe.id)return;const gesture=swipe;swipe=null;gesture.row.style.transform='';if(event.type!=='pointercancel'&&Math.abs(gesture.dx)>40){const message=state?.messages.find(m=>String(m.id)===gesture.row.dataset.messageId);if(message)chooseReply(message)}}
for(const name of ['pointerup','pointercancel'])$('messages').addEventListener(name,finishReplySwipe);

const activityOverlay=element('div','presence-overlay');activityOverlay.setAttribute('aria-label','Participant activity');videoStage.append(activityOverlay);
const liveChat=element('div','live-chat-overlay');liveChat.setAttribute('aria-hidden','true');videoStage.append(liveChat);
const adPopup=element('div','in-app-ad-alert');adPopup.hidden=true;adPopup.setAttribute('role','status');videoStage.append(adPopup);
let adTimeout;const seenAds=new Set();
function updateRoomOverlays(data){
 const people=data.participants||data.members;
 activityOverlay.replaceChildren(...people.slice(0,6).map(person=>{const chip=element('span','presence-chip');const dot=element('i','activity-dot '+(person.status||'active'));chip.append(dot,element('span','',person.name+(person.is_host?' 👑':'')));chip.title=person.name+' · '+(person.status||'active');return chip}));
 if(people.length>6)activityOverlay.append(element('span','presence-chip','+'+(people.length-6)));
 const alerts=(data.ad_alerts||[]).filter(alert=>!alert.you&&!seenAds.has(alert.member_id+':'+alert.started));if(alerts.length){alerts.forEach(alert=>seenAds.add(alert.member_id+':'+alert.started));adPopup.textContent=alerts.map(alert=>alert.name).join(', ')+(alerts.length>1?' are':' is')+' seeing a YouTube ad';adPopup.hidden=false;clearTimeout(adTimeout);adTimeout=setTimeout(()=>adPopup.hidden=true,7000)}
 for(const dialog of document.querySelectorAll('dialog[open]')){dialog.querySelector('.presence-overlay')?.remove();dialog.querySelector('.in-app-ad-alert')?.remove();dialog.append(activityOverlay.cloneNode(true),adPopup.cloneNode(true))}
 if(seenAds.size>200){const latest=[...seenAds].slice(-100);seenAds.clear();latest.forEach(key=>seenAds.add(key))}
}
const experienceRender=render;
render=function(data){
 experienceRender(data);updateRoomOverlays(data);
 for(const row of $('messages').querySelectorAll('.chat-message')){if(row.querySelector('.reply-action'))continue;const button=element('button','reply-action','↩');button.type='button';button.setAttribute('aria-label','Reply to message');button.onclick=()=>{const message=data.messages.find(m=>String(m.id)===row.dataset.messageId);if(message)chooseReply(message)};row.append(button)}
 const latest=Math.max(0,...data.messages.map(m=>m.id));
 if(experienceRoom!==data.id||experienceCursor===null){experienceRoom=data.id;experienceCursor=latest;liveChat.replaceChildren();replyTarget=null;replyPreview.hidden=true;return}
 for(const message of data.messages){if(message.id<=experienceCursor)continue;const bubble=element('div','float-chat-message');bubble.append(element('strong','',message.name+(message.is_host?' 👑':'')),element('span','',message.body.slice(0,150)));liveChat.append(bubble);while(liveChat.childElementCount>4)liveChat.firstElementChild.remove();setTimeout(()=>bubble.remove(),6500)}
 experienceCursor=Math.max(experienceCursor,latest);
};
let restingViewportHeight=innerHeight,restingViewportWidth=innerWidth,viewportFrame=0,keyboardVisible=false,lastViewportStyle='';
function fitChatViewport(){
 viewportFrame=0;
 const viewport=window.visualViewport,height=viewport?.height||innerHeight,width=innerWidth;
 // Pinch zoom is a browser interaction, not a keyboard resize.
 if(viewport?.scale&&Math.abs(viewport.scale-1)>.05)return;
 const focused=document.activeElement===$('message');
 if(Math.abs(width-restingViewportWidth)>100){restingViewportWidth=width;restingViewportHeight=innerHeight;keyboardVisible=false}
 const gap=Math.max(innerHeight,restingViewportHeight)-height;
 // Hysteresis keeps the footer from flashing back during the closing animation.
 keyboardVisible=(focused||keyboardVisible)&&gap>(keyboardVisible?40:80);
 if(!focused&&!keyboardVisible)restingViewportHeight=height;
 const top=keyboardVisible?Math.max(0,viewport?.offsetTop||0):0,signature=height+':'+top;
 if(signature!==lastViewportStyle){lastViewportStyle=signature;document.documentElement.style.setProperty('--room-vh',height+'px');document.documentElement.style.setProperty('--room-top',top+'px')}
 document.body.classList.toggle('keyboard-open',keyboardVisible);
 window.SolaceChat?.layout();
}
function queueChatViewport(){if(!viewportFrame)viewportFrame=requestAnimationFrame(fitChatViewport)}
window.visualViewport?.addEventListener('resize',queueChatViewport,{passive:true});window.visualViewport?.addEventListener('scroll',queueChatViewport,{passive:true});
window.addEventListener('resize',queueChatViewport,{passive:true});document.addEventListener('focusin',queueChatViewport);document.addEventListener('focusout',queueChatViewport);window.addEventListener('pageshow',queueChatViewport);window.addEventListener('pagehide',()=>{if(viewportFrame)cancelAnimationFrame(viewportFrame);viewportFrame=0});fitChatViewport();

// Back closes the current room surface; leaving remains an explicit action.
let guardedRoom=null;
const guardRender=render;render=function(data){if(SolaceSession.isOlderSnapshot(state,data))return;data=SolaceSession.mergeRoomMessages(state,data);guardRender(data);if(guardedRoom!==data.id){guardedRoom=data.id;history.pushState({solaceRoom:data.id},'',location.href)}};
window.addEventListener('popstate',()=>{if(!state||!roomId)return;history.pushState({solaceRoom:roomId},'','/?room='+encodeURIComponent(roomId));
 if(document.activeElement?.matches('input,textarea')){document.activeElement.blur();return}
 if(document.body.classList.contains('solace-fullscreen')){exitSolaceFullscreen();return}
 if(!picker.hidden){picker.hidden=true;return}
 if(loveOverlay){closeLove();return}
 const dialog=[...document.querySelectorAll('dialog[open]')].at(-1);if(dialog)dialog.querySelector('button')?.click();
});

// Iframe players cannot expose their ad state. Web participants can report it.
let myAdActive=false;
const reportAdButton=element('button','subtle','Ad playing');reportAdButton.type='button';reportAdButton.setAttribute('aria-pressed','false');
async function reportMyAd(active){try{await api('/api/rooms/'+encodeURIComponent(roomId),{action:'ad_status',active});myAdActive=active;reportAdButton.textContent=active?'Ad ended':'Ad playing';reportAdButton.setAttribute('aria-pressed',String(active))}catch(error){toast(error.message)}}
reportAdButton.onclick=()=>reportMyAd(!myAdActive);document.querySelector('.compact-player-controls').append(reportAdButton);
setInterval(()=>{if(myAdActive&&!document.hidden&&roomId&&state)reportMyAd(true)},4000);

// Best-effort browser screen wake lock; released on pause/hidden/exit.
let streamWakeLock=null,wakeRequestPending=false,nextWakeAttempt=0;
async function maintainStreamWakeLock(){
 const wanted=!!state?.playing&&!document.hidden;
 if(!wanted){if(streamWakeLock){const old=streamWakeLock;streamWakeLock=null;old.release().catch(()=>{})}return}
 if(!navigator.wakeLock||streamWakeLock||wakeRequestPending||Date.now()<nextWakeAttempt)return;
 wakeRequestPending=true;
 try{const lock=await navigator.wakeLock.request('screen');if(!state?.playing||document.hidden){await lock.release();return}streamWakeLock=lock;lock.addEventListener('release',()=>{if(streamWakeLock===lock)streamWakeLock=null})}
 catch{nextWakeAttempt=Date.now()+60000}
 finally{wakeRequestPending=false}
}
const wakeRender=render;render=function(data){wakeRender(data);maintainStreamWakeLock()};
document.addEventListener('visibilitychange',()=>{nextWakeAttempt=0;maintainStreamWakeLock()});window.addEventListener('pagehide',()=>{if(streamWakeLock)streamWakeLock.release().catch(()=>{});streamWakeLock=null});
