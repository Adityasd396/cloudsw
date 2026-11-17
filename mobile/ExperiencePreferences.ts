import AsyncStorage from '@react-native-async-storage/async-storage';
let autoFullscreen=true,changed=false,writes=Promise.resolve();
const listeners=new Set<()=>void>();
export const getAutoFullscreen=()=>autoFullscreen;
export function setAutoFullscreen(value:boolean){changed=true;autoFullscreen=value;listeners.forEach(fn=>fn());writes=writes.catch(()=>{}).then(()=>AsyncStorage.setItem('solace-rotation',JSON.stringify(value)))}
export function subscribeRotation(fn:()=>void){listeners.add(fn);return()=>{listeners.delete(fn)}}
AsyncStorage.getItem('solace-rotation').then(value=>{if(!changed&&value!==null){autoFullscreen=value!=='false';listeners.forEach(fn=>fn())}}).catch(()=>{});
