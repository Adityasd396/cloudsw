(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.SolaceTransport=factory()})(typeof globalThis!=='undefined'?globalThis:this,function(){
 let serial=0;
 function mutationId(){return typeof crypto!=='undefined'&&crypto.randomUUID?crypto.randomUUID():'s-'+Date.now().toString(36)+'-'+(++serial).toString(36)+'-'+Math.random().toString(36).slice(2)}
 async function requestJson(fetcher,path,{data,timeoutMs=10000,maxAttempts=data?2:1,requestId=data?mutationId():null}={}){
  let last;const body=data?JSON.stringify(data):undefined;
  for(let attempt=0;attempt<maxAttempts;attempt++){
   const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeoutMs);
   try{
    const response=await fetcher(path,{method:data?'POST':'GET',credentials:'include',cache:'no-store',headers:data?{'Content-Type':'application/json','X-Request-ID':requestId}:{},body,signal:controller.signal});
    let result;try{result=await response.json()}catch{const error=Error('The server returned an incomplete response.');error.status=502;throw error}
    if(!response.ok){const error=Error(result.error||'Request failed.');error.status=response.status;error.code=result.code;throw error}
    return result;
   }catch(error){last=error;const retry=error.name==='AbortError'||error instanceof TypeError||[502,503,504].includes(error.status);if(!retry||attempt+1===maxAttempts)break}
   finally{clearTimeout(timer)}
   await new Promise(resolve=>setTimeout(resolve,250+Math.random()*200));
  }
  if(last.name==='AbortError'){const error=Error('Connection timed out. Your draft is safe.');error.code='timeout';throw error}
  throw last;
 }
 function pollDelay({playing=false,failures=0,hidden=false}={}){return hidden?20000:failures?Math.min(15000,1000*2**Math.min(4,failures-1)):playing?500:750}
 return {requestJson,mutationId,pollDelay};
});
