import React,{useEffect,useRef,useState} from 'react';
import {Animated} from 'react-native';
import {getHapticPreferences,subscribeHaptics,subscribeHapticPulses} from './Haptics';
export default function RhythmHeart({reduced}:{reduced:boolean}){
 const [settings,setSettings]=useState(getHapticPreferences),opacity=useRef(new Animated.Value(.35)).current;
 useEffect(()=>subscribeHaptics(()=>setSettings(getHapticPreferences())),[]);
 useEffect(()=>subscribeHapticPulses(kind=>{if(kind!=='beat')return;opacity.stopAnimation();opacity.setValue(1);Animated.timing(opacity,{toValue:.35,duration:reduced?0:200,useNativeDriver:true}).start()}),[reduced]);
 if(!settings.enabled||!settings.music)return null;
 return <Animated.Text accessible={false} style={{fontSize:12,color:'#e5b2cb',opacity}}>♡</Animated.Text>;
}
