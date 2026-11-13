const gameRoom=new URLSearchParams(location.search).get('room'),endpoint='/api/rooms/'+encodeURIComponent(gameRoom)+'/game';
let match=null,busy=false,polling=false,closed=false,sequence=0,applied=0;
const board=document.getElementById('board'),statusLine=document.getElementById('gameStatus'),join=document.getElementById('joinGame'),reset=document.getElementById('resetGame'),errorLine=document.getElementById('gameError');
const cells=Array.from({length:9},(_,cell)=>{const button=document.createElement('button');button.type='button';button.onclick=()=>updateGame({action:'move',cell,revision:match.revision});board.append(button);return button});
function drawGame(game){match=game;document.getElementById('players').textContent='X · '+(game.players.X||'Waiting')+'     O · '+(game.players.O||'Waiting');
 statusLine.textContent=game.winner?(game.winner==='draw'?'A perfect tie. Play again?':game.players[game.winner]+' wins ♡'):Object.keys(game.players).length<2?'Waiting for a second player…':game.you===game.turn?'Your turn · '+game.turn:game.players[game.turn]+'’s turn';
 join.hidden=!!game.you||Object.keys(game.players).length===2;reset.hidden=!game.winner||!game.you;reset.disabled=busy;
 cells.forEach((cell,index)=>{cell.textContent=game.board[index];cell.dataset.mark=game.board[index];cell.setAttribute('aria-label','Square '+(index+1)+': '+(game.board[index]||'empty'));cell.disabled=busy||!!game.winner||game.you!==game.turn||Object.keys(game.players).length<2||!!game.board[index]});
}
async function updateGame(data){if(busy||closed||(!data&&polling))return;if(data){busy=true;if(match)drawGame(match)}else polling=true;const ticket=++sequence;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),12000);
 try{const response=await fetch(endpoint,{method:data?'POST':'GET',credentials:'include',headers:data?{'Content-Type':'application/json'}:{},body:data?JSON.stringify(data):undefined,cache:'no-store',signal:controller.signal});const game=await response.json();if(!response.ok){if(response.status===404){closed=true;statusLine.textContent='This room has ended.'}throw Error(game.error||'Could not update the game.')}if(ticket>=applied){applied=ticket;errorLine.textContent='';match=game}}
 catch(error){errorLine.textContent=error.name==='AbortError'?'Connection timed out. Trying again…':error.message}
 finally{clearTimeout(timeout);if(data)busy=false;else polling=false;if(match&&!closed)drawGame(match)}
}
join.onclick=()=>updateGame({action:'join'});reset.onclick=()=>updateGame({action:'reset',revision:match.revision});
updateGame();const gameTimer=setInterval(()=>{if(!document.hidden)updateGame()},700);window.addEventListener('pagehide',()=>clearInterval(gameTimer));
