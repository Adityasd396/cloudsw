# Solace 2026.11.20.2 — public upload cleanup

Removed the personal video prompt entirely from web/native clients, administrator controls, room snapshots, configuration and film-serving routes. Removed its letter, scripts, styles and template from public assets and generated packages. Other chat gestures and games remain available. Existing users, chats and settings are preserved; no schema migration is needed. Rebuild the native apps to remove the old client feature. Earlier release notes below are historical.

# Solace 2026.11.20.1 — consolidated settings and social experience

Personal preferences now have one Settings page; room management is inline on the Room page. Added authorized chat avatars, long-press reactions and privacy-aware receipts, compact mobile navigation, standalone friend games, in-app alerts and real Moments summaries. Migration 9 is additive. Upload the complete generated package, including companions.py; preserve instance data and secrets. See SOCIAL-EXPERIENCE.md and audit-results/companion-verification.json for behavior and verification limits. Physical mobile acceptance remains outstanding. Earlier notes below are historical.

Current release **2026.11.19.5** fixes Home/Profile duplicate actions and auth navigation, and resolves the 59 conflicted files against the verified prior release. See [NAVIGATION-CLEANUP.md](NAVIGATION-CLEANUP.md). Use the complete generated ZIP; preserve instance data and secrets. Earlier notes below are historical.

Current update **2026.11.19.4**: focused screens, persistent room navigation, centralized Settings and Open World community chat. See [UX-COMMUNITY.md](UX-COMMUNITY.md). Migration 8 is additive. Upload the complete generated release, including community.py; preserve existing secrets and instance data. Native apps need a rebuild. Earlier release notes below are historical.

Open World and safety foundation (2026.11.19.3): see [SAFETY-OPERATIONS.md](SAFETY-OPERATIONS.md) and [OPEN-WORLD-REQUIREMENTS.md](OPEN-WORLD-REQUIREMENTS.md). Named staff enrollment through setup_staff.py is required before public launch.

Current messaging/media release: [MESSAGING.md](MESSAGING.md), version 2026.11.19.2, migration 5.

Returning-user dashboard, guest profiles/history, friends and public/private invitations: see [RETURNING-USERS.md](RETURNING-USERS.md). The complete 2026.11.19.1 release requires migration 4 and a native rebuild for the mobile dashboard.

# Solace — current release 2026.11.18.4

A quiet place to watch together, chat and play. Settings → Chat theme offers Solace, Rose, Moonlit ocean and Secret garden, saved per device. Games include agreed match options, cooperative Hoops, quick Ludo and tic-tac-toe series. Ludo now uses a larger board, sculpted pawns, a large rolling 3D die and one-tap moves. Hold to preview; optional single-legal-move automation is in its separate Match settings screen. Watch, video search, queue, games and room details each have their own screen. Four main destinations keep the watch screen quiet: Watch, Queue, Games and Room. Add video is inside Queue. `/iloveyou` is an optional admin-controlled moment; its personal name is anonymized and a licensed private film must be configured separately.

- Launch recommendation, ranked findings and measurements: [LAUNCH-READINESS.md](LAUNCH-READINESS.md)
- Public launch setup and blockers: [PUBLIC-LAUNCH.md](PUBLIC-LAUNCH.md)
- Upload package: **Solace-pythonanywhere.zip**
- Full source: **Solace-release-source.zip**
- Streaming measurements and limitations: [STREAMING-AUDIT.md](STREAMING-AUDIT.md)
- Current verification: [HARDENING-REPORT.md](HARDENING-REPORT.md)
- Upload, backup, restore and rollback: [DEPLOYMENT-RELIABILITY.md](DEPLOYMENT-RELIABILITY.md)
- Rebuild checked release artifacts: `python tools/build_release.py --version 2026.11.18.4`

Preserve instance/ and server configuration when updating. Physical Android/iPhone and deployed-server acceptance checks remain required. The earlier project reference follows.

---

# Solace

A place, comfort and peace.

With love, made for Jaanu. ♡

For cloud hosting and installed Android/iPhone builds without Expo Go, see [DEPLOYMENT.md](DEPLOYMENT.md).

