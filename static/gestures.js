(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.SolaceGestures=factory()})(typeof globalThis!=='undefined'?globalThis:this,function(){
 const commands=Object.freeze({
  '/love':{emoji:'💖',text:'Love, all around you',effect:'love'},
  '/heartglitter':{emoji:'✨',text:'A little heart glitter',effect:'glitter'},
  '/clap':{emoji:'👏',text:'All the applause for you',effect:'clap'},
  '/hug':{emoji:'🫂',text:'Wrapping you in the warmest hug',effect:'hug'},
  '/kiss':{emoji:'😘',text:'A little kiss, all the way to you',effect:'kiss'},
  '/cuddle':{emoji:'🥰',text:'A cozy little place beside me',effect:'cuddle'},
  '/missyou':{emoji:'💌',text:'Saving this little moment for you',effect:'missyou'},
  '/cheer':{emoji:'🫶',text:'Your own little cheering section',effect:'cheer'}
 });
 function parse(body){const key=typeof body==='string'?body.trim().toLowerCase():'';return Object.hasOwn(commands,key)?{command:key,...commands[key]}:null}
 class Stream{
  constructor(){this.room=null;this.generation=null;this.cursor=null}
  receive(data){const messages=data.messages||[],latest=Math.max(0,...messages.map(m=>m.id));
   if(this.room!==data.id||this.generation!==(data.storage_generation||null)||this.cursor===null){this.room=data.id;this.generation=data.storage_generation||null;this.cursor=latest;return []}
   const events=messages.filter(m=>m.id>this.cursor).sort((a,b)=>a.id-b.id).flatMap(m=>{const gesture=parse(m.body);return gesture?[{id:m.id,name:m.name,...gesture}]:[]});this.cursor=Math.max(this.cursor,latest);return events;
  }
 }
 return {commands,parse,Stream};
});
