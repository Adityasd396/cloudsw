import React,{useState} from 'react';
import {Image,Pressable,Text,View} from 'react-native';
export type ChatPicture={id:string;url:string;poster:string;width:number;height:number;animated:boolean;deleted:boolean;message?:number};
export default function ChatMedia({media,server,onOpen}:{media:ChatPicture;server:string;onOpen:()=>void}){
 const [playing,setPlaying]=useState(false),[failed,setFailed]=useState(false);
 if(media.deleted)return <Text style={{fontSize:12,color:'#d5c4de',paddingVertical:8}}>Attachment removed</Text>;
 const width=210,height=Math.min(220,Math.max(80,width*media.height/Math.max(1,media.width)));
 return <View style={{marginTop:8,maxWidth:220}}><Pressable accessibilityRole="button" accessibilityLabel="Open shared picture" onPress={onOpen}>{failed?<Text style={{padding:18,color:'#edd6ff',fontSize:14}}>▧ Open attachment</Text>:<Image source={{uri:server+(media.animated&&!playing?media.poster:media.url)}} resizeMode="contain" onError={()=>setFailed(true)} style={{width,height,borderRadius:13,backgroundColor:'#211728'}}/>}</Pressable>{media.animated&&!failed&&<Pressable accessibilityRole="button" onPress={()=>setPlaying(!playing)} style={{padding:8}}><Text style={{fontSize:12,color:'#f3dbff'}}>{playing?'Pause GIF':'Play GIF'}</Text></Pressable>}</View>;
}
