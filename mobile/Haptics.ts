import AsyncStorage from '@react-native-async-storage/async-storage';
import {AppState,Platform} from 'react-native';
import * as ExpoHaptics from 'expo-haptics';
const {Controller,preferences,BeatClock}=require('./haptic-core.cjs');
export type HapticPreferences={enabled:boolean;music:boolean;bpm:number};
export type HapticKind='chat'|'game'|'goal'|'song'|'beat';
const listeners=new Set<()=>void>(),pulseListeners=new Set<(kind:HapticKind)=>void>();
const controller=new Controller(async(kind:HapticKind)=>{
 for(const listener of pulseListeners)listener(kind);
 if(Platform.OS==='android'){try{await ExpoHaptics.performAndroidHapticsAsync(kind==='goal'?ExpoHaptics.AndroidHaptics.Segment_Tick:ExpoHaptics.AndroidHaptics.Segment_Frequent_Tick)}catch{await ExpoHaptics.selectionAsync()}}
 else if(Platform.OS==='ios'){if(kind==='goal')await ExpoHaptics.impactAsync(ExpoHaptics.ImpactFeedbackStyle.Soft);else await ExpoHaptics.selectionAsync()}
});
controller.configure({enabled:false,music:false,bpm:90});controller.foreground=AppState.currentState==='active';
let preferenceChanged=false;
AsyncStorage.getItem('solace-haptics-v1').then(raw=>{if(preferenceChanged)return;let saved={};try{saved=JSON.parse(raw||'{}')}catch{}controller.configure(saved);for(const listener of listeners)listener()}).catch(()=>{});
AppState.addEventListener('change',state=>{controller.foreground=state==='active'});
export const haptic=(kind:HapticKind)=>controller.pulse(kind);
export const getHapticPreferences=():HapticPreferences=>({...controller.settings});
let saving=Promise.resolve();
export function setHapticPreferences(value:HapticPreferences){preferenceChanged=true;const next=preferences(value);controller.configure(next);saving=saving.catch(()=>{}).then(()=>AsyncStorage.setItem('solace-haptics-v1',JSON.stringify(next)));saving.catch(()=>{});for(const listener of listeners)listener()}
export function subscribeHaptics(listener:()=>void){listeners.add(listener);return()=>{listeners.delete(listener)}}
export function subscribeHapticPulses(listener:(kind:HapticKind)=>void){pulseListeners.add(listener);return()=>{pulseListeners.delete(listener)}}
export {BeatClock};
