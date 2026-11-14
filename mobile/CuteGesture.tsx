import React,{useEffect,useRef,useState} from 'react';
import {AccessibilityInfo,Animated,StyleSheet,Text} from 'react-native';
export type Gesture={id:number;name:string;emoji:string;text:string};
export default function CuteGesture({event}:{event:Gesture|null}){
 const [visible,setVisible]=useState(false),opacity=useRef(new Animated.Value(0)).current;
 useEffect(()=>{if(!event){setVisible(false);return}let live=true;setVisible(true);opacity.setValue(0);AccessibilityInfo.isReduceMotionEnabled().catch(()=>true).then(reduced=>{if(live)Animated.timing(opacity,{toValue:1,duration:reduced?0:180,useNativeDriver:true}).start()});const timer=setTimeout(()=>setVisible(false),3200);return()=>{live=false;clearTimeout(timer);opacity.stopAnimation()}},[event]);
 if(!event||!visible)return null;
 return <Animated.View pointerEvents="none" accessibilityLiveRegion="polite" style={[styles.badge,{opacity}]}><Text style={styles.art}>{event.emoji}</Text><Text style={styles.label}>{event.name} · {event.text}</Text></Animated.View>;
}
const styles=StyleSheet.create({badge:{position:'absolute',top:56,alignSelf:'center',zIndex:300,maxWidth:'92%',flexDirection:'row',alignItems:'center',gap:9,paddingHorizontal:14,paddingVertical:9,borderRadius:24,backgroundColor:'#35243ef0'},art:{fontSize:25},label:{fontSize:12,color:'#f9eaf5',flexShrink:1}});
