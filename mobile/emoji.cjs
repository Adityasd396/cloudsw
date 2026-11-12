function extractEmoji(text){return String(text).match(/\p{Extended_Pictographic}(?:\uFE0F|\p{Emoji_Modifier})?(?:\u200D\p{Extended_Pictographic}(?:\uFE0F|\p{Emoji_Modifier})?)*|\p{Regional_Indicator}{2}/gu)||[]}
function emojiOnly(text){return extractEmoji(text).length>0&&String(text).replace(/[\p{Extended_Pictographic}\p{Regional_Indicator}\p{Emoji_Component}\s]/gu,'')===''}
module.exports={extractEmoji,emojiOnly};
