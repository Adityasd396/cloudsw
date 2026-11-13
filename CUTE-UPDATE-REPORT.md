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

## Keyboard open/close reliability follow-up

Web chat now scrolls immediately and at bounded 120/300/600 ms settling points after focus, blur, viewport resize/scroll and ordinary window resize. Repeated events replace pending settling timers; only one animation frame is pending at a time. Pagehide clears pending work. The scroll helper only changes the message list's scrollTop; it never focuses the page or invokes the player, playback API, pause or seek.

The native chat now follows FlatList layout/content-size changes, typing focus/blur and input. It follows Android did-show/did-hide events and both iOS will/did keyboard events. Scroll requests are coalesced to one frame and cancelled on unmount. Short lists align at the bottom with reduced padding. No playback or synchronization routines were changed.

Validation: 35 client tests pass, including four new keyboard regressions covering iPhone visual-viewport and Android resize sequences, delayed keyboard-close layout, incoming messages while typing, draft preservation, event storms bounded to three timers/one frame, cleanup, fallback without visualViewport, and guards that throw if scroll handling touches the player or network. Existing sync, stale-pause, media recovery and three-hour model tests still pass. TypeScript checking and Android/iOS JavaScript bundle exports pass. All 55 HTTP smoke assertions pass.

Two independent browser sessions played video while one viewport changed between 390×844 and 390×500. The latest incoming message stayed visible during typing, with the draft intact. On keyboard close, including close while the textbox remained focused, the scroll remainder was zero and keyboard layout was cleared. Once the second browser received its required initial YouTube playback gesture, both remained playing through open/close transitions; observed times progressed from about 49 seconds to 71 seconds. A closed-keyboard sample measured 71.086836 and 71.232470 seconds (about 0.15 seconds apart), not a guarantee of drift on other devices. Normal browser autoplay permissions still apply.

Evidence: keyboard-open-latest.jpg and keyboard-closed-latest.jpg beside this report. These are desktop browser viewport simulations and automated event tests, not physical iPhone/Android keyboard tests. Rebuild the native apps to include their FlatList/keyboard changes; the server ZIP updates phone-browser behavior.

## YouTube on-video overlay follow-up

Confirmed the request refers to YouTube's own title, logo, share and player overlay, rather than Solace's control row. Web player parameters keep controls=0 and add disablekb=1, fs=0 and iv_load_policy=3. Ordinary taps route to Solace's touch surface in both portrait and landscape; the surface releases pointer handling when an initial YouTube playback gesture is required, and disappears during song selection. This avoids opening YouTube's interaction overlay through ordinary taps while retaining Solace's controls. Native video-only layout additionally hides YouTube chrome, pause panels, bezel and end-card UI in the page it owns; the initial play affordance remains available.

Limit: YouTube's cross-origin iframe controls its own title/branding and paused/permission states. Complete permanent removal across all states/devices is not supported. Do not describe the web player as fully unbranded. The official player documentation states that modestbranding has no effect and older showinfo settings are deprecated: https://developers.google.com/youtube/player_parameters . No masking or cropping of the video was introduced.

Verified playing view at 390×844 with no YouTube overlay visible in the screenshot, and an active tap surface at 844×390. Confirmed actual iframe parameters, video kept playing after an ordinary tap, Solace pause/resume still operated, and both Solace controls and the touch surface were display:none while the song picker was open. 35 client regressions and 55 HTTP smoke assertions passed. Android/iOS bundle exports passed; physical devices remain unverified. Screenshot: player-ui-portrait.jpg. Native UI filtering requires rebuilding installed apps. The website limitation remains after upload.
