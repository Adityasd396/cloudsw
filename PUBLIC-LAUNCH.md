Open World and safety update (2026.11.19.3): see [SAFETY-OPERATIONS.md](SAFETY-OPERATIONS.md) and [OPEN-WORLD-REQUIREMENTS.md](OPEN-WORLD-REQUIREMENTS.md). Upload the complete generated release; keep existing secrets/instance data. Named staff enrollment through setup_staff.py is required before public launch.

Current messaging/media release: [MESSAGING.md](MESSAGING.md), version 2026.11.19.2, migration 5.

Returning-user dashboard, guest profiles/history, friends and public/private invitations: see [RETURNING-USERS.md](RETURNING-USERS.md). The complete 2026.11.19.1 release requires migration 4 and a native rebuild for the mobile dashboard.

# Public launch configuration

This update uses the existing Flask, SQLite, Werkzeug and Waitress stack. Additive, idempotent migration versions 1–4 adds accounts, revocable sessions, settings and private history to the existing database. Back up instance/ before deployment; never replace its secret or databases with a release file.

Required before public launch:

- `SOLACE_PUBLIC_URL=https://your-production-domain` — HTTPS origin only, no path or trailing query. This controls canonical URLs, social previews, sitemap and indexing. Until configured, public pages are noindex, robots disallows crawling and sitemap returns 503. Never derives SEO URLs from request Host.
- `SOLACE_SITE_NAME=Solace` — optional site/SEO branding.
- `SOLACE_CONTACT_EMAIL=your-support-address` — publish a monitored operator contact. No contact or legal identity is invented by the app.
- A stable `SECRET_KEY`, HTTPS and persistent instance/ storage. Existing installations retain their saved secret. Enable `COOKIE_SECURE=1` in the supplied HTTPS production entrypoint. Trust proxy headers only behind the actual trusted proxy.
- Install the updated requirements inside the application's virtual environment: the pinned requirements.lock (including Pillow 13.0.0 and tzdata). No account SaaS credentials are needed. The existing `YOUTUBE_API_KEY`/saved server key remains necessary for full YouTube search.

Accounts use email/password with scrypt hashes, 12–128 character passwords, server-side revocable random session tokens stored only as hashes, 30-day expiry, secure/HTTP-only/Lax cookies on HTTPS, CSRF checks, generic credential errors and persistent per-IP limits. Signout rotates the guest identity. Registration in the current browser upgrades its guest identity and watch history; signing in to a different existing account does not merge unrelated guest history. Profile avatars are private database blobs, limited to still JPEG/PNG/WebP under 2 MiB/16 MP, re-encoded to a metadata-free 256px PNG. Keep Pillow patched.

Public pages are rendered by Flask/Jinja with crawlable content. Only Home, Features, How It Works, About, FAQ, Contact, Privacy and Terms enter the sitemap. Account/history/room/API/admin routes use no-store and noindex headers and server-side authorization. Search directives do not replace authorization. The generated social preview is a local 1200×630 brand illustration, not a product screenshot or testimonial.

## History measurement

Web and native players send separate samples about every 15 seconds while a room exists, with earlier samples when local playing status changes. A session begins on an actual visible, decoded-playing sample, with matching server room intent. Consecutive active samples no more than 25 seconds apart credit elapsed seconds. Pauses, buffering, hidden screens and long disconnects are conservatively excluded. One history entry per owner/room/playback instance prevents reconnect duplicates. Video URL query/fragment tokens are stripped. Companions are display names only. Account deletion anonymizes a participant in others' history; no emails or stable participant identifiers are returned.

History remains after room deletion until the owner removes it or deletes their account. Deleting an entry suppresses the same ongoing playback so polling cannot recreate it. Daily graphs split duration at local midnight in the selected IANA timezone and label session starts separately. Histories are private. Unclaimed guest history expires after 30 days during request-driven cleanup and becomes visible after registration. No attention-tracking guarantee is implied.

Existing private operations diagnostics/chat backups remain at their disclosed 30-day retention. No covert fingerprinting, permission bypass, cross-site tracking, contacts, camera or microphone collection was added. Account deletion removes the account, picture and owned history but not other users' shared chat or existing operational backups; the published Privacy page explains this and contact-based requests. Decide and publish a backup rotation policy before launch.

