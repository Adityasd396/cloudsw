import React,{useEffect,useState} from 'react';
import {View,Text,Pressable} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
const {themes,valid}=require('./chat-themes.cjs');
let choice='solace',changed=false,writes=Promise.resolve();const listeners=new Set<()=>void>();
AsyncStorage.getItem('solace-chat-theme').then(value=>{if(!changed){choice=valid(value);listeners.forEach(fn=>fn())}}).catch(()=>{});
export function setChatTheme(key:string){changed=true;choice=valid(key);listeners.forEach(fn=>fn());writes=writes.catch(()=>{}).then(()=>AsyncStorage.setItem('solace-chat-theme',choice))}
export function useChatTheme(){const [key,setKey]=useState(choice);useEffect(()=>{const fn=()=>setKey(choice);listeners.add(fn);fn();return()=>{listeners.delete(fn)}},[]);return {...themes[key],key}}
export default function ChatThemes(){const current=useChatTheme();return <View style={{marginTop:24,gap:12}}><Text style={{color:'#f5edf8',fontSize:15}}>Chat theme</Text><View style={{flexDirection:'row',flexWrap:'wrap',gap:10}}>{Object.keys(themes).map(key=><Pressable key={key} accessibilityRole="button" accessibilityState={{selected:current.key===key}} onPress={()=>{changed=true;choice=key;listeners.forEach(fn=>fn());writes=writes.catch(()=>{}).then(()=>AsyncStorage.setItem('solace-chat-theme',key))}} style={{width:'47%',minHeight:52,borderWidth:current.key===key?2:1,borderColor:current.key===key?'#e2c5ee':'#56415f',borderRadius:16,backgroundColor:themes[key].mine,padding:12,justifyContent:'center'}}><Text style={{color:'#fff',fontSize:13}}>{themes[key].name}</Text></Pressable>)}</View></View>}
