import React from 'react';
import {ScrollView,Text,StyleSheet} from 'react-native';
export default function PrivacyView(){return <ScrollView contentContainerStyle={s.page}>{['Room chat is removed when everyone explicitly leaves. Temporary disconnections have a 30-minute recovery window.','Private chat backups, IP addresses and activity records are retained for 30 days, including after a room is deleted. Access is password-protected.','Shared public IP addresses can reflect shared Wi-Fi, a VPN or a mobile carrier. They do not identify a person.','Haptic and display preferences are saved on this device.'].map(copy=><Text key={copy} style={s.copy}>{copy}</Text>)}</ScrollView>}
const s=StyleSheet.create({page:{padding:20},copy:{color:'#d3c3df',fontSize:15,lineHeight:26,marginBottom:20}});