## Optional love moment

The personal film was removed from static/ and is excluded from both launch ZIPs. A local preservation copy is under .openai/private-love/ and is not packaged. **On an existing host, remove the old `static/media/for-jaanu.mp4` before opening the launch to the public**, especially when PythonAnywhere serves static files directly. Also remove any legacy static love page if a previous static mapping exposes it. Flask now rejects those legacy paths, but it cannot intercept a reverse proxy's direct file response.

The private admin panel has an Enable /iloveyou switch. It defaults off. To use it, supply an appropriately licensed, non-personal MP4 outside every public/static directory using `SOLACE_LOVE_VIDEO=/absolute/private/path/film.mp4`, then enable the switch. Only current room participants can request /love and /love/film; Range playback is supported and responses are no-store. Turning it off blocks new prompts and closes an open moment on the next room snapshot. Existing romantic copy is retained apart from anonymizing the personal name.

## Remaining launch gates

- Review the factual Privacy/Terms drafts for the operator's jurisdiction, publish its legal identity/contact, decide eligible age/audience, and document backup deletion/retention. These are product/legal decisions, not claims of compliance.
- Email ownership verification and one-use password recovery are implemented. Configure and validate the SMTP environment variables before broad launch. Delivery, DNS/domain authentication and real inbox behavior could not be tested without credentials.
- Run deployed HTTPS acceptance and real Android/iPhone keyboard, sound, haptics, fullscreen and sustained playback tests. Local simulations and platform exports cannot certify physical devices.
- The standalone native app includes a separate account WebView sheet, shared-cookie support and native watch-history sampling. Rebuild both native apps. Shared-cookie handoff, account switching and haptics still need real-device acceptance; no physical devices were available.
- No promise of ad-free playback, all-video availability, Netflix DRM or SEO rankings is made.

Security references used: [Flask web security](https://flask.palletsprojects.com/en/stable/web-security/), [Pillow image validation and pixel limits](https://pillow.readthedocs.io/en/stable/reference/Image.html).

## Local verification

99 Python tests, 66 client tests and 61 HTTP smoke assertions passed. Type checking and both platform exports succeeded. The new browser journey exercised actual synthetic playback, shared hugs, guest upgrade preserving history, private picture/name edits, activity graph/history deletion and signout. Existing keyboard/sync/game journeys passed with live admin on/off coverage. Docker COPY/import regression passed; no Docker engine, real phones or production deployment was available.

Current release: 2026.11.18.4. See LAUNCH-READINESS.md for the ranked launch decision, latest evidence, quotas, security findings and operating procedures.

## Email and storage configuration (2026.11.18.4)

Use SOLACE_ENV=production, SOLACE_REQUIRE_EMAIL=1, SOLACE_SMTP_HOST, SOLACE_SMTP_PORT (587 by default), SOLACE_SMTP_SSL=0 for STARTTLS or 1 for implicit TLS, SOLACE_SMTP_USERNAME, SOLACE_SMTP_PASSWORD and SOLACE_MAIL_FROM. SMTP always uses certificate-validated TLS. Supply credentials only in the server environment. Links use the configured production origin and put tokens in the fragment, then clear it from the browser URL. Reset links expire after 30 minutes, verification after 24 hours; only hashes are stored. Reset revokes all account sessions. A limited launch can explicitly use SOLACE_REQUIRE_EMAIL=0; the UI reports unavailable delivery rather than claiming success.

Private admin → User storage limits controls the 50 MiB default and 1–1024 MiB individual overrides. Use the private support reference to distinguish equal display names; no participant emails are exposed there. Resetting an override restores the current default. Usage covers logical profile/history payload, not shared chat, operations archives or physical database/index overhead. Over-limit users retain read/delete access; new history/uploads pause, with no playback/chat/game control effect. Guests have the same default and retain overrides when registering. Watch quota checks and history changes are transactional. Account pages display usage and limit; the private ops panel separately shows physical DB size/free disk.

Install requirements.lock in the deployment virtual environment, including Pillow 13.0.0. Do not use a stale image library: new uploads reject it. Run owner maintenance hourly and backup retention on the reviewed schedule. Automatic request-driven cleanup does not guarantee erasure while an app is completely dormant. No secret, film or credential is bundled in .env.example.
