'use strict';
const statusNode=document.getElementById('formStatus'),csrfToken=document.querySelector('meta[name=account-csrf]').content;
let identityNavigationPending=false;
function completeIdentity(path,upgraded=false){if(identityNavigationPending)return;identityNavigationPending=true;if(!upgraded)window.ReactNativeWebView?.postMessage(JSON.stringify({type:'account-identity-changed'}));if(window.parent!==window){parent.postMessage({type:upgraded?'solace-identity-upgraded':'solace-identity-changed',path},location.origin);return}window.SolaceNavigation?SolaceNavigation.navigate(path):location.assign(path)}
function tell(text){statusNode.textContent=text}
async function accountRequest(path,data,method='POST'){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
 try{
 const headers={'X-CSRF-Token':csrfToken};if(data&&!(data instanceof FormData))headers['Content-Type']='application/json';
 const response=await fetch(path,{method,headers,signal:controller.signal,body:data?(data instanceof FormData?data:JSON.stringify(data)):undefined,credentials:'same-origin',cache:'no-store'});
 const result=await response.json().catch(()=>({error:'The request could not be completed.'}));if(!response.ok){if(response.status===401&&path.startsWith('/api/me'))completeIdentity('/signin');throw Error(result.error||'The request could not be completed.')}return result;
 }catch(error){if(error.name==='AbortError')throw Error('The connection timed out. Your form is still here; try again.');if(error instanceof TypeError)throw Error('Connection interrupted. Please try again.');throw error}finally{clearTimeout(timer)}
}
function form(id,submit){const target=document.getElementById(id);if(!target)return;target.addEventListener('submit',async event=>{event.preventDefault();const button=target.querySelector('button');if(button.disabled)return;button.disabled=true;tell('');try{await submit(new FormData(target))}catch(error){tell(error.message)}finally{button.disabled=identityNavigationPending||(id==='pictureForm'&&!target.elements.picture.files.length)}})}
form('authForm',async fields=>{const target=document.getElementById('authForm');if(target.dataset.mode==='signin'&&window.SolaceNavigation&&!await SolaceNavigation.confirmSwitch(null))return;const result=await accountRequest('/api/auth/'+target.dataset.mode,Object.fromEntries(fields));completeIdentity(result.next||'/home',target.dataset.mode==='signup')});
form('profileForm',async fields=>{await accountRequest('/api/me/profile',{name:fields.get('name')});localStorage.setItem('afterglow-name',String(fields.get('name')));tell('Name saved.')});
function refreshAvatar(){const preview=document.getElementById('avatarPreview');preview.src='/api/me/avatar?v='+Date.now()}
form('pictureForm',async fields=>{const picture=fields.get('picture');if(picture.size>2*1024*1024)throw Error('The picture must be no larger than 2 MiB.');await accountRequest('/api/me/avatar',fields);refreshAvatar();document.getElementById('removePicture').hidden=false;document.getElementById('pictureForm').reset();document.querySelector('#pictureForm button').disabled=true;tell('Picture updated.')});
function actionButton(id,action){const target=document.getElementById(id);if(target)target.onclick=async()=>{if(target.disabled)return;target.disabled=true;tell('');try{await action()}catch(error){tell(error.message)}finally{target.disabled=identityNavigationPending}}}
actionButton('removePicture',async()=>{await accountRequest('/api/me/avatar',null,'DELETE');document.getElementById('avatarPreview').src='/static/default-avatar.svg';document.getElementById('removePicture').hidden=true;tell('Picture removed.')});
actionButton('verifyEmail',async()=>{const result=await accountRequest('/api/auth/send-verification',{});tell(result.message)});
if(document.getElementById('storageUsage'))accountRequest('/api/me',null,'GET').then(data=>{const s=data.storage;document.getElementById('storageUsage').textContent='Reference '+s.reference+' · Storage: '+(s.used_bytes/1048576).toFixed(2)+' / '+(s.limit_bytes/1048576).toFixed(0)+' MiB.'+(s.full?' Full — delete history or remove a picture to keep recording.':'')}).catch(error=>tell(error.message));
actionButton('signout',async()=>{if(window.SolaceNavigation&&!await SolaceNavigation.confirmSwitch(null))return;await accountRequest('/api/auth/signout',{});completeIdentity('/signin')});
form('deleteAccountForm',async fields=>{if(window.SolaceNavigation&&!await SolaceNavigation.confirmSwitch(null))return;await accountRequest('/api/me/delete-account',{password:fields.get('password')});localStorage.removeItem('afterglow-name');completeIdentity('/welcome')});
const created=document.getElementById('accountCreated');if(created)created.textContent='Joined '+new Date(Number(created.dataset.time)*1000).toLocaleDateString(undefined,{year:'numeric',month:'long',day:'numeric'});
const filters=document.getElementById('historyFilters');let historyPending=false;
function make(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node}
async function loadHistory(){
 if(historyPending)return;historyPending=true;tell('');
 try{const query=new URLSearchParams(Object.fromEntries(new FormData(filters))),data=await accountRequest('/api/me/history?'+query,null,'GET');
  const graph=document.getElementById('activityGraph'),table=document.getElementById('activityTable'),list=document.getElementById('historyList');graph.replaceChildren();table.replaceChildren();list.replaceChildren();
  const maxCount=Math.max(1,...data.days.map(d=>d.sessions)),maxSeconds=Math.max(1,...data.days.map(d=>d.seconds));
  for(const day of data.days){const column=make('div',undefined,'activity-day');column.title=day.date+': '+day.sessions+' sessions, '+(day.seconds/60).toFixed(1)+' minutes';for(const value of [day.sessions/maxCount,day.seconds/maxSeconds]){const bar=make('i');bar.style.height=(value*100)+'%';column.append(bar)}graph.append(column);const row=make('tr');for(const value of [day.date,day.sessions,(day.seconds/60).toFixed(1)])row.append(make('td',value));table.append(row)}
  if(!data.entries.length)list.append(make('p','No viewing sessions in these dates. Your next shared moment can start in a room.','quiet'));
  if(data.truncated)tell('Showing the latest 500 entries. Narrow the date range to see more.');
  for(const entry of data.entries){const article=make('article',undefined,'history-entry');article.append(make('h2',entry.title));article.append(make('p',entry.video,'quiet'));article.append(make('p',new Date(entry.started*1000).toLocaleString(undefined,{timeZone:data.timezone})+' · '+(entry.seconds/60).toFixed(1)+' minutes watched','quiet'));article.append(make('p',entry.people.length?'With '+entry.people.join(', '):'A little time on your own','quiet'));const remove=make('button','Delete entry','secondary');remove.onclick=async()=>{remove.disabled=true;try{await accountRequest('/api/me/history/'+entry.id,null,'DELETE');await loadHistory()}catch(error){tell(error.message);remove.disabled=false}};article.append(remove);list.append(article)}
 }catch(error){tell(error.message)}finally{historyPending=false}
}
if(filters){const iso=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'),end=new Date(),start=new Date();start.setDate(start.getDate()-29);filters.elements.start.value=iso(start);filters.elements.end.value=iso(end);filters.elements.timezone.value=Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC';form('historyFilters',loadHistory);loadHistory();actionButton('clearHistory',async()=>{await accountRequest('/api/me/history',null,'DELETE');await loadHistory();tell('History cleared.')})}
if(document.getElementById('sharingForm')){accountRequest('/api/me/privacy',null,'GET').then(d=>{for(const k of ['share_presence','share_stats','share_avatar','share_read'])document.getElementById('sharingForm').elements[k].checked=d[k]}).catch(e=>tell(e.message));form('sharingForm',async()=>{const f=document.getElementById('sharingForm');await accountRequest('/api/me/privacy',Object.fromEntries(['share_presence','share_stats','share_avatar','share_read'].map(k=>[k,f.elements[k].checked])));tell('Privacy saved.')})}
window.addEventListener('pageshow',event=>{if(event.persisted)location.reload()});

const pictureInput=document.querySelector('#pictureForm input[type=file]');if(pictureInput)pictureInput.addEventListener('change',()=>{document.querySelector('#pictureForm button').disabled=!pictureInput.files.length});
