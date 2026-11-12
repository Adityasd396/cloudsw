'use strict';
const film=document.getElementById('loveVideo'),sound=document.getElementById('soundButton');
async function playWithSound(){film.muted=false;if(film.error)film.load();try{await film.play();sound.hidden=true}catch{sound.hidden=false;sound.textContent='Play with sound ♡'}}
sound.addEventListener('click',playWithSound);
function refreshSoundButton(){sound.hidden=!film.paused&&!film.muted&&film.volume>0}
film.addEventListener('volumechange',refreshSoundButton);film.addEventListener('playing',refreshSoundButton);
film.addEventListener('error',()=>{sound.hidden=false;sound.textContent='Video couldn’t load · tap to retry'});
playWithSound();
