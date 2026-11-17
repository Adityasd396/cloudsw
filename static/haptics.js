// Shared by the room and isolated games. Never modifies audio or playback.
(function(){
 const KEY='solace-haptics-v1';let saved={};try{saved=JSON.parse(localStorage.getItem(KEY)||'{}')}catch{}
 const durations={chat:5,game:6,goal:10,song:5,beat:4};
 const controller=new SolaceHapticCore.Controller(kind=>{if(window.ReactNativeWebView){window.ReactNativeWebView.postMessage(JSON.stringify({type:'solace-haptic',kind}));return}if(navigator.userActivation?.hasBeenActive===false)return;if(typeof navigator.vibrate==='function')navigator.vibrate(durations[kind])});controller.configure(window.ReactNativeWebView?{}:saved);controller.foreground=!document.hidden;
 window.SolaceHaptics={pulse:kind=>controller.pulse(kind),get:()=>({...controller.settings}),set:value=>{controller.configure(value);try{localStorage.setItem(KEY,JSON.stringify(controller.settings))}catch{}if(!controller.settings.enabled&&navigator.vibrate)try{navigator.vibrate(0)}catch{}window.dispatchEvent(new Event('solace-haptics-change'))}};
 window.addEventListener('storage',event=>{if(event.key===KEY){try{controller.configure(window.ReactNativeWebView?{}:JSON.parse(event.newValue||'{}'))}catch{controller.configure({})}window.dispatchEvent(new Event('solace-haptics-change'))}});
 document.addEventListener('visibilitychange',()=>{controller.foreground=!document.hidden;if(document.hidden&&navigator.vibrate)try{navigator.vibrate(0)}catch{}});window.addEventListener('pagehide',()=>{controller.foreground=false;if(navigator.vibrate)try{navigator.vibrate(0)}catch{}});window.addEventListener('pageshow',()=>controller.foreground=!document.hidden);
})();
