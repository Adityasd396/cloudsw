# Solace 2026.11.18.4 — deployment and recovery

## Upload to the existing PythonAnywhere app

1. Before replacing the app, save the existing server ZIP/code and make a verified database backup. Preserve the existing `instance/` directory, `SECRET_KEY` environment value if configured, YouTube key and administrator password hash. These private files are not in either release ZIP.
2. Extract **Solace-pythonanywhere.zip** into the existing directory used by the WSGI import. Replace its modules and complete `static/` and `templates/` folders together. Keep the packaged `tools/` directory and `release.json`. Do not extract into a second nested release folder.
3. Install requirements in the existing virtual environment if needed, then Reload the app from PythonAnywhere's Web tab. The app remains a Flask WSGI app; do not run a development server in the console for hosting.
4. Check the static mapping points at this app's updated static folder. Refresh both phone browsers. Rebuild installed Android/iPhone apps from the updated mobile source; uploading the server ZIP does not update an installed app.
5. Verify the release and public assets, then optionally run the disposable two-user journey:

```text
python tools/verify_deployment.py https://aditya211.pythonanywhere.com --expected-version 2026.11.18.4
python tools/verify_deployment.py https://aditya211.pythonanywhere.com --expected-version 2026.11.18.4 --journey
```

The second command creates one temporary test room, checks chat/controls, and explicitly leaves both participants. It does not access real room chats or admin credentials. Separately log into the private panel and verify Lock panel. Existing admin logins need to sign in again after this security update; the saved password remains unchanged.

`/api/health` now reports the version/build, `ordered_playback_v1`, `safe_retries_v1` and a 1,800-second reconnect grace. A partial frontend/backend upload is rejected before the updated clients send mutations to an incompatible backend.

## Verified SQLite backup

Upload `tools/storage.py` before replacing the remaining files if the older server does not have it. Run from the app directory, choosing a NEW backup folder each time:

```text
python tools/storage.py backup --instance instance --output backups/solace-backup-20261114
python tools/storage.py verify --backup backups/solace-backup-20261114
python tools/storage.py prune --folder backups --days 7
```

The backup uses SQLite's online backup API, validates each copied database with quick_check and records SHA-256 checksums. It can capture committed WAL content. Room and private operations databases are individually consistent snapshots; they are not one cross-database transaction. Configuration files and secrets are intentionally excluded. Keep a separate protected copy of the existing secret/API-key/password-hash configuration, or keep its existing environment configuration.

For scheduled backups, use your hosting account's scheduled task facility with a unique date-based output directory. Configure the schedule in the hosting account; no external schedule was installed by this local change. Pruning removes only verified `solace-backup-*` folders older than the chosen age, with the exact recognized file set. Unknown files protect a folder from deletion.

## Restore and rollback

```text
python tools/storage.py restore --backup backups/solace-backup-20261114 --target restored-instance
```

Restore refuses an existing target and verifies the input before copying. Never restore over a live instance directory. Preserve the original directory; point a stopped/reloaded app at the restored files only after verification and restoring its ORIGINAL secret/configuration. The utility rotates the storage generation, so updated clients request a complete snapshot and can accept restored playback revisions. Admin sessions are revoked on restore; sign in again. Refresh/restart clients after code rollback or deployment.

For code rollback, keep the existing instance directory and replace public code/assets with the saved previous server package, then Reload and refresh clients. Current migrations are additive. The pre-update server archive is retained locally at `Solace-rollback-before-20261114.zip`; it contains public server files only. It restores the earlier UI and earlier room-expiry behavior. Prefer forward fixes when possible. A data rollback changes the recovery point and may discard newer chats; preserve the current instance separately.

## Capacity and monitoring

The server serializes room mutations with SQLite transactions, uses short snapshot reads, indexed lookups, a busy timeout and retryable 503 responses for storage contention. Requests with IDs keep receipts for 24 hours, pruned on subsequent successful mutations; final Leave removes that room's receipts. This supports safe short retries, not indefinite offline command replay.

The website and native client adapt polling to playing/paused state and back off on errors. Hidden web tabs stop polling; phones may suspend all work in the background. Explicit final Leave deletes public room data immediately. An abandoned room expires after all members stop contacting the server for 30 minutes, on the next API request. This is not indefinite background playback.

The private panel adds numeric drift/conflict/replay aggregates alongside request failures/latency and worker health. These observations can be incomplete during outages and are not a compatibility guarantee. Existing 30-day IP/activity and private chat-backup retention remains. The room screen explains retention. No notification permission or OS push notification is requested.

The release retains the current WSGI deployment. PythonAnywhere documents a separate [async Flask-SocketIO setup](https://help.pythonanywhere.com/pages/FlaskSocketIO/); adopting it requires a hosting change and was not silently enabled. Measure deployed request latency, storage-busy errors and reconnects before moving transport or database. This local workload test does not establish production capacity. The room database's existing journal mode is preserved: SQLite [WAL requires same-host storage and does not work over a network filesystem](https://www.sqlite.org/wal.html), so WAL was not forced onto the room database.

## Physical-device release gate

Use one iPhone and one Android phone for a three-hour run before claiming verified long-session reliability. Exercise audible playback permission, both users' controls, keyboard open/close, history reading, rotation/fullscreen, queue transitions, games, ad states, calls, Wi-Fi/mobile-data switching, background recovery and final Leave. Observe battery and heat. Automated time replay and desktop viewport simulation cannot verify those OS/device behaviors.

Use a new release version for changed code/assets. Reusing the same version is appropriate only for reproducing the same checked source; phone browsers may cache assets by their versioned URL.
