const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.join(__dirname,'../..');
test('retired personal prompt has no browser or native implementation',()=>{
 for(const name of ['static/love.js','static/love.html','static/love.css','static/love-film.js','templates/love-public.html'])assert.equal(fs.existsSync(path.join(root,name)),false,name);
 for(const name of ['mobile/App.tsx','templates/index.html','static/room-experience.js','static/experience-refinements.js','static/haptic-settings.js','static/launch-client.js','static/gesture-effects.js','static/room-dice-result.js','static/experience-v2.js'])assert.doesNotMatch(fs.readFileSync(path.join(root,name),'utf8'),/[Ll]oveOpen|loveOverlay|closeLove|loveRoom|loveCursor|\/iloveyou|love_enabled|\/static\/love/);
});
