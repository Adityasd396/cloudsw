(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.SolaceDirectPlayback=factory()})(typeof globalThis!=='undefined'?globalThis:this,function(){
 class Controller{
  constructor({play,pause,valid=()=>true,notify=()=>{},schedule=(fn,delay)=>setTimeout(fn,delay),cancel=id=>clearTimeout(id),timeoutMs=15000}){Object.assign(this,{start:play,stop:pause,valid,notify,schedule,cancel,timeoutMs});this.epoch=0;this.pending=false;this.blocked=false;this.wanted=false;this.retries=0;this.timer=null;this.timeout=null}
  clear(){this.cancel(this.timer);this.cancel(this.timeout);this.timer=null;this.timeout=null}
  reset(){this.epoch++;this.clear();this.pending=false;this.blocked=false;this.wanted=false;this.retries=0}
  arm(){this.cancel(this.timer);this.timer=null;this.blocked=false;this.retries=0}
  play(){this.wanted=true;if(this.pending||this.timer!==null||this.blocked||!this.valid())return;this.pending=true;const epoch=this.epoch;
   this.timeout=this.schedule(()=>{if(epoch!==this.epoch||!this.pending)return;this.epoch++;this.pending=false;this.blocked=true;this.notify('Tap Play to continue','The stream took too long to start. Tap Play or retry the source.')},this.timeoutMs);
   Promise.resolve().then(()=>{if(epoch===this.epoch&&this.wanted&&this.valid())return this.start()}).then(()=>{if(epoch!==this.epoch)return;this.cancel(this.timeout);this.pending=false;this.retries=0},error=>{if(epoch!==this.epoch)return;this.cancel(this.timeout);this.pending=false;if(!this.wanted||!this.valid())return;
    if(error?.name==='AbortError'&&this.retries<2){const delay=[150,450][this.retries++];this.timer=this.schedule(()=>{this.timer=null;if(epoch===this.epoch&&this.wanted)this.play()},delay);return}
    this.blocked=true;this.notify(error?.name==='NotAllowedError'?'Tap Play to continue':'This stream could not play',error?.name==='NotAllowedError'?'Your browser needs a tap before playing this stream with sound.':'Retry the source or choose another supported video.')
   })
  }
  pause(){this.reset();try{this.stop()}catch{}}
 }
 return {Controller};
});
