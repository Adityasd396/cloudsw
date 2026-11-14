// Best-effort operational snapshots. No permission APIs, typed text, or playback writes.
let diagnosticTimer=0,diagnosticBusy=false,diagnosticLast=0,diagnosticRoom=null,diagnosticSignature='',diagnosticRtt;
function diagnosticSnapshot(){
 const viewport=window.visualViewport,network=navigator.connection;
 const value={client:'web',platform:navigator.userAgentData?.platform||navigator.platform||'unknown',release:state?.release_version||'development',language:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,width:Math.round(viewport?.width||innerWidth),height:Math.round(viewport?.height||innerHeight),pixel_ratio:devicePixelRatio,orientation:innerWidth>innerHeight?'landscape':'portrait',visibility:document.hidden?'hidden':'visible',connection:navigator.onLine?'online':'offline',screen:activeScreen,keyboard:document.body.classList.contains('keyboard-open'),typing:!!$('message').value,fullscreen:document.body.classList.contains('solace-fullscreen'),ready:!!ready,playback:'unavailable',error:!playerNotice.hidden?'player_error':pollFailures?'network_error':'none',request_rtt_ms:diagnosticRtt,network_type:network?.effectiveType||'unknown',network_rtt_ms:network?.rtt,downlink_mbps:network?.downlink};
 if(ready)try{const mode=player.getPlayerState();value.playback=({1:'playing',2:'paused',3:'buffering',0:'ended','-1':'loading',5:'paused'})[mode]||'unavailable';value.position=player.getCurrentTime();value.duration=player.getDuration();value.muted=player.isMuted();value.volume=player.getVolume?.();if([1,2].includes(mode)&&!state.host_ad){const expected=state.position+(state.playing?Math.max(0,state.server_time-state.updated)+(performance.now()-roomReceivedAt)/1000:0);value.drift_ms=Math.abs(value.position-expected)*1000}}catch{}
 return value;
}
async function sendDiagnostics(final=false){
 clearTimeout(diagnosticTimer);diagnosticTimer=0;if(!state||!roomId||diagnosticBusy)return;
 if(!final&&Date.now()-diagnosticLast<2100){diagnosticTimer=setTimeout(sendDiagnostics,2100-(Date.now()-diagnosticLast));return}
 const started=performance.now(),controller=new AbortController(),timeout=final?0:setTimeout(()=>controller.abort(),3000);diagnosticBusy=true;diagnosticLast=Date.now();
 try{await fetch('/api/rooms/'+encodeURIComponent(roomId)+'/diagnostics',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(diagnosticSnapshot()),keepalive:final,signal:controller.signal});diagnosticRtt=Math.round(performance.now()-started)}catch{}finally{if(timeout)clearTimeout(timeout);diagnosticBusy=false}
}
function queueDiagnostics(){if(!diagnosticTimer)diagnosticTimer=setTimeout(sendDiagnostics,180)}
const diagnosticsRender=render;render=function(data){diagnosticsRender(data);let mode='unavailable';if(ready)try{mode=player.getPlayerState()}catch{}const signature=JSON.stringify([data.id,data.is_host,data.playing,activeScreen,ready,mode,!playerNotice.hidden]);if(diagnosticRoom!==data.id||signature!==diagnosticSignature){diagnosticRoom=data.id;diagnosticSignature=signature;queueDiagnostics()}};
setInterval(()=>{if(!document.hidden)queueDiagnostics()},15000);
for(const event of ['online','offline','resize','pageshow'])window.addEventListener(event,queueDiagnostics,{passive:true});
document.addEventListener('visibilitychange',()=>sendDiagnostics(true));window.addEventListener('pagehide',()=>sendDiagnostics(true));
$('message').addEventListener('input',queueDiagnostics);$('message').addEventListener('focus',queueDiagnostics);$('message').addEventListener('blur',queueDiagnostics);
let diagnosticLayoutSignature='';
new MutationObserver(()=>{const signature=JSON.stringify([document.body.dataset.screen,document.body.classList.contains('keyboard-open'),document.body.classList.contains('solace-fullscreen')]);if(signature!==diagnosticLayoutSignature){diagnosticLayoutSignature=signature;queueDiagnostics()}}).observe(document.body,{attributes:true,attributeFilter:['data-screen','class']});
