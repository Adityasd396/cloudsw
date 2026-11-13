'use strict';
const ops=id=>document.getElementById(id),timestamp=value=>value?new Date(value*1000).toLocaleString():'—';
function node(tag,text,cls){const element=document.createElement(tag);element.textContent=String(text);if(cls)element.className=cls;return element}
function tableRows(target,rows){ops(target).replaceChildren(...rows.map(row=>{const tr=document.createElement('tr');for(const value of row)tr.append(node('td',value));return tr}))}
let loading=false;
async function refreshOps(){
 if(loading||document.hidden)return;loading=true;const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),12000);
 try{
  const response=await fetch('/ops/solace/data',{cache:'no-store',credentials:'same-origin',signal:controller.signal});
  if(response.status===401){location.replace('/ops/solace');return}
  if(!response.ok)throw Error('The private panel could not read server status.');
  const data=await response.json(),traffic=data.traffic,average=traffic.requests?traffic.elapsed/traffic.requests*1000:0;
  const cards=[['Server',data.status],['Room DB check',data.db_check_ms+' ms'],['Active rooms',data.rooms],['Active members',data.active_members],['Requests · 5 min',traffic.requests],['Server errors · 5 min',traffic.errors],['Handler time',average.toFixed(1)+' ms'],['Worker CPU average',data.worker_cpu_average_percent+'%'],['Worker uptime',Math.floor(data.worker_uptime_seconds/60)+' min'],['Host load · 1 min',data.host_load_averages?data.host_load_averages[0].toFixed(2):'Unavailable']];
  ops('health').replaceChildren(...cards.map(([label,value])=>{const card=node('div','','metric');card.append(node('strong',value),node('span',label));return card}));
  ops('metricsNote').textContent='Handler timings exclude internet/video latency and telemetry writes. CPU is this worker’s lifetime average, not whole-server utilization. Host load is platform-provided and may include other tenants. Request counts flush about every five seconds. Retention: '+data.retention_days+' days. IP source: '+data.ip_source+'.';
  tableRows('visitors',data.visitors.map(v=>[v.name+' · '+v.id.slice(0,8),v.ip,data.now-v.last>15?'Offline (timeout)':v.last_leave&&v.last_leave>=(v.last_join||0)?'Left room':!v.active?'Inactive':v.last_join?'In room':'Online (site)',timestamp(v.last),timestamp(v.last_join),timestamp(v.last_leave)]));
  ops('matches').replaceChildren(...(data.ip_matches.length?data.ip_matches.map(m=>node('p',m.ip+' · '+m.devices+' devices')):[node('p','No matching IPs recorded.')]));
  ops('backupCount').textContent=data.chat_backup_count+' messages in the private 30-day backup.';
  tableRows('events',data.events.map(e=>[timestamp(e.created),e.name,e.event.replaceAll('_',' '),e.room||'—',e.ip]));ops('opsError').textContent='';
 }catch(error){ops('opsError').textContent=error.name==='AbortError'?'Status request timed out. Retrying…':error.message;const server=ops('health').querySelector('strong');if(server)server.textContent='Unavailable'}finally{clearTimeout(timeout);loading=false}
}
refreshOps();setInterval(refreshOps,10000);
