// Shared chat delivery triggers the surprise once, without replaying old history.
let loveRoom=null,loveCursor=null,loveOverlay=null,lovePreviousFocus=null,loveWasMuted=null;
function closeLove(){
  if(!loveOverlay)return;
  loveOverlay.remove();loveOverlay=null;
  if(loveWasMuted===false&&ready)try{player.unMute()}catch{}
  loveWasMuted=null;lovePreviousFocus?.focus();
}
function openLove(){
  if(loveOverlay)return;
  lovePreviousFocus=document.activeElement;
  try{if(ready){loveWasMuted=player.isMuted();player.mute()}}catch{}
  loveOverlay=element('dialog','love-overlay');
  const close=element('button','love-close','Close ♡');close.type='button';close.setAttribute('aria-label','Close love surprise');close.onclick=closeLove;
  const frame=element('iframe','love-frame');frame.title='For Jaanu, with love';frame.src='/static/love.html';frame.allow='autoplay; fullscreen';
  loveOverlay.setAttribute('aria-label','A little love for Jaanu');loveOverlay.append(close,frame);
  loveOverlay.addEventListener('cancel',event=>{event.preventDefault();closeLove()});
  document.body.append(loveOverlay);loveOverlay.showModal();close.focus();
}
const loveRender=render;
render=function(data){
  loveRender(data);
  const messages=data.messages||[],latest=Math.max(0,...messages.map(message=>message.id));
  if(loveRoom!==data.id){closeLove();loveRoom=data.id;loveCursor=latest;return}
  const surprise=messages.some(message=>message.id>loveCursor&&message.body.trim().toLowerCase()==='/iloveyou');
  loveCursor=Math.max(loveCursor,latest);
  if(surprise)openLove();
};
