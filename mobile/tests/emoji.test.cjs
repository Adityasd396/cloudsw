const test=require('node:test'),assert=require('node:assert/strict');
const {extractEmoji,emojiOnly}=require('../emoji.cjs');
test('reactions handle skin tones, joined emoji, flags and messages',()=>{
 assert.deepEqual(extractEmoji('great movie 🥰 👩🏽‍🚀 🇮🇳'),['🥰','👩🏽‍🚀','🇮🇳']);
 assert.equal(emojiOnly('👩🏽‍🚀 ❤️'),true);
 assert.equal(emojiOnly('123'),false);
 assert.equal(emojiOnly('hello 😂'),false);
});
