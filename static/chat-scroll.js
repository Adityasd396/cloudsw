// Follow the newest message after the final bubble/reply layout and keyboard resize.
const chatMessages=$('messages'),chatComposer=$('message');
let chatScrollFrame=0;
function showLatestMessage(){
 if(chatScrollFrame)return;
 chatScrollFrame=requestAnimationFrame(()=>{chatScrollFrame=0;if(state)chatMessages.scrollTop=chatMessages.scrollHeight});
}
new MutationObserver(showLatestMessage).observe(chatMessages,{childList:true,subtree:true,characterData:true});
if(window.ResizeObserver){const chatSizeObserver=new ResizeObserver(showLatestMessage);chatSizeObserver.observe(chatMessages);chatSizeObserver.observe($('chatForm'));chatSizeObserver.observe(typingLine);chatSizeObserver.observe(replyPreview)}
chatComposer.addEventListener('focus',showLatestMessage);chatComposer.addEventListener('input',showLatestMessage);
window.visualViewport?.addEventListener('resize',showLatestMessage);window.visualViewport?.addEventListener('scroll',()=>{if(document.activeElement===chatComposer)showLatestMessage()});
window.addEventListener('resize',showLatestMessage);
showLatestMessage();
