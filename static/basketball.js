const room=new URLSearchParams(location.search).get('room'),endpoint='/api/rooms/'+encodeURIComponent(room)+'/basketball',$=id=>document.getElementById(id);
let game=null,busy=false,polling=false,ended=false,lastShot=null,lastCheer=null,goalTimer,cheerTimer,confettiTimer,flight=null;
let visualTarget=.5,visualTargetUntil=0;
let aim=.5,power=0,charging=false,lockedAim=.5,holdStart=0,engaged=false,lastLive=0,liveBusy=false,liveAbort=null,liveQueued=null;
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
$('otherGame').href='/static/ludo.html?room='+encodeURIComponent(room)+'&v='+encodeURIComponent(document.querySelector('meta[name=solace-release]')?.content||'development');$('otherGame').textContent='Ludo ↗';
function canShoot(){return !!game?.you&&Object.keys(game.players).length===2&&game.turn===game.you&&!game.winner&&!busy&&performance.now()>=visualTargetUntil}
function draw(next){
 if(game&&game.storage_generation===next.storage_generation&&next.revision<game.revision)return;
 const initial=!game||game.storage_generation!==next.storage_generation;if(initial){lastShot=null;lastCheer=next.cheer?.id||null;charging=false}game=next;
 if(!initial&&game.shot&&game.shot.id!==lastShot){visualTarget=game.shot.target??.5;visualTargetUntil=performance.now()+(reduced?100:1300)}
 if(charging&&!canShoot()){charging=false;power=0}
 $('scores').replaceChildren(...['X','O'].map(role=>{const node=document.createElement('div');node.className='score'+(game.turn===role?' turn':'');const name=document.createElement('span');name.textContent=(role==='X'?'🐻 ':'🐰 ')+(game.players[role]||'Waiting for you');const score=document.createElement('b');score.textContent=game.scores[role];const stat=document.createElement('small');stat.textContent=(game.streaks?.[role]||0)+' streak · '+(game.attempts?.[role]||0)+' shots';node.append(name,score,stat);return node}));
 const ready=Object.keys(game.players).length===2;$('status').textContent=game.winner?(game.winner==='together'?'Together':game.players[game.winner])+' wins ♡':!ready?'Waiting for partner':game.you===game.turn?'Your turn':game.players[game.turn]+'’s shot';
 $('join').hidden=!!game.you||ready;$('shoot').hidden=!game.you||!!game.winner;$('shoot').disabled=!canShoot();$('shoot').textContent=charging?'Release for love ♡':'Hold to shoot ♡';$('reset').hidden=!game.winner||!game.you;
 const challenge=game.challenge||{target:.5,power:.62,radius:.13};$('aimZone').style.left=(challenge.target-challenge.radius)*100+'%';$('aimZone').style.width=challenge.radius*200+'%';$('powerZone').style.left=(challenge.power-.12)*100+'%';$('powerZone').style.width='24%';$('court').style.setProperty('--hoop-x',((performance.now()<visualTargetUntil?visualTarget:challenge.target)-.5)*160+'px');
 const live=game.live,fresh=live&&Date.now()/1000-live.updated<2.5&&live.player===game.turn&&live.phase!=='idle';
 $('court').classList.toggle('is-charging',charging||!!fresh&&live.phase==='charging');
 const actor=charging?game.you:fresh?live.player:null;document.querySelectorAll('.fans span').forEach((node,index)=>node.classList.toggle('getting-ready',actor===(index===0?'X':'O')));
 $('liveStatus').textContent=fresh&&live.player!==game.you?game.players[live.player]+(live.phase==='charging'?' is holding the ball · '+Math.round(live.power*100)+'% power':' is lining up a shot'):'';
 if(fresh&&live.player!==game.you){$('needle').style.left=live.aim*100+'%';$('powerFill').style.width=live.power*100+'%';preview(live.aim)}
 else if(!charging)$('powerFill').style.width='0%';
 if(game.shot&&game.shot.id!==lastShot){lastShot=game.shot.id;if(!initial)animateShot(game.shot)}
 if(game.cheer&&game.cheer.id!==lastCheer){lastCheer=game.cheer.id;if(!initial&&Date.now()/1000-game.cheer.created<8)showCheer(game.cheer.emoji+' '+game.players[game.cheer.player]+' is cheering for you')}
 document.querySelectorAll('[data-cheer]').forEach(button=>button.disabled=!game.you||busy);
}
function preview(value){$('aimPath').setAttribute('d','M 50 94 Q '+(40+value*20)+' -5 '+(30+value*40)+' 35')}
function showCheer(text){$('cheerBubble').textContent=text;$('cheerBubble').hidden=false;clearTimeout(cheerTimer);cheerTimer=setTimeout(()=>$('cheerBubble').hidden=true,2400)}
function celebrate(){clearTimeout(confettiTimer);$('confetti').replaceChildren();for(let i=0;i<14;i++){const heart=document.createElement('span');heart.textContent=i%2?'♡':'✧';heart.style.setProperty('--x',i*7+'%');heart.style.setProperty('--delay',(i%4)*.08+'s');$('confetti').append(heart)}confettiTimer=setTimeout(()=>$('confetti').replaceChildren(),2300)}
function animateShot(shot){
 flight?.cancel();clearTimeout(goalTimer);$('goal').hidden=true;const ball=$('ball'),court=$('court').getBoundingClientRect(),x=(shot.target-.5)*160+(shot.goal?0:(shot.aim-shot.target)*court.width*.4),net=-court.height*.62;
 if(!reduced)flight=ball.animate([{transform:'translate(0,0) scale(1) rotate(0deg)',offset:0},{transform:'translate('+(x*.45)+'px,'+(-court.height*.83)+'px) scale(.62) rotate(175deg)',offset:.45},{transform:'translate('+(shot.rating==='goal'?x+15:x)+'px,'+(net-12)+'px) scale(.72) rotate(260deg)',offset:.68},{transform:'translate('+x+'px,'+net+'px) scale(.72) rotate(280deg)',offset:.78},{transform:'translate('+(shot.goal?x:x*1.35)+'px,'+(shot.goal?net+65:-20)+'px) scale(.8) rotate(380deg)',offset:.86},{transform:'translate('+x+'px,0px) scale(.95) rotate(410deg)',offset:.92},{transform:'translate('+x+'px,-25px) scale(.95) rotate(440deg)',offset:.96},{transform:'translate('+x+'px,0px) scale(1) rotate(460deg)',opacity:0,offset:1}],{duration:1200,easing:'cubic-bezier(.25,.46,.45,.94)'});
 goalTimer=setTimeout(()=>{if(ended)return;if(shot.goal){window.SolaceHaptics?.pulse('goal');$('goal').textContent=shot.rating==='swish'?"it's a love goal · perfect swish ♡":"it's a love goal · rim kiss ♡";$('goal').hidden=false;celebrate();goalTimer=setTimeout(()=>$('goal').hidden=true,1900)}else showCheer('So close ♡')},reduced?0:850);
}
async function update(data){if(ended||busy||(!data&&polling))return;if(data)busy=true;else polling=true;if(game)draw(game);const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);try{const response=await fetch(endpoint,{method:data?'POST':'GET',credentials:'include',cache:'no-store',headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined,signal:controller.signal});const next=await response.json();if(!response.ok){if(response.status===404)ended=true;throw Error(next.error||'Try again')}if(!ended){$('error').textContent='';draw(next);if(data)window.SolaceHaptics?.pulse('game')}}catch(error){if(!ended)$('error').textContent=error.name==='AbortError'?'Reconnecting…':error.message}finally{clearTimeout(timer);if(data)busy=false;else polling=false;if(game&&!ended)draw(game)}}
async function sendLive(phase){if(!game?.you||game.turn!==game.you||ended)return;if(liveBusy){liveQueued=phase;return}lastLive=performance.now();liveBusy=true;liveAbort=new AbortController();const timeout=setTimeout(()=>liveAbort?.abort(),1500);try{await fetch(endpoint,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'aim',revision:game.revision,phase,aim:charging?lockedAim:aim,power}),signal:liveAbort.signal})}catch{}finally{clearTimeout(timeout);liveBusy=false;if(liveQueued&&!ended){const next=liveQueued;liveQueued=null;sendLive(next)}}}
function begin(){if(!canShoot()||charging)return;lockedAim=aim;power=0;holdStart=performance.now();charging=true;engaged=true;sendLive('charging');$('shoot').textContent='Release for love ♡'}
function release(cancel=false){if(!charging)return;charging=false;engaged=false;if(cancel){power=0;sendLive('idle');return}const shot={action:'shoot',aim:lockedAim,power,revision:game.revision};update(shot);power=0}
$('join').onclick=()=>update({action:'join'});$('reset').onclick=()=>update({action:'reset',revision:game.revision});
$('shoot').addEventListener('pointerdown',event=>{if(event.button!==0&&event.pointerType==='mouse')return;event.preventDefault();try{$('shoot').setPointerCapture(event.pointerId)}catch{}begin()});
$('shoot').addEventListener('pointerup',()=>release());$('shoot').addEventListener('pointercancel',()=>release(true));$('shoot').addEventListener('pointerenter',()=>engaged=true);$('shoot').addEventListener('pointerleave',()=>{if(!charging)engaged=false});
$('shoot').onclick=event=>{if(event.detail===0){if(charging)release();else begin()}};
document.addEventListener('keydown',event=>{if(event.code==='Space'&&!event.repeat&&!event.target.matches?.('input,a')){event.preventDefault();begin()}});document.addEventListener('keyup',event=>{if(event.code==='Space'){event.preventDefault();release()}});
document.querySelectorAll('[data-cheer]').forEach(button=>button.onclick=()=>update({action:'cheer',emoji:button.dataset.cheer}));
function tick(now){if(ended)return;if(!document.hidden&&canShoot()){
 if(charging){power=Math.min(1,(now-holdStart)/(game.difficulty==='challenging'?900:1400));$('powerFill').style.width=power*100+'%';$('needle').style.left=lockedAim*100+'%';if(now-holdStart>=1600)release()}
 else{const period=game.difficulty==='challenging'?1400:2200;aim=1-Math.abs((now%period)/(period/2)-1);$('needle').style.left=aim*100+'%'}
 preview(charging?lockedAim:aim);if((charging||engaged)&&now-lastLive>280)sendLive(charging?'charging':'aiming')
 }requestAnimationFrame(tick)}
requestAnimationFrame(tick);update();const pollTimer=setInterval(()=>{if(!document.hidden)update()},350);
document.addEventListener('visibilitychange',()=>{if(document.hidden)release(true);else update()});window.addEventListener('pagehide',()=>{ended=true;clearInterval(pollTimer);clearTimeout(goalTimer);clearTimeout(cheerTimer);clearTimeout(confettiTimer);flight?.cancel();liveAbort?.abort()});
