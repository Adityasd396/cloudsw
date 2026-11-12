const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const script=fs.readFileSync(path.join(__dirname,'../../static/love-film.js'),'utf8');
test('love film requests audible playback and offers a tap when autoplay is blocked',async()=>{
 let permitted=false;const events={};
 const film={muted:false,paused:true,volume:1,error:null,addEventListener(name,fn){events[name]=fn},async play(){assert.equal(this.muted,false);if(!permitted)throw Error('NotAllowedError');this.paused=false;events.playing?.()}};
 const sound={hidden:false,textContent:'Play with sound ♡',addEventListener(name,fn){events[name]=fn}};
 const context={document:{getElementById:id=>id==='loveVideo'?film:sound}};
 vm.createContext(context);vm.runInContext(script,context);
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(film.muted,false);assert.equal(sound.hidden,false);assert.match(sound.textContent,/Play with sound/);
 permitted=true;await events.click();assert.equal(film.muted,false);assert.equal(sound.hidden,true);
 const html=fs.readFileSync(path.join(__dirname,'../../static/love.html'),'utf8');
 const videoTag=html.match(/<video\b[^>]*>/)[0];assert.doesNotMatch(videoTag,/\bmuted\b/);assert.match(videoTag,/playsinline/);
});
