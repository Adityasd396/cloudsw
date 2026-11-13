# Update your existing PythonAnywhere app

Use `Solace-pythonanywhere.zip` for the server update. It contains the server files only. `Solace-release-source.zip` also includes the Android/iPhone source, build configuration, tests and documentation.

## Files to upload

Copy these from `release/` into the **existing application directory** on PythonAnywhere, replacing the corresponding files:

```text
app.py
room_game.py
admin_panel.py
setup_admin.py
requirements.txt
templates/index.html
static/app.js
static/enhancements.js
static/player-room.js
static/rooms.js
static/style.css
static/love.html
static/love.css
static/love.js
static/love-film.js
static/media/for-jaanu.mp4
static/fullscreen.js
static/session.js
static/player-overlay.js
static/game.html
static/game.css
static/game.js
static/game-launcher.js
static/room-experience.js
static/admin.css
static/admin.js
templates/admin.html
templates/admin-login.html
```

Preserve these relative paths. For example, upload `templates/index.html` into the server's `templates` folder, not beside `app.py`. The ZIP contents start at the application root, with no extra `release/` parent directory. The correct destination is the directory used by your existing WSGI configuration; do not create a second nested app folder.

Keep the server's existing `instance/` directory, database, API key and secret. Neither ZIP contains those private files. The new code creates missing database tables without requiring you to erase the database. Existing saved names remain.

If the Web tab defines a separate `/static/` mapping, make sure it points to this application's updated `static/` directory.

## Load the update

1. In the app's existing virtual environment, install `requirements.txt` if required: `pip install -r requirements.txt`.
2. Check the Web tab's WSGI configuration. It should import this `app.py` as `from app import app as application`, with the existing application directory on `sys.path`. Keep your existing environment/secret configuration. If it currently imports `flask_app`, uploading `app.py` alone will not change the module it loads.
3. Click **Reload** for `aditya211.pythonanywhere.com` on the **Web** tab. PythonAnywhere runs the app through WSGI; do not start `serve.py` or `app.run()` in a console for this deployment.
4. Refresh the app in both browsers/phones.

PythonAnywhere references: [Flask setup](https://help.pythonanywhere.com/pages/Flask/) and [reloading an app](https://help.pythonanywhere.com/pages/ReloadWebApp/).

## Confirm that the right backend is running

Open https://aditya211.pythonanywhere.com/api/health . Its response must include:

```json
"capabilities": ["room_leave_v2"]
```

If this field is missing, the old backend is still running. Recheck the upload directory, WSGI import and Reload step.

The latest shared-controls/game release also includes `shared_playback_v3`, `tictactoe_v1` and `chat_identity_v1` in `capabilities`. Upload **room_game.py beside app.py**; the backend imports it. Upload the entire packaged `static/` and `templates/` folders together, then reload. Missing the new module will prevent the server from importing. New database columns and the game table are created automatically; keep the existing instance directory.

Create a new room and join from a second device. Leaving on the first device must preserve the other participant's room. Leaving on the last device must delete it; opening the old invitation should then report that the room is not found. Retrying Leave is safe.

Closing a tab, losing connectivity or backgrounding a phone is different from tapping Leave. Abandoned rooms have a two-minute reconnect grace period and are removed on the next API request after expiry. Immediate deletion applies to the final explicit Leave.

## Installed phone apps

The mobile Leave-confirmation fix and patched build dependency are in `release/mobile/`. Rebuild and reinstall the standalone Android/iPhone apps to receive these client changes. Uploading the Flask files updates the server and browser interface, not an already installed phone binary. Do not upload `mobile/`, `node_modules/`, local `instance/`, or local secrets to the PythonAnywhere application directory.

## Shared controls, playlist and game update

Every joined participant can play, pause, seek, select/advance videos and manage the queue. The creator remains the room host for host transfer and clock/ad reporting. Automatic song-end requests use a playback-instance identifier, so simultaneous reports cannot consume two playlist entries, including when the same video appears twice.

The browser fullscreen button has an in-page fitted fallback when Safari cannot grant element fullscreen; this fallback fills the available browser viewport and keeps an exit control. It cannot hide browser chrome where the platform does not permit it. The native app retains its fullscreen layout.

Add to playlist now contains the manageable queue below search. The Play together/Game button opens a two-player tic-tac-toe board; spectators can watch, and moves synchronize through the server. Game state is removed with the room. New chat messages carry room-scoped sender identities, so your messages align right and incoming messages left, with consistent name colors. Older saved messages without sender identities remain readable as incoming history.

The rebuilt native apps have expanded domain filters, player-response JSON/XHR/fetch cleaning, sponsored-slot removal and faster available-Skip handling. They preserve video media and login endpoints. These filters cannot run inside the website's cross-origin YouTube iframe and do not guarantee zero YouTube ads. Both native platforms require rebuilding for the filter changes.

## Room experience and private stats update

Upload **all** current server ZIP files, including `admin_panel.py` (imported by the app), `setup_admin.py`, the three templates and the updated static files. The backend creates new reply/ad tables and columns automatically. The private panel stays disabled until you choose a server-side password using `python setup_admin.py`; follow `ADMIN-SETUP.md` for the hidden URL, PythonAnywhere IP setting and 30-day retention behavior.

The room update adds swipe/hold replies, host crowns, participant activity chips, temporary landscape/fullscreen chat bubbles, keyboard fitting and back-navigation guards. In-app ad alerts can come from any participant: the native phone observer reports detected ads automatically; web participants use the **Ad playing / Ad ended** button because the embedded player cannot reliably expose ad state. These are in-app overlays only, not iOS/Android push notifications. Installed phone apps need rebuilding.

## The /iloveyou surprise

Send `/iloveyou` as a complete chat message to open the love video and letter for everyone currently in the room. Each participant can close their own surprise. Joining a room does not replay old commands. The clip attempts to play with sound; phone browsers that require a gesture show a **Play with sound** button. Other room audio is muted locally while the surprise is open and restored on close; shared play/pause state is not changed by the surprise.

Upload all of the new `static/love*` files plus `static/media/for-jaanu.mp4`, the updated `static/style.css`, and `templates/index.html`. Preserve the `media/` subfolder. The video is included in both ZIPs. Native phones need a rebuilt app for the new command overlay; the video itself is served from the Flask server.

## Three-hour reliability and overlay update

Upload the new `static/session.js` and `static/player-overlay.js` together with the updated `app.py`, all packaged static files and `templates/index.html`. The template now loads these helpers; omitting them can break room startup. Use the complete server ZIP to keep versions together. See LONG-SESSION-REPORT.md for measured results and physical-device limits. Installed apps need a new build with the direct `expo-keep-awake` dependency; uploading web files alone does not update an installed app.
