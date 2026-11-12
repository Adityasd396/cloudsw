# Solace release — 12 November 2026

- Added `/iloveyou`: a new chat command opens the supplied love video with floating hearts and a personal letter for Jaanu, on web and native clients. It plays with sound when the platform permits; otherwise one tap starts audible playback. The video is optimized for progressive delivery and bundled in the server ZIP. Existing chat commands are not replayed on join.

- Renamed the visible web and native app branding to Solace, with “A place, comfort and peace” and “With love, made for Jaanu”. Saved preferences and installed-app identifiers are preserved.
- Room Leave is transactional and idempotent. The final explicit Leave deletes the room and its messages, playlist, typing, presence and ad state while keeping saved display names.
- Simultaneous final Leave requests and retries after lost responses are covered by regressions. Leaving hosts pass control to remaining members.
- Both native Leave controls await confirmation; failed requests keep the room open and show an error. Polling pauses while Leave is pending.
- Health reports the `room_leave_v2` capability to identify the new backend after deployment.
- The Expo fingerprint dependency now uses patched `minimatch` 11.0.1 through a scoped override; the lockfile is included. The post-fix production dependency audit reports zero vulnerabilities.

Validation: 20 backend tests and 11 mobile/JavaScript tests pass; TypeScript checking passes. iOS and Android JavaScript bundle export completed after the fixes. Real-device playback and a real three-hour streaming soak remain unverified.

The previous live test found that PythonAnywhere lacked the Leave endpoint. This package contains the fix, but the hosted site must be updated and reloaded using `PYTHONANYWHERE.md`; these files do not establish a completed live deployment.
