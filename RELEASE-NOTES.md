# Fix release — 12 November 2026

- Room Leave is transactional and idempotent. The final explicit Leave deletes the room and its messages, playlist, typing, presence and ad state while keeping saved display names.
- Simultaneous final Leave requests and retries after lost responses are covered by regressions. Leaving hosts pass control to remaining members.
- Both native Leave controls await confirmation; failed requests keep the room open and show an error. Polling pauses while Leave is pending.
- Health reports the `room_leave_v2` capability to identify the new backend after deployment.
- The Expo fingerprint dependency now uses patched `minimatch` 11.0.1 through a scoped override; the lockfile is included. The post-fix production dependency audit reports zero vulnerabilities.

Validation: 20 backend tests and 11 mobile/JavaScript tests pass; TypeScript checking passes. iOS and Android JavaScript bundle export completed after the fixes. Real-device playback and a real three-hour streaming soak remain unverified.

The previous live test found that PythonAnywhere lacked the Leave endpoint. This package contains the fix, but the hosted site must be updated and reloaded using `PYTHONANYWHERE.md`; these files do not establish a completed live deployment.
