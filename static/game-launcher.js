const gameButton=element('button','subtle','◉ Play together');
gameButton.onclick=()=>{
 const panel=element('dialog','love-overlay'),close=element('button','love-close','Close game'),frame=element('iframe','love-frame');
 close.type='button';frame.title='Two-player tic-tac-toe';frame.src='/static/game.html?room='+encodeURIComponent(roomId);
 close.onclick=()=>panel.remove();panel.addEventListener('cancel',event=>{event.preventDefault();panel.remove()});
 panel.setAttribute('aria-label','Play together');panel.append(close,frame);document.body.append(panel);panel.showModal();close.focus();
};
document.querySelector('.room-add-row').append(gameButton);
