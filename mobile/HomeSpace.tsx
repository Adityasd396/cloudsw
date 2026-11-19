import React from 'react';
import {View,Text,Pressable} from 'react-native';
import {WebView} from 'react-native-webview';
export default function HomeSpace({server,onRoom,onSettings}:{server:string;onRoom:(room:string,token:string)=>void;onSettings:()=>void}){
 const base=server.replace(/\/$/,'');
 return <View style={{flex:1,backgroundColor:'#17121f'}}><WebView source={{uri:base+'/home'}} sharedCookiesEnabled thirdPartyCookiesEnabled={false} originWhitelist={[base]} onShouldStartLoadWithRequest={n=>{try{return n.url==='about:blank'||new URL(n.url).origin===new URL(base).origin}catch{return false}}} onMessage={e=>{try{if(new URL(e.nativeEvent.url).origin!==new URL(base).origin)return;const d=JSON.parse(e.nativeEvent.data);if(d.type==='room-ready'&&/^\d{6}$/.test(d.room)&&typeof d.token==='string')onRoom(d.room,d.token)}catch{}}} renderError={()=><View style={{padding:24}}><Text style={{color:'#ead5f4'}}>Unable to reach Solace. Check your connection or server address.</Text></View>} style={{flex:1,backgroundColor:'#17121f'}}/><Pressable onPress={onSettings} accessibilityRole="button" style={{padding:12,alignItems:'center'}}><Text style={{color:'#cab6d8',fontSize:12}}>Server settings</Text></Pressable></View>;
}
