let overlayRoom=null;
const overlayVisibility=new SolaceSession.AutoHideControls(3000);
const touchSurface=element('button','player-touch-surface');touchSurface.type='button';touchSurface.setAttribute('aria-label','Show or hide playback controls');videoStage.append(touchSurface);
function paintControls(visible){visible=picker.hidden&&(window.matchMedia('(orientation: portrait)').matches&&!document.body.classList.contains('solace-fullscreen')||visible);videoStage.classList.toggle('controls-visible',visible);controls.setAttribute('aria-hidden',String(!visible));fullscreen.textContent=document.body.classList.contains('solace-fullscreen')?'⛶ Exit fullscreen':'⛶ Fullscreen'}
function revealControls(){paintControls(overlayVisibility.show())}
touchSurface.onclick=revealControls;
videoStage.addEventListener('pointermove',event=>{if(event.pointerType==='mouse')revealControls()});
videoStage.addEventListener('keydown',revealControls);
controls.addEventListener('pointerdown',()=>{overlayVisibility.focused=false;revealControls()});
controls.addEventListener('focusin',event=>{overlayVisibility.focused=event.target.matches(':focus-visible');revealControls()});
controls.addEventListener('focusout',()=>{overlayVisibility.focused=false;overlayVisibility.show()});
// Let a blocked YouTube player receive the first required media gesture directly.
const overlayRender=render;render=function(data){overlayRender(data);videoStage.classList.toggle('needs-media-gesture',!playerNotice.hidden);paintControls(overlayVisibility.update(!!data.playing));if(overlayRoom!==data.id){overlayRoom=data.id;syncLandscape()}};
setInterval(()=>{if(document.hidden)return;videoStage.classList.toggle('needs-media-gesture',!playerNotice.hidden);paintControls(overlayVisibility.update(!!state?.playing))},250);
let landscapeExpanded=false;
const landscapeQuery=window.matchMedia('(orientation: landscape) and (pointer: coarse)');
function syncLandscape(){
 if(!state)return;
 if(landscapeQuery.matches&&!document.body.classList.contains('solace-fullscreen')){landscapeExpanded=true;document.body.classList.add('solace-fullscreen');revealControls()}
 else if(!landscapeQuery.matches&&landscapeExpanded){landscapeExpanded=false;exitSolaceFullscreen();revealControls()}
 fullscreen.textContent=document.body.classList.contains('solace-fullscreen')?'⛶ Exit fullscreen':'⛶ Fullscreen';
}
landscapeQuery.addEventListener('change',syncLandscape);
const existingFullscreenClick=fullscreen.onclick;fullscreen.onclick=async()=>{landscapeExpanded=false;await existingFullscreenClick();fullscreen.textContent=document.body.classList.contains('solace-fullscreen')?'⛶ Exit fullscreen':'⛶ Fullscreen';revealControls()};
revealControls();

// The picker must never share the playback controls' hit-testing layer.
new MutationObserver(()=>paintControls(overlayVisibility.visible)).observe(picker,{attributes:true,attributeFilter:['hidden']});
window.matchMedia('(orientation: portrait)').addEventListener('change',()=>paintControls(overlayVisibility.show()));
