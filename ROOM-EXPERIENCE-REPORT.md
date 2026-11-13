# Solace room experience and private panel — 13 November 2026

## Delivered

- Android Back closes the keyboard, fullscreen, picker or reply state and stays in the app at its root. Browser room navigation has a Back guard; explicitly leaving still uses Leave.
- Swipe sideways or hold a native chat message to reply. Browser messages support swiping and an accessible reply button. Quoted messages are validated against the same room and stored in SQLite.
- Keyboard-aware sizing keeps a fitted video above the visible chat area. New chat messages become short-lived bubbles during landscape fullscreen and disappear after roughly 6.5 seconds.
- Corner activity chips remain visible in the player, fullscreen and supported room overlays. The current host has a crown. Message, overlay and gesture transitions are animated.
- Any participant can report an ad. Native YouTube observers report detected ads; web participants have an Ad playing/Ad ended button. Other participants see a deduplicated, temporary in-app alert. No OS notification delivery, notification permissions, email or external analytics integration is added.
- The hidden `/ops/solace` panel is disabled until a server owner chooses a password. It provides health/status, app timing and request/error metrics, worker CPU/uptime, host load where available, guest activity/IP matches, audit events and protected JSON chat backups.
- Private IP/activity/backup records use a separate database and a 30-day visibility/export window, with lazy pruning. The setup command can seed still-existing recent messages. Room deletion removes public room records while preserving the private backup within retention.

## Verification

- **38 backend/startup tests pass**, including the admin form-origin regression, fresh-install startup and legacy database preservation. The real-HTTP and browser smoke results are detailed in LOCAL-SMOKE-TEST.md.
- **22 client tests pass**, covering back-action priority, keyboard sizing, swipe completion/cancellation, ad alert deduplication, fullscreen fallback, playback races and existing features.
- **12 bounded local concurrency, input/error and access checks pass.** Telemetry handles oversized request errors without replacing their HTTP 413 response.
- TypeScript checking and Android/iOS JavaScript bundle exports pass (exit 0). Results are recorded in `validation-experience-export.txt`.
- Release packaging excludes instance storage, IP/activity databases, passwords, keys, repository metadata, caches and dependencies. Runtime files are verified against the release manifest and ZIP contents.

## Deployment and limits

Follow `PYTHONANYWHERE.md` and `ADMIN-SETUP.md`. Upload all server modules/templates/assets together, configure a server-side password and the trusted PythonAnywhere IP setting, and reload the web app. Installed phone apps must be rebuilt. No live deployment was performed during this update.

Real iPhone/Android keyboard, rotation, gesture and playback behavior needs physical-device acceptance testing. Bundle exports do not establish successful signed native builds. Website iframe ads cannot be detected or blocked as reliably as the native full-site observer. IP matches can reflect shared networks rather than identity. Site metrics are app-side, not an independent uptime monitor or a whole-machine utilization guarantee. A real multi-hour video soak remains unverified.

This report supersedes earlier test reports for the current source release.

Local admin form fix: switched the private-page referrer policy from `no-referrer` to `same-origin`, preserving the browser's same-origin form Origin without allowing opaque, external or different-port origins. Login and logout are covered at `http://127.0.0.1:8000`, with foreign/null origins still returning HTTP 403.
