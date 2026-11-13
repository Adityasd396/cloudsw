const DOMAINS=['doubleclick.net','googlesyndication.com','googleadservices.com','googletagservices.com','adservice.google.com','google-analytics.com','imasdk.googleapis.com','ads.youtube.com','adservice.google.co.in','adservice.google.co.uk','amazon-adsystem.com','adnxs.com','adsrvr.org','criteo.com','criteo.net'];
function shouldBlock(value){try{const url=new URL(value);if(!['http:','https:'].includes(url.protocol))return false;const host=url.hostname.toLowerCase();if(DOMAINS.some(domain=>host===domain||host.endsWith('.'+domain)))return true;return /(^|\.)youtube\.com$/.test(host)&&(/^\/pagead\//.test(url.pathname)||/^\/api\/stats\/ads(?:\/|$)/.test(url.pathname))}catch{return false}}
function appleRules(){return [...DOMAINS.map(domain=>({trigger:{'url-filter':'^https?://([^/]+\\.)?'+domain.replace(/\./g,'\\.')+'/'},action:{type:'block'}})),{trigger:{'url-filter':'^https?://([^/]+\\.)?youtube\\.com/(pagead/|api/stats/ads([/?]|$))'},action:{type:'block'}}]}
const BLOCKER_SCRIPT=`(() => {
 if(!['youtube.com','www.youtube.com','m.youtube.com','music.youtube.com'].includes(location.hostname)||window.__afterglowAdBlock)return;
 window.__afterglowAdBlock=true;
 const domains=${JSON.stringify(DOMAINS)};
 const blocked=value=>{try{const url=new URL(String(value),location.href);if(!['http:','https:'].includes(url.protocol))return false;return domains.some(domain=>url.hostname===domain||url.hostname.endsWith('.'+domain))||(/(^|\\.)youtube\\.com$/.test(url.hostname)&&(/^\\/pagead\\//.test(url.pathname)||/^\\/api\\/stats\\/ads(?:\\/|$)/.test(url.pathname)))}catch{return false}};
 const cleanPlayer=response=>{if(!response||typeof response!=='object')return response;for(const key of ['adPlacements','playerAds','adSlots','adBreakHeartbeatParams']){if(Object.prototype.hasOwnProperty.call(response,key))delete response[key]}return response};
 // Clean initial JSON and XHR responses as well as fetch-based player requests.
 const json=window.JSON;
 if(json&&json.parse){const parse=json.parse;json.parse=function(text,reviver){const result=parse.call(this,text,reviver);if(result&&typeof result==='object'){if(result.videoDetails||result.playabilityStatus||result.streamingData)cleanPlayer(result);if(result.playerResponse)cleanPlayer(result.playerResponse)}return result}}
 if(window.XMLHttpRequest){const proto=window.XMLHttpRequest.prototype,open=proto.open;proto.open=function(method,url,...args){this.__solacePlayer=/\\/youtubei\\/v1\\/player(?:[/?]|$)/.test(String(url));return open.call(this,method,url,...args)};
 for(const key of ['response','responseText']){const descriptor=Object.getOwnPropertyDescriptor(proto,key);if(descriptor&&descriptor.get&&descriptor.configurable)try{Object.defineProperty(proto,key,{...descriptor,get(){const value=descriptor.get.call(this);if(!this.__solacePlayer||this.readyState!==4)return value;try{if(value&&typeof value==='object')return cleanPlayer(value);if(typeof value==='string')return JSON.stringify(cleanPlayer(JSON.parse(value)))}catch{}return value}})}catch{}}}
 if(window.fetch){const original=window.fetch;window.fetch=async function(input,init){const url=typeof input==='string'?input:input&&input.url||String(input);if(blocked(url))return new Response(null,{status:204});const response=await original.call(this,input,init);if(/\\/youtubei\\/v1\\/player(?:[/?]|$)/.test(url)&&response.ok){try{const data=await response.clone().json();if(data&&typeof data==='object'&&!Array.isArray(data)){cleanPlayer(data);const headers=new Headers(response.headers);headers.delete('content-length');headers.delete('content-encoding');return new Response(JSON.stringify(data),{status:response.status,statusText:response.statusText,headers})}}catch{}}return response}}
 const apply=()=>{
  if(window.ytInitialPlayerResponse)cleanPlayer(window.ytInitialPlayerResponse);
  if(!document.head)return;
  if(!document.getElementById('afterglow-ad-filter')){const style=document.createElement('style');style.id='afterglow-ad-filter';style.textContent='ytd-ad-slot-renderer,ytm-ad-slot-renderer,ytd-display-ad-renderer,ytd-promoted-sparkles-web-renderer,ytm-promoted-sparkles-web-renderer,ytd-in-feed-ad-layout-renderer,ytm-in-feed-ad-layout-renderer,ytd-companion-slot-renderer,ytm-companion-slot-renderer,ytd-action-companion-ad-renderer,#player-ads,#masthead-ad{display:none!important}';document.head.appendChild(style)}
  const skip=document.querySelector('.ytp-ad-skip-button,.ytp-ad-skip-button-modern,.ytp-skip-ad-button,.ytm-ad-skip-button');
  if(skip&&skip.getClientRects().length&&!skip.disabled)skip.click();
 };
 let scheduled=false;const schedule=()=>{if(scheduled)return;scheduled=true;setTimeout(()=>{scheduled=false;apply()},240)};
 if(window.MutationObserver&&document.documentElement)new window.MutationObserver(schedule).observe(document.documentElement,{childList:true,subtree:true});
 apply();setInterval(apply,500);
})();true;`;
module.exports={DOMAINS,shouldBlock,appleRules,BLOCKER_SCRIPT};
