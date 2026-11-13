# Solace release — 13 November 2026

YouTube UI update: ordinary video taps use Solace controls in both orientations. Added supported keyboard/fullscreen/annotation parameters and extended native video-only UI filtering. Complete permanent hiding of YouTube branding/title in web iframe states is not supported; see CUTE-UPDATE-REPORT.md.

Keyboard reliability update: web chat follows keyboard opening/closing with bounded settling checks; native chat follows keyboard will/did events and list layout/content changes. Drafts are preserved and the scroll handler never calls video controls. 35 client tests, 55 HTTP smoke assertions, TypeScript and Android/iOS bundle export pass. Browser keyboard simulations preserve the latest message while both videos keep playing; real-phone keyboard testing remains pending.

Chat layout update: portrait video activity chips are hidden while landscape retains them. Short chats align toward the composer, empty typing space is removed, and scrolling follows new messages, typing focus and keyboard/viewport resizing. Verified incoming chat from a second browser without losing the draft; the latest bubble stayed visible with a roughly four-pixel gap to the composer in a resized keyboard layout.

Cute update: added two-player Love hoops basketball with shared scores, turns, first-to-five rounds and a love-goal popup. Softened website colors and trimmed repeated welcome/playlist copy. The love command is unchanged. Portrait/landscape and two-browser playback smoke checks passed. See CUTE-UPDATE-REPORT.md for current results: 45 backend tests, 55 HTTP smoke assertions and 31 client regressions.

Latest update: portrait playback controls remain visible in a compact row below the video. Landscape controls float over the video and hide after three seconds. Playback controls are hidden while selecting songs, so search and queue management stay unobstructed. Landscape supports full-viewport viewing. Improved recovery after backgrounding, renderer restarts and transient play failures, independent chat polling, incremental chat responses, and foreground screen wakefulness. Accelerated three-hour replay passed; actual phone soak remains unverified. See LONG-SESSION-REPORT.md.

Local smoke update: 46 real-HTTP assertions plus actual browser login/logout and room checks pass. Corrected iframe header spacing so overlay buttons receive pointer clicks reliably. Added fresh/legacy startup checks and isolated smoke tooling. See LOCAL-SMOKE-TEST.md.

Room-experience update: Back no longer directly exits the Android app; swipe/hold to reply; keyboard-aware viewing; temporary fullscreen landscape chat bubbles; always-visible activity chips and host crowns; ad alerts from any participant. A hidden password-protected operations panel adds health, worker metrics, 30-day IP/activity history, matching-IP groups and chat backup. It uses no push notification APIs. See ADMIN-SETUP.md for one-time server setup and ROOM-EXPERIENCE-REPORT.md for current validation.

Previous update: iPhone fullscreen fallback; playback/queue controls for every joined participant; exactly-once automatic queue advancement with repeated-video support; queue management under playlist search; right/left sender-aware colored chat bubbles; two-player online tic-tac-toe; expanded native ad filtering. Host transfer remains creator/host-only. See `UPDATE-REPORT.md` for validation and limits.

- Added `/iloveyou`: a new chat command opens the supplied love video with floating hearts and a personal letter for Jaanu, on web and native clients. It plays with sound when the platform permits; otherwise one tap starts audible playback. The video is optimized for progressive delivery and bundled in the server ZIP. Existing chat commands are not replayed on join.

- Renamed the visible web and native app branding to Solace, with “A place, comfort and peace” and “With love, made for Jaanu”. Saved preferences and installed-app identifiers are preserved.
- Room Leave is transactional and idempotent. The final explicit Leave deletes the room and its messages, playlist, typing, presence and ad state while keeping saved display names.
- Simultaneous final Leave requests and retries after lost responses are covered by regressions. Leaving hosts pass control to remaining members.
- Both native Leave controls await confirmation; failed requests keep the room open and show an error. Polling pauses while Leave is pending.
- Health reports the `room_leave_v2` capability to identify the new backend after deployment.
- The Expo fingerprint dependency now uses patched `minimatch` 11.0.1 through a scoped override; the lockfile is included. The post-fix production dependency audit reports zero vulnerabilities.

Current validation: 45 backend/startup tests, 35 mobile/JavaScript tests, 12 bounded local checks and 55 real-HTTP smoke assertions pass. TypeScript checking and iOS/Android JavaScript bundle export pass. Real-device three-hour playback remains unverified.

The previous live test found that PythonAnywhere lacked the Leave endpoint. This package contains the fix, but the hosted site must be updated and reloaded using `PYTHONANYWHERE.md`; these files do not establish a completed live deployment.
