# Afterglow

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

