const YOUTUBE_HOSTS = new Set(['youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com']);
function isYoutubeUrl(value) {
  try { const url = new URL(value); return url.protocol === 'https:' && YOUTUBE_HOSTS.has(url.hostname); } catch { return false; }
}
function parseVideo(value) {
  try {
    const url = new URL(value);
    if (!isYoutubeUrl(value)) return null;
    const id = url.pathname === '/watch' ? url.searchParams.get('v') : /^\/(shorts|live)\//.test(url.pathname) ? url.pathname.split('/')[2] : null;
    return id && /^[A-Za-z0-9_-]{11}$/.test(id) ? id : null;
  } catch { return null; }
}
const OBSERVER_SCRIPT = `(() => {
  if (!['youtube.com','www.youtube.com','m.youtube.com','music.youtube.com'].includes(location.hostname)) return;
  if (window.__afterglowObserver) return;
  window.__afterglowObserver = true;
  const send = () => {
    const video = document.querySelector('video');
    if (!video || !window.ReactNativeWebView) return;
    const ad = Boolean(document.querySelector('.ad-showing, .ad-interrupting, .ytp-ad-player-overlay'));
    window.ReactNativeWebView.postMessage(JSON.stringify({type:'playback',url:location.href,title:document.title.replace(/ - YouTube$/, '').slice(0,150),position:video.currentTime,playing:!video.paused&&!video.ended,ended:video.ended,ready:video.readyState>=2,ad,blocked:window.__afterglowBlocked===true,live:!Number.isFinite(video.duration)}));
  };
  setInterval(send, 1000);
  send();
})(); true;`;
function buildApplyScript(position, playing) {
  if (!Number.isFinite(position) || position < 0) throw new Error('Invalid playback position');
  return `(() => {
    if (!['youtube.com','www.youtube.com','m.youtube.com','music.youtube.com'].includes(location.hostname)) return;
    if (document.querySelector('.ad-showing, .ad-interrupting, .ytp-ad-player-overlay')) return;
    const video=document.querySelector('video');
    if (!video || video.readyState<2) return;
    if (Number.isFinite(video.duration) && Math.abs(video.currentTime-${position})>3) video.currentTime=Math.min(${position},Math.max(0,video.duration-.1));
    if (${Boolean(playing)}) {
      if(video.paused) {const promise=video.play();if(promise)promise.then(()=>window.__afterglowBlocked=false).catch(()=>window.__afterglowBlocked=true);}
    } else if (!video.paused) video.pause();
  })(); true;`;
}
function buildVideoLayoutScript(enabled) {
  return `(() => {
    if (!['youtube.com','www.youtube.com','m.youtube.com','music.youtube.com'].includes(location.hostname)) return;
    const existing=document.getElementById('afterglow-video-layout');
    if (!${Boolean(enabled)}) {
      if(existing)existing.remove();
      document.querySelectorAll('[data-afterglow-player],[data-afterglow-ancestor]').forEach(node=>{node.removeAttribute('data-afterglow-player');node.removeAttribute('data-afterglow-ancestor');});
      return;
    }
    const video=document.querySelector('video');
    if(!video)return;
    const player=video.closest('#movie_player, .html5-video-player, #player-container-id, #player')||video.parentElement;
    if(!player)return;
    if(existing&&player.hasAttribute('data-afterglow-player'))return;
    document.querySelectorAll('[data-afterglow-player],[data-afterglow-ancestor]').forEach(node=>{node.removeAttribute('data-afterglow-player');node.removeAttribute('data-afterglow-ancestor');});
    player.setAttribute('data-afterglow-player','');
    for(let parent=player.parentElement;parent;parent=parent.parentElement)parent.setAttribute('data-afterglow-ancestor','');
    const style=existing||document.createElement('style');style.id='afterglow-video-layout';
    style.textContent='html,body{margin:0!important;width:100%!important;height:100%!important;overflow:hidden!important;background:#000!important}body *{visibility:hidden!important}[data-afterglow-ancestor]{transform:none!important;filter:none!important;contain:none!important;overflow:visible!important}[data-afterglow-player],[data-afterglow-player] *{visibility:visible!important}[data-afterglow-player]{position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;max-width:none!important;max-height:none!important;margin:0!important;z-index:2147483646!important;background:#000!important;overflow:hidden!important}[data-afterglow-player] video{width:100%!important;height:100%!important;max-height:100%!important;object-fit:contain!important;inset:0!important}[data-afterglow-player] .ytp-share-button,[data-afterglow-player] .ytp-share-button-visible,[data-afterglow-player] .ytp-volume-panel,[data-afterglow-player] .ytp-mute-button,[data-afterglow-player] .ytp-settings-button,[data-afterglow-player] .ytp-settings-menu,[data-afterglow-player] .ytp-youtube-button,[data-afterglow-player] .ytp-watermark{display:none!important;visibility:hidden!important;pointer-events:none!important}';
    if(!existing)document.head.appendChild(style);
  })();true;`;
}
module.exports = {isYoutubeUrl,parseVideo,OBSERVER_SCRIPT,buildApplyScript,buildVideoLayoutScript};

const PICKER_SCRIPT=`(()=>{if(!['youtube.com','www.youtube.com','m.youtube.com'].includes(location.hostname)||window.__afterglowPicker)return;window.__afterglowPicker=true;document.addEventListener('click',event=>{const anchor=event.target.closest&&event.target.closest('a[href]');if(!anchor)return;try{const url=new URL(anchor.href,location.href);if(!['youtube.com','www.youtube.com','m.youtube.com'].includes(url.hostname))return;const id=url.pathname==='/watch'?url.searchParams.get('v'):/^\\/(shorts|live)\\//.test(url.pathname)?url.pathname.split('/')[2]:null;if(!id||!/^[A-Za-z0-9_-]{11}$/.test(id))return;event.preventDefault();event.stopImmediatePropagation();window.ReactNativeWebView.postMessage(JSON.stringify({type:'select-video',url:url.href,title:(anchor.title||anchor.getAttribute('aria-label')||anchor.textContent||'YouTube video').trim().slice(0,150)}))}catch{}},true)})();true;`;
module.exports.PICKER_SCRIPT=PICKER_SCRIPT;
