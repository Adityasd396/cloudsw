// One visible task screen at a time. The mounted player keeps its room session.
document.body.classList.add('solace-v2');
let activeScreen='watch',screenReturnFocus=null;
const screenViews=new Map(),shell=document.querySelector('.shell');
function screen(name,title){const view=element('section','task-screen');view.hidden=true;view.dataset.screen=name;view.setAttribute('aria-label',title);const top=element('div','task-top'),back=element('button','screen-back','←');back.type='button';back.setAttribute('aria-label','Back to watch');back.onclick=()=>showScreen('watch');const heading=element('h1','',title);heading.tabIndex=-1;top.append(back,heading);view.append(top);document.body.append(view);screenViews.set(name,view);return view}
function showScreen(name){
 if(name!=='watch'&&!state)return;
 exitSolaceFullscreen();
 if(activeScreen==='watch'&&name!=='watch')screenReturnFocus=document.activeElement;
 for(const [key,view]of screenViews)view.hidden=key!==name;
 picker.hidden=name!=='search';
 if(activeScreen==='game'&&name!=='game')gameFrame.removeAttribute('src');
 activeScreen=name;document.body.dataset.screen=name;shell.inert=name!=='watch';shell.setAttribute('aria-hidden',String(name!=='watch'));
 for(const button of navigation.querySelectorAll('button'))button.setAttribute('aria-current',button.dataset.target===name?'page':'false');
 if(name==='watch'){screenReturnFocus?.focus?.();screenReturnFocus=null}else screenViews.get(name)?.querySelector('h1')?.focus();
 if(name==='queue')paintQueueSummary();
}
// Search and queue are separate full-page views.
const searchTop=picker.querySelector('.selection-bar');searchTop.classList.add('task-top');picker.classList.add('task-screen');picker.dataset.screen='search';picker.setAttribute('aria-label','Search videos');$('closeSelection').textContent='←';$('closeSelection').setAttribute('aria-label','Back to watch');$('closeSelection').onclick=()=>showScreen('watch');screenViews.set('search',picker);
const queueView=screen('queue','Your queue'),nowPlaying=element('div','now-playing'),nextHeading=element('h2','screen-section-title','Up next');queueView.append(nowPlaying,nextHeading,pickerQueue);
const previousOpenSelection=openVideoSelection;openVideoSelection=function(mode='add'){showScreen('search');previousOpenSelection(mode);$('selectionTitle').setAttribute('role','heading');$('selectionTitle').setAttribute('aria-level','1');$('selectionTitle').textContent=mode==='watch'?'Choose your first video':'Find a video'};
new MutationObserver(()=>{if(picker.hidden&&activeScreen==='search')showScreen('watch')}).observe(picker,{attributes:true,attributeFilter:['hidden']});
function paintQueueSummary(){if(!state)return;nowPlaying.replaceChildren(element('span','section-kicker','Playing now'),element('strong','',ready?player.getVideoData()?.title||'YouTube video':'YouTube video'));nextHeading.textContent='Up next · '+state.queue.length;}
const gamesView=screen('games','A little play'),gamesGrid=element('div','game-cards');gamesView.append(gamesGrid);
const gameView=screen('game','Play together'),gameFrame=element('iframe','game-screen-frame');gameFrame.title='Room game';gameView.append(gameFrame);gameView.querySelector('button').onclick=()=>showScreen('games');gameView.querySelector('button').setAttribute('aria-label','Back to games');
for(const [title,detail,path,art]of [['Love hoops','A little basketball, first to five','game.html','🏀'],['Tic-tac-toe','Three in a row, together','tictactoe.html','✧']]){const card=element('button','game-card');card.append(element('span','game-art',art),element('strong','',title),element('small','',detail));card.onclick=()=>{showScreen('game');gameFrame.src='/static/'+path+'?room='+encodeURIComponent(roomId)+'&v='+encodeURIComponent(state?.release_version||'development')};gamesGrid.append(card)}
gameButton.onclick=()=>showScreen('games');
const roomView=screen('room','Your room'),codeCard=element('div','code-card'),roomPeople=element('div','room-people'),roomActionsV2=element('div','room-detail-actions');
const codeLabel=element('span','section-kicker','Room code'),roomCodeV2=element('strong'),copyCode=element('button','subtle','Copy code'),shareV2=element('button','primary','Share invitation'),leaveV2=element('button','leave-action','Leave room'),claimV2=element('button','subtle','Become host');claimV2.hidden=true;claimV2.onclick=()=>action({action:'claim_host'});
copyCode.onclick=()=>visibleCode.click();shareV2.onclick=shareRoom;leaveV2.onclick=()=>leaveButton.click();codeCard.append(codeLabel,roomCodeV2,copyCode);roomActionsV2.append(shareV2,claimV2,leaveV2);roomView.append(codeCard,element('h2','screen-section-title','Together here'),roomPeople,roomActionsV2);
const watchHeader=element('div','watch-header'),watchWordmark=element('span','watch-wordmark','solace'),statusPill=element('span','playback-status','Connecting'),roomShortcut=element('button','room-shortcut');roomShortcut.onclick=()=>showScreen('room');statusPill.setAttribute('role','status');watchHeader.append(watchWordmark,statusPill,roomShortcut);videoStage.before(watchHeader);
const navigation=element('nav','bottom-nav');navigation.setAttribute('aria-label','Room navigation');for(const [target,icon,label]of [['watch','▷','Watch'],['search','＋','Add video'],['queue','☷','Queue'],['games','✧','Games'],['room','♡','Room']]){const button=element('button');button.type='button';button.dataset.target=target;button.append(element('span','nav-icon',icon),element('span','',label));button.onclick=()=>target==='search'?openVideoSelection():showScreen(target);button.setAttribute('aria-current',target==='watch'?'page':'false');navigation.append(button)}document.querySelector('.watch').append(navigation);
let roomReceivedAt=performance.now();
const oldRenderV2=render;render=function(data){if(state?.storage_generation&&data.storage_generation&&state.storage_generation!==data.storage_generation){loveRoom=null;loveCursor=null;experienceRoom=null;experienceCursor=null;lastReactionMessage=null;pageRecovery.begin()}oldRenderV2(data);document.querySelector('.chat').before(document.querySelector('.joined-names'));roomReceivedAt=performance.now();roomCodeV2.textContent=data.id;claimV2.hidden=data.is_host||!data.can_claim_host;roomShortcut.textContent=data.id+' · '+data.members.length+' here';roomShortcut.setAttribute('aria-label','Room '+data.id+' details');
 if(activeScreen==='queue')paintQueueSummary();
 if(activeScreen==='room'){roomPeople.replaceChildren(...(data.participants||data.members).map(person=>{const item=element('button','person-row'),dot=element('i','activity-dot '+person.status);item.append(dot,element('span','',person.name+(person.is_host?' 👑':'')),element('small','',person.status));item.disabled=!data.is_host||person.is_host||!person.active;item.setAttribute('aria-label',person.name+', '+person.status+(data.is_host&&!person.is_host&&person.active?', make host':''));item.onclick=()=>action({action:'transfer_host',member_id:person.member_id});return item}))}
 const rows=$('messages').querySelectorAll('.chat-message');rows.forEach((row,index)=>{const message=state.messages[index],prior=state.messages[index-1];row.classList.toggle('message-grouped',!!prior&&prior.sender_id===message?.sender_id&&message.created-prior.created<180&&!message.reply);const content=row.querySelector('div:not(.mini-avatar)'),time=content?.querySelector(':scope > time');if(time&&content.lastElementChild!==time)content.append(time)});
 const toggle=$('toggle');toggle.textContent=data.playing?'Ⅱ':'▶';toggle.setAttribute('aria-label',data.playing?'Pause':'Play');toggle.title=data.playing?'Pause':'Play';
};
for(const [index,label]of [[0,'Back 10 seconds'],[1,'Forward 10 seconds']]){const button=controls.children[index];button.setAttribute('aria-label',label);button.title=label}
// The manual ad report belongs with room actions rather than primary playback.
reportAdButton.remove();roomActionsV2.prepend(reportAdButton);
function playbackStatus(){if(!state)return;let text='Connecting',kind='loading';if(pollFailures||Date.now()-lastRoomContact>15000||pageRecovery.recovering){text='Reconnecting';kind='waiting'}else if(!playerNotice.hidden){text='Tap video or retry';kind='waiting'}else if(ready){let mode;try{mode=player.getPlayerState()}catch{}text=mode===3?'Buffering':state.playing?'Playing together':'Paused';kind=mode===3?'waiting':state.playing?'playing':'paused'}if(statusPill.textContent!==text)statusPill.textContent=text;statusPill.dataset.state=kind}
let telemetryAt=0;setInterval(()=>{playbackStatus();if(!ready||!state||document.hidden||!pageRecovery.canPublish()||Date.now()<applyingUntil||Date.now()-telemetryAt<30000)return;const mode=player.getPlayerState();if(![1,2].includes(mode)||state.host_ad)return;telemetryAt=Date.now();const expected=state.position+(state.playing?Math.max(0,state.server_time-state.updated)+(performance.now()-roomReceivedAt)/1000:0);api('/api/rooms/'+roomId+'/telemetry',{name:'playback_drift_ms',value:Math.min(600000,Math.abs(player.getCurrentTime()-expected)*1000)}).catch(()=>{})},1000);
window.addEventListener('popstate',event=>{if(activeScreen==='watch')return;event.stopImmediatePropagation();showScreen(activeScreen==='game'?'games':'watch');history.pushState({solaceRoom:roomId},'',location.href)},true);
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&activeScreen!=='watch'){event.preventDefault();showScreen(activeScreen==='game'?'games':'watch')}});
// Restore keyboard focus to the screen that opened a panel; love dialogs remain unchanged.
document.body.dataset.screen='watch';

