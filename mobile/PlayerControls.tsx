import React,{useEffect,useRef,useState} from 'react';
import {AccessibilityInfo,Animated,Pressable,StyleSheet,Text,View} from 'react-native';
const {AutoHideControls}=require('./session.cjs');
type Props={playing:boolean;expanded:boolean;active:boolean;captureTouches:boolean;disabled:boolean;onSeek:(delta:number)=>void;onToggle:()=>void;onFullscreen:()=>void};
export default function PlayerControls(props:Props){
 const controller=useRef(new AutoHideControls(3000)),opacity=useRef(new Animated.Value(1)).current;
 const visibleRef=useRef(true);
 const [visible,setVisible]=useState(true),[screenReader,setScreenReader]=useState(false);
 function paint(next:boolean){if(visibleRef.current===next)return;visibleRef.current=next;setVisible(next);Animated.timing(opacity,{toValue:next?1:0,duration:200,useNativeDriver:true}).start()}
 useEffect(()=>{AccessibilityInfo.isScreenReaderEnabled().then(setScreenReader);const listener=AccessibilityInfo.addEventListener('screenReaderChanged',setScreenReader);return()=>listener.remove()},[]);
 useEffect(()=>{controller.current.show();paint(true);if(!props.active)return;const timer=setInterval(()=>{const next=(controller.current.focused=screenReader,controller.current.update(props.playing));paint(next)},250);return()=>clearInterval(timer)},[props.playing,props.active,props.expanded,screenReader]);
 const interact=(action:()=>void)=>{controller.current.show();paint(true);action()};
 return <View pointerEvents="box-none" style={StyleSheet.absoluteFill}>{props.captureTouches&&<Pressable accessibilityRole="button" accessibilityLabel="Show or hide playback controls" style={StyleSheet.absoluteFill} onPress={()=>{controller.current.show();paint(true)}}/>}<Animated.View pointerEvents={visible?'auto':'none'} accessibilityElementsHidden={!visible} importantForAccessibility={visible?'auto':'no-hide-descendants'} style={[s.bar,{opacity}]}>{[['−10s',()=>props.onSeek(-10)], [props.playing?'Pause':'Play',props.onToggle],['+10s',()=>props.onSeek(10)],[props.expanded?'⛶ Exit':'⛶ Fullscreen',props.onFullscreen]].map(([label,action],index)=><Pressable key={index} accessibilityRole="button" accessibilityLabel={String(label)} disabled={index!==3&&props.disabled} style={s.button} onPress={()=>interact(action as ()=>void)}><Text style={s.label}>{String(label)}</Text></Pressable>)}</Animated.View></View>;
}
const s=StyleSheet.create({bar:{position:'absolute',bottom:0,left:0,right:0,flexDirection:'row',justifyContent:'center',alignItems:'center',gap:7,padding:13,backgroundColor:'#00000066'},button:{backgroundColor:'#191720cc',borderWidth:1,borderColor:'#ffffff24',borderRadius:11,minHeight:42,paddingHorizontal:12,paddingVertical:10,justifyContent:'center'},label:{color:'#f0eafa',fontSize:11}});
