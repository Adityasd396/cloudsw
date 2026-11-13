function exitSolaceFullscreen(){document.body.classList.remove('solace-fullscreen');const exit=document.exitFullscreen||document.webkitExitFullscreen;if((document.fullscreenElement||document.webkitFullscreenElement)&&exit)Promise.resolve(exit.call(document)).catch(()=>{});}
async function toggleSolaceFullscreen(surface){
 if(document.body.classList.contains('solace-fullscreen')||document.fullscreenElement||document.webkitFullscreenElement){exitSolaceFullscreen();return}
 document.body.classList.add('solace-fullscreen');
 const request=surface.requestFullscreen||surface.webkitRequestFullscreen;
 // iPhone Safari may lack element fullscreen. The fitted viewport remains usable.
 if(request)try{await request.call(surface)}catch{}
}
document.addEventListener('keydown',event=>{if(event.key==='Escape')exitSolaceFullscreen()});
for(const name of ['fullscreenchange','webkitfullscreenchange'])document.addEventListener(name,()=>{if(!document.fullscreenElement&&!document.webkitFullscreenElement)document.body.classList.remove('solace-fullscreen')});
