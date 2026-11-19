import React,{useEffect,useMemo,useRef,useState} from 'react';
import {View} from 'react-native';
import {WebView} from 'react-native-webview';
import {haptic} from './Haptics';
const dice=require('./dice-result.cjs');
type Roll={id:string;dice:number;name:string;created:number};
export default function LudoRollNotice({roll,roomKey,active}:{roll?:Roll|null;roomKey:string;active:boolean}){
 const cursor=useRef<{room:string;id:string|null}|null>(null),[visible,setVisible]=useState<Roll|null>(null);
 useEffect(()=>{if(cursor.current?.room!==roomKey){cursor.current={room:roomKey,id:roll?.id||null};setVisible(null);return}if(!roll||cursor.current.id===roll.id)return;cursor.current.id=roll.id;if(!active||!Number.isInteger(roll.dice)||roll.dice<1||roll.dice>6)return;setVisible(roll);haptic('game');const timer=setTimeout(()=>setVisible(null),3000);return()=>clearTimeout(timer)},[roll?.id,roomKey]);
 useEffect(()=>{if(!active)setVisible(null)},[active]);
 const source=useMemo(()=>{if(!visible)return {html:''};const name=visible.name.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));return {html:'<meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:transparent}'+dice.css+'.dice-result{position:relative;top:0;left:0;transform:none;width:156px;box-sizing:border-box}</style><aside class="dice-result"><div class="who">'+name+' rolled ♡</div>'+dice.markup(visible.dice)+'</aside>'}},[visible]);
 if(!visible||!active)return null;
 return <View pointerEvents="none" accessibilityLabel={visible.name+' rolled '+visible.dice} style={{position:'absolute',top:62,right:12,width:156,height:170,zIndex:600}}><WebView pointerEvents="none" source={source} javaScriptEnabled={false} scrollEnabled={false} style={{backgroundColor:'transparent'}}/></View>
}
