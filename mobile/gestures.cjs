(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.SolaceGestures=factory()})(typeof globalThis!=='undefined'?globalThis:this,function(){
 const commands=Object.freeze({
  '/hug':{emoji:'🫂',text:'A warm hug, just for you'},
  '/kiss':{emoji:'😘',text:'A little kiss across the distance'},
  '/cuddle':{emoji:'🥰',text:'Come a little closer'},
  '/missyou':{emoji:'💌',text:'Wish you were right here'},
  '/cheer':{emoji:'🫶',text:'Always cheering for you'}
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
