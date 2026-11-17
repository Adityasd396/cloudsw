(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.SolaceHapticCore=factory()})(typeof globalThis!=='undefined'?globalThis:this,function(){
 const defaults=Object.freeze({enabled:true,music:false,bpm:90});
 function preferences(value){value=value&&typeof value==='object'?value:{};return {enabled:typeof value.enabled==='boolean'?value.enabled:defaults.enabled,music:typeof value.music==='boolean'?value.music:defaults.music,bpm:typeof value.bpm==='number'&&Number.isFinite(value.bpm)?Math.max(60,Math.min(160,Math.round(value.bpm))):90}}
 class Controller{
  constructor(emit,now=()=>Date.now()){this.emit=emit;this.now=now;this.settings=preferences();this.foreground=true;this.last=-Infinity;this.lastBeat=-Infinity}
  configure(value){this.settings=preferences(value)}
  pulse(kind){if(!['chat','game','goal','song','beat'].includes(kind)||!this.settings.enabled||!this.foreground||kind==='beat'&&!this.settings.music)return false;const now=this.now();if(now-this.last<100||kind==='beat'&&now-this.lastBeat<450)return false;this.last=now;if(kind==='beat')this.lastBeat=now;try{const promise=this.emit(kind);promise?.catch?.(()=>{})}catch{}return true}
 }
 class BeatClock{
  constructor(){this.key=null;this.last=null;this.bpm=null}
  sample(position,playing,key,bpm){if(!playing||!Number.isFinite(position)||position<0){this.last=null;return false}const beat=Math.floor(position*bpm/60);if(this.key!==key||this.bpm!==bpm||this.last===null){this.key=key;this.bpm=bpm;this.last=beat;return false}const delta=beat-this.last;this.last=beat;return delta===1&&beat%2===0}
 }
 return {defaults,preferences,Controller,BeatClock};
});
