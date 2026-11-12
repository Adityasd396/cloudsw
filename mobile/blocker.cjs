const DOMAINS=['doubleclick.net','googlesyndication.com','googleadservices.com','googletagservices.com','adservice.google.com','google-analytics.com'];
function shouldBlock(value){try{const url=new URL(value);if(!['http:','https:'].includes(url.protocol))return false;const host=url.hostname.toLowerCase();if(DOMAINS.some(domain=>host===domain||host.endsWith('.'+domain)))return true;return /(^|\.)youtube\.com$/.test(host)&&(/^\/pagead\//.test(url.pathname)||/^\/api\/stats\/ads(?:\/|$)/.test(url.pathname))}catch{return false}}
function appleRules(){return [...DOMAINS.map(domain=>({trigger:{'url-filter':'^https?://([^/]+\\.)?'+domain.replace(/\./g,'\\.')+'/'},action:{type:'block'}})),{trigger:{'url-filter':'^https?://([^/]+\\.)?youtube\\.com/(pagead/|api/stats/ads([/?]|$))'},action:{type:'block'}}]}
const BLOCKER_SCRIPT=`(() => {
 if(!['youtube.com','www.youtube.com','m.youtube.com','music.youtube.com'].includes(location.hostname)||window.__afterglowAdBlock)return;
 window.__afterglowAdBlock=true;
 const domains=${JSON.stringify(DOMAINS)};
 const blocked=value=>{try{const url=new URL(String(value),location.href);if(!['http:','https:'].includes(url.protocol))return false;return domains.some(domain=>url.hostname===domain||url.hostname.endsWith('.'+domain))||(/(^|\\.)youtube\\.com$/.test(url.hostname)&&(/^\\/pagead\\//.test(url.pathname)||/^\\/api\\/stats\\/ads(?:\\/|$)/.test(url.pathname)))}catch{return false}};
 const cleanPlayer=response=>{if(!response||typeof response!=='object')return response;for(const key of ['adPlacements','playerAds','adSlots']){if(Object.prototype.hasOwnProperty.call(response,key))delete response[key]}return response};
 if(window.fetch){const original=window.fetch;window.fetch=async function(input,init){const url=typeof input==='string'?input:input&&input.url||String(input);if(blocked(url))return new Response(null,{status:204});const response=await original.call(this,input,init);if(/\\/youtubei\\/v1\\/player(?:[/?]|$)/.test(url)&&response.ok){try{const data=await response.clone().json();if(data&&typeof data==='object'&&!Array.isArray(data)){cleanPlayer(data);const headers=new Headers(response.headers);headers.delete('content-length');headers.delete('content-encoding');return new Response(JSON.stringify(data),{status:response.status,statusText:response.statusText,headers})}}catch{}}return response}}
 const apply=()=>{
  if(window.ytInitialPlayerResponse)cleanPlayer(window.ytInitialPlayerResponse);
  if(!document.head)return;
  if(!document.getElementById('afterglow-ad-filter')){const style=document.createElement('style');style.id='afterglow-ad-filter';style.textContent='ytd-ad-slot-renderer,ytm-ad-slot-renderer,ytd-display-ad-renderer,ytd-promoted-sparkles-web-renderer,ytm-promoted-sparkles-web-renderer,ytd-in-feed-ad-layout-renderer,ytm-in-feed-ad-layout-renderer,#masthead-ad{display:none!important}';document.head.appendChild(style)}
  const skip=document.querySelector('.ytp-ad-skip-button,.ytp-ad-skip-button-modern,.ytp-skip-ad-button,.ytm-ad-skip-button');
  if(skip&&skip.getClientRects().length&&!skip.disabled)skip.click();
 };
 apply();setInterval(apply,700);
})();true;`;
module.exports={DOMAINS,shouldBlock,appleRules,BLOCKER_SCRIPT};
