// Chat-only scrolling: never focus or change playback as a side effect.
const chatMessages=$('messages'),chatComposer=$('message');
chatMessages.tabIndex=0;chatMessages.setAttribute('aria-label','Conversation');
let chatScrollFrame=0,chatSettleTimers=[],chatFollowLatest=true,chatAnchor=null,chatNewButton=null,chatLayoutSettling=false;
function editingChat(){return document.activeElement===chatComposer}
function paintNewMessages(){if(chatNewButton)chatNewButton.hidden=chatFollowLatest||editingChat()}
function beforeChatUpdate(){
 if(chatFollowLatest||editingChat())return;
 const top=chatMessages.getBoundingClientRect().top;
 const row=[...chatMessages.querySelectorAll('.chat-message')].find(node=>node.getBoundingClientRect().bottom>top);
 chatAnchor={id:row?.dataset.messageId,offset:row?row.getBoundingClientRect().top-top:0,scrollTop:chatMessages.scrollTop,height:chatMessages.scrollHeight};
}
function showLatestMessage(force=false){
 if(force===true)chatFollowLatest=true;
 if(chatScrollFrame)return;
 chatScrollFrame=requestAnimationFrame(()=>{chatScrollFrame=0;if(!state)return;
  if(chatFollowLatest||editingChat()){chatFollowLatest=true;chatMessages.scrollTop=chatMessages.scrollHeight}
  else if(chatAnchor){const row=[...chatMessages.querySelectorAll('.chat-message')].find(node=>node.dataset.messageId===chatAnchor.id);if(row)chatMessages.scrollTop+=row.getBoundingClientRect().top-chatMessages.getBoundingClientRect().top-chatAnchor.offset;else chatMessages.scrollTop=Math.max(0,chatAnchor.scrollTop+chatMessages.scrollHeight-chatAnchor.height)}
  chatAnchor=null;paintNewMessages();
 });
}
function settleLatestMessage(){chatLayoutSettling=true;chatSettleTimers.forEach(clearTimeout);showLatestMessage();chatSettleTimers=[120,300,600].map(delay=>setTimeout(()=>{showLatestMessage();if(delay===600)chatLayoutSettling=false},delay))}
chatMessages.addEventListener('scroll',()=>{if(chatScrollFrame||chatAnchor||(chatLayoutSettling&&chatFollowLatest)||editingChat())return;chatFollowLatest=chatMessages.scrollHeight-chatMessages.scrollTop-chatMessages.clientHeight<48;paintNewMessages()},{passive:true});
// A deliberate gesture can still leave the bottom while layout is settling.
for(const name of ['touchstart','wheel','pointerdown','keydown'])chatMessages.addEventListener(name,()=>{chatLayoutSettling=false},{passive:true});
new MutationObserver(()=>showLatestMessage()).observe(chatMessages,{childList:true,subtree:true,characterData:true});
if(window.ResizeObserver){const observer=new ResizeObserver(()=>showLatestMessage());observer.observe(chatMessages);observer.observe($('chatForm'));observer.observe(typingLine);observer.observe(replyPreview)}
chatComposer.addEventListener('focus',()=>{chatFollowLatest=true;settleLatestMessage()});chatComposer.addEventListener('blur',settleLatestMessage);chatComposer.addEventListener('input',()=>showLatestMessage(true));
window.visualViewport?.addEventListener('resize',settleLatestMessage);window.visualViewport?.addEventListener('scroll',settleLatestMessage);window.addEventListener('resize',settleLatestMessage);window.addEventListener('pageshow',settleLatestMessage);
window.addEventListener('pagehide',()=>{chatSettleTimers.forEach(clearTimeout);chatSettleTimers=[];if(chatScrollFrame)cancelAnimationFrame(chatScrollFrame);chatScrollFrame=0});
// A pointer send must not blur the input and dismiss/reopen the phone keyboard.
$('chatForm').addEventListener('pointerdown',event=>{if(editingChat()&&event.target.closest?.('.send'))event.preventDefault()});
window.SolaceChat={beforeUpdate:beforeChatUpdate,layout:showLatestMessage,jump:()=>showLatestMessage(true),setButton(button){chatNewButton=button;button.onclick=()=>showLatestMessage(true);paintNewMessages()}};
showLatestMessage();
