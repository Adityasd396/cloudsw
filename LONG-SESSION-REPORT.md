# Solace reliability and player update — 13 November 2026

## Result and limits

Accelerated three-hour protocol and media-model tests passed. These replay simulated time; they are not three hours of physical Android/iPhone playback. No phones were available. Battery, temperature, actual Safari/WebView background suspension, OS process death, real ad delivery and mobile rotation still require physical-device testing. No guarantee of uninterrupted playback or zero ads is implied.

## Player controls

Updated after phone screenshot feedback: web and native portrait playback controls stay visible in their own compact row below the video. Landscape controls float over the image, hide after three seconds without interaction, and reappear when the video is tapped. Song selection hides playback controls; opening the web picker also exits fullscreen. Fullscreen remains available in landscape; the image preserves its aspect ratio. Native orientation and touch-capable web landscape viewing expand the video automatically. Returning to portrait restores the prior layout. Keyboard-focused web controls and native screen-reader controls stay available for accessibility. Activity chips remain visible.

Actual local browser checks verified playing video, controls hidden after the deadline, tap-to-show, fullscreen entry/exit, a full-viewport video surface, and returning home after Leave. Screenshots are saved beside this report as fullscreen-overlay-controls.jpg and fullscreen-controls-hidden.jpg. A temporary narrow-landscape viewport was reset after verification. Physical iPhone/Android rotation remains unverified.

## Reliability fixes

- Chat polling continues while native chat mutations are in flight. Incremental message responses avoid downloading the full chat history on every poll; merged display history stays bounded at 100 messages while database history remains intact until room deletion.
- Background and recovery gates prevent stale player pause/position samples from being published after returning to the app. Fresh authoritative room state is read before publication resumes.
- Transient media play failures can retry. Actual autoplay permission denial still requires a user gesture. Hung play promises expire after ten seconds, and obsolete promise completions cannot overwrite a newer attempt.
- Native WebView renderer recovery reloads the player with fresh room state, with at most three automatic restarts per minute before showing Retry.
- Foreground native playback requests screen wakefulness. The website makes a best-effort screen wake-lock request where supported. Neither uses push notifications.

## Evidence

| Check | Result |
| --- | --- |
| Accelerated backend timeline | 10,800 simulated seconds; 4,253 polls; 20,065 assertions passed in 230.73 seconds |
| Saved history / queue | 719 chat messages; 18 queue entries; two saved profiles |
| Media models | Android-model and iPhone-model each replayed 10,800 seconds |
| Backend/startup regressions | 40 passed |
| JavaScript/native regressions | 31 passed |
| Real HTTP smoke journey | 46 assertions passed, including admin login/logout and final-Leave deletion |
| Local concurrency, bounds and security | 12 passed; 120 concurrent room reads, 20 playlist writes retained |
| TypeScript | Passed |
| Android and iOS JavaScript bundle export | Passed |

The final full room response measured 35,625 bytes; the incremental response measured 3,297 bytes, including unread chat. This is a sample comparison, not a production bandwidth guarantee. Temporary replay databases measured 278,528 and 245,760 bytes. Their size does not establish a fixed long-term database bound. The private backup has its existing 30-day retention policy.

The replay includes pause/resume/seek, repeated queue advancement, chat, ads reported through the room protocol, 30/75-second background gaps, a 90-second network gap, and both clients briefly absent. The final explicit Leave deleted public room data and retained saved profiles. The existing abandoned-room rule still applies: if everyone stops contacting the server for over 120 seconds, the room expires on the next API request. Locking or backgrounding both phones for longer can therefore end the room.

## Deployment and physical-device follow-up

Upload the whole Solace-pythonanywhere.zip contents into the existing server application directory, preserve instance/, and reload the PythonAnywhere web app. The live server has not been updated by this local work. Rebuild installed Android/iPhone apps from the updated source; the new expo-keep-awake dependency requires a new native build. Bundle export does not create signed APK/IPA installers.

For a physical three-hour run, use one Android phone and one iPhone in the same room. Exercise play/pause/seek from both, chat during playback, queue transitions, portrait/landscape fullscreen, brief background/network interruptions and recovery, and final Leave. Observe battery, heat, audible playback permission prompts and sync drift. Include a separate test where both phones are absent for over two minutes to verify the documented room-expiry behavior.

Portrait/picker regression check: verified at 390×844 that the control row begins exactly at the video bottom, the search textbox remains usable, and controls have display:none while the song picker is open. At 844×390, verified overlay positioning, automatic hiding and tap-to-show. Native TypeScript checking passed; no physical phones were used. Current screenshots: portrait-controls-below.jpg and portrait-picker-fixed.jpg, beside this report.
