function backAction({keyboardHeight,expanded,pickerMode,replyTo,tab,inRoom,entryMode}){
 if(keyboardHeight)return 'keyboard';if(expanded)return 'fullscreen';if(pickerMode)return 'picker';if(replyTo)return 'reply';if(tab!=='chat')return 'chat';if(!inRoom&&entryMode)return 'home';return 'stay';
}
function videoHeight({expanded,width,height,keyboardHeight,platform,ratio}){
 const available=platform==='ios'?height-keyboardHeight:height;
 if(expanded)return Math.max(160,available-70);
 return keyboardHeight?Math.max(90,Math.min(width/ratio,available*.28)):Math.max(120,Math.min(width/ratio,height*.55));
}
function freshAdAlerts(alerts,seen){
 const fresh=(alerts||[]).filter(alert=>!alert.you&&!seen.has(alert.member_id+':'+alert.started));
 fresh.forEach(alert=>seen.add(alert.member_id+':'+alert.started));
 if(seen.size>200){const keep=[...seen].slice(-100);seen.clear();keep.forEach(key=>seen.add(key))}
 return fresh;
}
module.exports={backAction,videoHeight,freshAdAlerts};
