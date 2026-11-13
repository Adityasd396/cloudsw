# Local smoke test — 13 November 2026

**Result: passed. The admin login/logout failure is resolved, and browser testing found and fixed an overlay pointer-targeting issue.**

Tests used disposable databases, an isolated signing key, a test-only password, and a separate localhost Waitress server. Your real administrator password and saved records were not used or changed. The reusable HTTP runner now also uses a separate cookie name to avoid replacing normal local-app sessions.

## Automated results

| Group | Result | Evidence |
| --- | --- | --- |
| Real HTTP journey through Waitress | 46/46 assertions pass; clean exit 0 | `local-http-smoke-results.json`, `validation-local-http-smoke.txt` |
| Backend regression and startup checks | 38/38 pass, including fresh install and legacy database migration | `validation-local-full-backend.txt` |
| Client regressions | 22/22 pass | `validation-local-full-client.txt` |
| TypeScript check | Pass | `validation-local-full-types.txt` |
| Local concurrency/input/access checks | 12/12 pass | `validation-local-full-bounds.txt` |

The HTTP journey checks login-page headers, missing CSRF rejection, opaque/foreign/different-port Origin rejection, wrong passwords, successful login redirects, dashboard HTML/scripts/data, invalid logout requests, successful logout, blocked stats/backups after logout, re-login, expiration, and final logout. It also covers home assets, two guest sessions, chat/replies/identity/crowns, typing, shared pause/seek, stale-pause rejection, playlist ordering, duplicate-end protection, participant ad alerts, two-player game moves/winner, video range delivery, room deletion and protected backup retention.

## Browser verification

Verified in the in-app browser against the isolated local server:

- Wrong-password feedback appears normally.
- The real HTML login form successfully opens the dashboard, with live health cards, IP groups and activity logs. No cross-origin rejection occurs.
- Lock panel returns to the login screen. Browser Back does not restore private dashboard access.
- Home, create-room, initial video selection, own-message chat, quoted replies, and the manageable playlist picker render and respond.
- The game opens and Join game works by pointer after the layout fix.
- Fitted fullscreen enters/exits with controls and activity visible. Leave returns to the minimal home screen.
- No app warnings/errors were reported in the inspected browser console.

Screenshots: `local-admin-dashboard-smoke.jpg`, `local-admin-logout-smoke.jpg`, `local-playlist-smoke.jpg`. They contain disposable test data only.

## Fixes retained or added

1. Admin pages use `Referrer-Policy: same-origin`. The former `no-referrer` policy could turn a basic form POST's Origin into `null`; foreign/opaque origins remain blocked, and password/CSRF checks remain intact.
2. Overlay header spacing now belongs to the dialog container rather than padding the embedded iframe. This corrects pointer targeting inside game/love overlays. The game Join button was verified by pointer after a reload, and web asset versions were bumped.
3. Added repeatable real-HTTP and fresh/legacy startup smoke checks. The HTTP runner's test cookie namespace is separate from the normal application.

The release folder and both ZIPs are refreshed with the verified files and tests.

## Repeat locally

```text
python -B tests/run_local_smoke.py
python -B -m unittest discover -s tests -v
npm test --prefix mobile
npm run check --prefix mobile
python -B tests/run_validation.py
```

For optional browser testing, `python -B tests/run_local_smoke.py --serve --port 8017` leaves a **test-only** server running on loopback. Its public fixture password is defined in the test script. Stop it afterward; use the normal launcher and your real password for the real app.

## Limits

This was a local smoke run, not a new PythonAnywhere deployment, a physical-phone acceptance test or a multi-hour playback soak. The browser loaded the YouTube player, but continuous YouTube playback, ad removal and cross-device media timing were not established. The disposable server has no saved YouTube search key, so selection used the featured collection; the existing key/search logic remains covered by mocked backend tests. Platform-provided host load is unavailable on Windows and is shown as unavailable rather than a fabricated value.
