import {useEffect,useRef} from 'react';
export default function ClientDiagnostics({roomId,report,request,foreground}:{roomId:string;report:Record<string,unknown>;request:(path:string,data?:object)=>Promise<any>;foreground:boolean}){
 const latest=useRef(report),busy=useRef(false),last=useRef(0);latest.current=report;
 async function send(){if(busy.current||Date.now()-last.current<2100)return;busy.current=true;last.current=Date.now();try{await request('/api/rooms/'+roomId+'/diagnostics',latest.current)}catch{}finally{busy.current=false}}
 const signature=JSON.stringify([roomId,report.visibility,report.playback,report.keyboard,report.typing,report.fullscreen,report.screen,report.error]);
 useEffect(()=>{send()},[signature]);
 useEffect(()=>{const timer=setInterval(()=>{if(foreground)send()},15000);return()=>clearInterval(timer)},[roomId,foreground]);
 return null;
}
