(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.SolaceExperienceModel=factory()})(typeof globalThis!=='undefined'?globalThis:this,function(){
 function playbackLabel({connected=true,offline=false,recovering=false,notice='',ready=false,mode=-1,playing=false,ad=false}){
  if(offline)return 'Offline';if(!connected||recovering)return 'Reconnecting';if(notice==='error')return 'Playback unavailable';if(notice==='blocked')return 'Tap to resume';if(ad)return 'Ad playing';if(!ready)return 'Loading';if(mode===3)return 'Buffering';if(playing&&mode===1)return 'Playing';if(playing&&[0,2].includes(mode))return 'Tap to resume';if(playing)return 'Loading';return 'Paused';
 }
 return {playbackLabel};
});
