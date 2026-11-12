# Update your existing PythonAnywhere app

Use `Solace-pythonanywhere.zip` for the server update. It contains the server files only. `Solace-release-source.zip` also includes the Android/iPhone source, build configuration, tests and documentation.

## Files to upload

Copy these from `release/` into the **existing application directory** on PythonAnywhere, replacing the corresponding files:

```text
app.py
requirements.txt
templates/index.html
static/app.js
static/enhancements.js
static/player-room.js
static/rooms.js
static/style.css
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

Create a new room and join from a second device. Leaving on the first device must preserve the other participant's room. Leaving on the last device must delete it; opening the old invitation should then report that the room is not found. Retrying Leave is safe.

Closing a tab, losing connectivity or backgrounding a phone is different from tapping Leave. Abandoned rooms have a two-minute reconnect grace period and are removed on the next API request after expiry. Immediate deletion applies to the final explicit Leave.

## Installed phone apps

The mobile Leave-confirmation fix and patched build dependency are in `release/mobile/`. Rebuild and reinstall the standalone Android/iPhone apps to receive these client changes. Uploading the Flask files updates the server and browser interface, not an already installed phone binary. Do not upload `mobile/`, `node_modules/`, local `instance/`, or local secrets to the PythonAnywhere application directory.
