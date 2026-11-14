// Chat-delivered gestures never take focus, pause playback, or cover controls.
const gestureStream=new SolaceGestures.Stream();
const gestureBadge=element('div','cute-gesture');gestureBadge.hidden=true;gestureBadge.setAttribute('role','status');gestureBadge.setAttribute('aria-live','polite');videoStage.append(gestureBadge);let gestureTimer=0;
function hideGesture(){gestureBadge.hidden=true;clearTimeout(gestureTimer);gestureTimer=0}
const gestureRender=render;render=function(data){gestureRender(data);const events=gestureStream.receive(data);if(document.hidden||activeScreen!=='watch'||loveOverlay){hideGesture();return}if(!events.length)return;const event=events.at(-1);gestureBadge.replaceChildren(element('span','gesture-art',event.emoji),element('span','',event.name+' · '+event.text));gestureBadge.hidden=false;clearTimeout(gestureTimer);gestureTimer=setTimeout(hideGesture,3200)};
document.addEventListener('visibilitychange',()=>{if(document.hidden)hideGesture()});window.addEventListener('pagehide',hideGesture);

// An in-flow tray reserves its own space above the composer, never over the keyboard.
const gestureToggle=element('button','gesture-toggle','♡'),gestureTray=element('div','gesture-tray');
gestureToggle.type='button';gestureToggle.setAttribute('aria-label','Cute gestures');gestureToggle.setAttribute('aria-expanded','false');gestureToggle.setAttribute('aria-controls','gestureTray');
gestureTray.id='gestureTray';gestureTray.hidden=true;gestureTray.setAttribute('role','group');gestureTray.setAttribute('aria-label','Send a cute gesture');
$('chatForm').insertBefore(gestureToggle,$('message'));$('chatForm').before(gestureTray);
function closeGestureTray(){gestureTray.hidden=true;document.body.classList.remove('gesture-picker-open');gestureToggle.setAttribute('aria-expanded','false');window.SolaceChat.layout()}
gestureToggle.onclick=()=>{gestureTray.hidden=!gestureTray.hidden;document.body.classList.toggle('gesture-picker-open',!gestureTray.hidden);gestureToggle.setAttribute('aria-expanded',String(!gestureTray.hidden));window.SolaceChat.layout()};
for(const [command,gesture]of Object.entries(SolaceGestures.commands)){
 const button=element('button','gesture-choice');button.type='button';button.dataset.command=command;button.setAttribute('aria-label','Send '+command.slice(1));button.title=gesture.text;
 const art=element('span','',gesture.emoji);art.setAttribute('aria-hidden','true');button.append(art,element('span','',command.slice(1)));gestureTray.append(button);
 button.onclick=async()=>{if(!state||chatSendPending)return;chatSendPending=true;const send=$('chatForm').querySelector('.send');send.disabled=true;for(const chip of gestureTray.children)chip.disabled=true;
  try{if(await action({action:'chat',body:command})){const keyboardFocus=document.activeElement===$('message');closeGestureTray();if(!keyboardFocus)gestureToggle.focus();window.SolaceChat.jump()}}
  finally{chatSendPending=false;send.disabled=false;for(const chip of gestureTray.children)chip.disabled=false}
 };
}
// Keep an already-open keyboard stable when tapping the toggle or a gesture.
for(const node of [gestureToggle,gestureTray])node.addEventListener('pointerdown',event=>{if(document.activeElement===$('message')&&event.target.closest('button'))event.preventDefault()});
document.addEventListener('pointerdown',event=>{if(!gestureTray.hidden&&!gestureTray.contains(event.target)&&!gestureToggle.contains(event.target))closeGestureTray()},{passive:true});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!gestureTray.hidden){event.preventDefault();event.stopImmediatePropagation();closeGestureTray();gestureToggle.focus()}},true);
new MutationObserver(()=>{if(activeScreen!=='watch')closeGestureTray()}).observe(document.body,{attributes:true,attributeFilter:['data-screen']});
if(window.ResizeObserver)new ResizeObserver(()=>window.SolaceChat.layout()).observe(gestureTray);