const newMessagesButton=element('button','new-messages','New messages ↓');newMessagesButton.hidden=true;document.querySelector('.chat').append(newMessagesButton);window.SolaceChat.setButton(newMessagesButton);

const reconnectButton=element('button','reconnect-button','↻');reconnectButton.type='button';reconnectButton.hidden=true;reconnectButton.setAttribute('aria-label','Reconnect room');watchHeader.insertBefore(reconnectButton,roomShortcut);reconnectButton.onclick=async()=>{if(!state)return;const epoch=pageRecovery.begin();try{const fresh=await api('/api/rooms/'+roomId);render(fresh);synchronize(true);pageRecovery.complete(epoch);nextRoomPoll=0}catch{toast('Still reconnecting. Your draft is safe.')}};
const originalStatus=playbackStatus;playbackStatus=function(){originalStatus();reconnectButton.hidden=!(pollFailures||pageRecovery.recovering||Date.now()-lastRoomContact>15000)};
// Recovery stays available in Room details after removing the watch header.
roomActionsV2.append(statusPill,reconnectButton);

const entryBack=element('button','entry-back','← Back');entryBack.type='button';entryBack.onclick=()=>location.assign('/');$('setup').prepend(entryBack);

document.addEventListener('keydown',event=>{if(event.key!=='Tab'||activeScreen==='watch'||document.querySelector('dialog[open]'))return;const view=screenViews.get(activeScreen);const items=[...view.querySelectorAll('button:not(:disabled),input,a[href],[tabindex="0"]')].filter(node=>node.getClientRects().length);if(!items.length)return;const first=items[0],last=items.at(-1);if(event.shiftKey&&(document.activeElement===first||!view.contains(document.activeElement))){event.preventDefault();last.focus()}else if(!event.shiftKey&&(document.activeElement===last||!view.contains(document.activeElement))){event.preventDefault();first.focus()}});

pageRecovery.onRecovered=()=>{if(state&&roomId)api('/api/rooms/'+roomId+'/telemetry',{name:'reconnect',value:1}).catch(()=>{})};
