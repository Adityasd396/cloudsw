> Historical report: the current source release is documented in ROOM-EXPERIENCE-REPORT.md.

# Solace update — 13 November 2026

Implemented the requested iPhone fullscreen fallback, shared playback controls, guarded queue continuation, playlist management inside search, sender-aware chat bubbles, stronger native ad filtering and two-player online tic-tac-toe.

## Verification

- 25 backend tests pass, including simultaneous song-end requests against repeated video IDs, guest playback permissions, matching display names, game turns/winner/reset, duplicate move rejection, and room/game deletion.
- 18 JavaScript/mobile tests pass, including missing/rejected fullscreen APIs, stale-pause protection, newer shared controls applied to the host, and initial JSON/XHR/fetch ad filtering.
- 12 local concurrency/access/error checks pass. Updated permissions retain unjoined-client and host-transfer boundaries.
- TypeScript checking and Android/iOS JavaScript bundle exports pass (exit 0). Export results are recorded in `validation-update-export.txt`.

Earlier reports describe previous source/deployments. This update has not been deployed to PythonAnywhere during this task. Upload the current server ZIP and reload, following `PYTHONANYWHERE.md`; rebuild installed phone apps for native changes.

The fullscreen fallback fills the browser viewport when platform fullscreen is unavailable. Physical iPhone/Android playback and native compilation have not been verified here. Filtering changes do not establish ad-free YouTube, especially in the browser iframe. A real multi-hour playback soak remains unverified.
