# Solace cute update — 13 November 2026

Love hoops is a two-player basketball game in the website's Play together panel. Players time a shot at the heart, alternate turns, and race to five baskets. A scored basket shows “it's a love goal ♡”. Scores and turns are server-backed and shared. The existing tic-tac-toe game remains available from the game panel.

The site uses subtle rose/lilac colors and softer details. Removed repeated chat welcome paragraphs, the extra empty-playlist explanation and the default picker instruction. Useful errors, typing and connection feedback remain. All existing /iloveyou assets, the love video and its message are byte-for-byte unchanged from the previous packaged version.

## Checks completed

- 45 backend/startup tests passed, including five new basketball regressions: two-user scoring and misses, turns, first-to-five/reset, concurrent duplicate-shot protection, invalid input/access rejection, room deletion, keeping tic-tac-toe state, and independent playback during a game.
- 55 real-HTTP smoke assertions passed, including admin login/logout, basketball, shared play/pause/seek, queue reorder and final-Leave deletion.
- 31 existing JavaScript/native regressions passed, including stale-pause protection, recovery and the love command.
- Two independent browser sessions (separate localhost and 127.0.0.1 cookies) joined the same room. Pause reached both players. A guest forward seek left both paused at 43.738865 seconds. Resume from the guest reached the host. A host backward seek and resume also reached the guest; a later playing snapshot measured 126.506741 and 126.478637 seconds. These are observed samples, not a guaranteed drift bound.
- Portrait at 390×844: controls begin below the picture; search input works; queue is present; playback controls have display:none while the picker is open.
- Landscape at 844×390: search and queue remain unobstructed; playback controls stay hidden during selection; fullscreen fills the viewport and controls auto-hide/reappear on touch.
- Opened the basketball game from both sessions, joined both players, took shots and observed shared scores. Timed a successful shot and captured the requested popup. Checked the court and controls in portrait and landscape.
- Left both sessions and restored the test browser viewport. No live deployment was performed.

Browser evidence: love-goal-popup.jpg, love-hoops-landscape.jpg, cute-portrait-picker.jpg and cute-landscape-picker.jpg beside this report. Physical Android/iPhone testing remains unverified. The separately installed native client retains its existing native game screen; this update adds basketball to the website for phone browsers.

## Upload

Use Solace-pythonanywhere.zip. Replace the packaged server modules and entire static/ and templates/ folders in the existing application directory; preserve instance/ and reload PythonAnywhere. New files include static/basketball.js, static/basketball.css and static/tictactoe.html. Upload room_game.py with app.py. Solace-release-source.zip includes source, tests and reports. Neither ZIP includes private databases, passwords or API keys.

## Portrait activity and latest-message follow-up

The activity overlay directly over the video is hidden in portrait and visible in landscape. Footer names remain available in the normal portrait room. Chat now follows message mutations after reply buttons and bubble layout finish, and follows input focus/input events plus visual viewport and chat-size changes. Short conversations align toward the composer; bubbles do not shrink or clip, the last bubble has no trailing margin, and an empty typing indicator takes no height.

Actual browser checks used 390×844 portrait, a 390×500 resized keyboard layout and 844×390 landscape. The newest message stayed visible after typing and resizing (scroll remainder below one pixel). The keyboard layout measured a 4.1-pixel bubble-to-composer gap and the composer ended at the 500-pixel viewport edge. A second independent browser sent an incoming message; the first browser displayed it at the bottom while retaining its unsent draft. Portrait overlay computed display:none; landscape computed display:flex with both names. The rapid dummy-message test encountered the existing send-rate limit; a retry after the limit interval succeeded and the draft was preserved. No change to that rate limit was made.

All 55 real-HTTP smoke assertions passed with the updated template and new script; JavaScript syntax checking passed. No physical phone keyboard was available; viewport resizing tests the layout rather than the device keyboard itself. Screenshots: chat-keyboard-layout.jpg, chat-portrait-latest.jpg and chat-landscape-activity.jpg. The new static/chat-scroll.js must be uploaded with the updated template and stylesheet.
