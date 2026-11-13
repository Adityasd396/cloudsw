// Only scroll the chat list: keyboard motion must never focus, seek or pause media.
const chatMessages=$('messages'),chatComposer=$('message');
let chatScrollFrame=0,chatSettleTimers=[];
function showLatestMessage(){
 if(chatScrollFrame)return;
 chatScrollFrame=requestAnimationFrame(()=>{chatScrollFrame=0;if(state)chatMessages.scrollTop=chatMessages.scrollHeight});
}
function settleLatestMessage(){
 chatSettleTimers.forEach(clearTimeout);
 showLatestMessage();
 // Safari and Android can finish keyboard/viewport layout after the focus event.
 chatSettleTimers=[120,300,600].map(delay=>setTimeout(showLatestMessage,delay));
}
new MutationObserver(showLatestMessage).observe(chatMessages,{childList:true,subtree:true,characterData:true});
if(window.ResizeObserver){const chatSizeObserver=new ResizeObserver(showLatestMessage);chatSizeObserver.observe(chatMessages);chatSizeObserver.observe($('chatForm'));chatSizeObserver.observe(typingLine);chatSizeObserver.observe(replyPreview)}
chatComposer.addEventListener('focus',settleLatestMessage);chatComposer.addEventListener('blur',settleLatestMessage);chatComposer.addEventListener('input',showLatestMessage);
window.visualViewport?.addEventListener('resize',settleLatestMessage);window.visualViewport?.addEventListener('scroll',settleLatestMessage);
window.addEventListener('resize',settleLatestMessage);window.addEventListener('pageshow',settleLatestMessage);
window.addEventListener('pagehide',()=>{chatSettleTimers.forEach(clearTimeout);chatSettleTimers=[];if(chatScrollFrame)cancelAnimationFrame(chatScrollFrame);chatScrollFrame=0});
showLatestMessage();