A Flask and Python YouTube watch-party app with shared rooms, live chat, collaborative queues, invite links, and host-controlled playback synchronization.

## Android and iPhone client

The full-YouTube-site phone experience is in [`mobile/`](mobile/README.md). It uses a native WebView loading the mobile YouTube website directly, not an iframe. Double-click **start-mobile.bat** in this folder to start the phone room server and Expo QR preview. Install Expo Go on both phones, connect to the same Wi-Fi, and scan the QR code. The room server address is filled automatically. Create a room on one phone and join with its room code on the other.

The browser version below still uses YouTube's official iframe. The native phone client avoids that iframe requirement, but cannot guarantee playback of every YouTube video. Phone playback and cross-device sync require real-device verification; successful code checks and bundle exports alone do not establish that they work on every phone.

## Run

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```

Double-click `start.bat` to launch with Waitress, or run `python run.py` after installing dependencies. Open http://127.0.0.1:8000. Create a room, then share its URL. For local testing, open that URL in a separate browser or private window to join as another person. Tabs in the same browser share a participant identity.

To let devices on your network connect, use a production WSGI server:

```powershell
.venv\Scripts\waitress-serve --host=0.0.0.0 --port=8000 app:app
```

Use your computer's LAN address in the invitation. For internet access, deploy to a Python-capable host with HTTPS and persistent storage for `instance/`. Set `SECRET_KEY` in the environment and configure `SESSION_COOKIE_SECURE=True` when serving exclusively over HTTPS. The Sites project reserved before the Flask framework selection is unpublished; it cannot host this Python backend.

## Behavior

### Connect YouTube search

Under Explore YouTube, click **Connect / change key**, paste your YouTube Data API key, and click **Connect YouTube**. The app validates it with Google before saving it to ignored `instance/youtube.key`. It works immediately without restarting. Setup is available only through localhost on the server computer. The key is never returned to room participants. Saved keys take priority over environment variables. After setup, the panel stays hidden and replacement through the web API is disabled; rotate a key directly on the server if needed.

Search failures explain invalid keys, disabled APIs, restrictions, exhausted quota, and connection failures. Never put your real key in this README or in browser JavaScript.

### Playlist order

Hosts can use the up and down arrows beside each playlist item to change playback order. The order is saved in SQLite, appears for all participants, and controls what Next plays. Everyone can add videos; only the host can reorder, remove, or play them.

### Browse inside the app

Explore YouTube below the player has featured video cards, category filters, Watch and Queue buttons, and a search box that also accepts YouTube links. Without configuration, keyword searches filter the featured collection. To enable full YouTube searches, enable YouTube Data API v3 in Google Cloud, create an API key restricted to that API, and set it on the server before starting:

```powershell
$env:YOUTUBE_API_KEY = 'your-api-key'
python app.py
```

The key stays on the Python server. Search uses the official YouTube search endpoint, requests embeddable videos, caches results for five minutes, and supports loading additional results. API quotas apply. Featured links can become unavailable over time; use another video when YouTube disallows playback. YouTube's full website cannot be browsed inside its video iframe; the app supplies the browsing interface around the official player.

- SQLite persists rooms, the last 100 displayed chat messages, and video queues. The database and session signing secret are created under ignored `instance/`.
- Guests poll every two seconds for messages and room state. The host sends playback updates on play/pause and every five seconds while playing. Guests correct drift beyond three seconds. This is approximate synchronization, not frame-accurate streaming.
- The host controls playback and queue removal; everyone can chat and add videos. The host identity is tied to their browser session. Open People to transfer hosting to another participant. After the host disconnects for 30 seconds, another participant can become host. Account recovery is not implemented.
- YouTube's official embedded player streams the video. No API key is required for adding links. YouTube may block autoplay, ads can interrupt sync, and some videos disable embedding. Click the player to enable playback or choose another video.
- Invite links grant room access to anyone who can reach the server. This initial version uses guest names, not verified accounts. Keep deployments small and trusted until authentication and deployment-level abuse controls are added.

## Checks

```powershell
python -m unittest discover -s tests -v
```

