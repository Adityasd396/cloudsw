# Private Solace panel — one-time server setup

The panel has no button or link in the normal app. It is disabled until you set a password. There is no default password and no password-setting endpoint on the website. Nothing in this feature registers push notifications or asks for phone notification permission. Ad alerts are temporary overlays inside an open room only.

## 1. Upload the complete server update

Extract `Solace-pythonanywhere.zip` into the **existing** application directory, preserving folders. In particular, upload `app.py`, `room_game.py`, **`admin_panel.py`**, **`setup_admin.py`**, `templates/` and `static/`. Keep your existing server `instance/` directory and secrets. Never upload your local instance directory.

## 2. Choose the admin password on PythonAnywhere

Open a Bash console in your existing application directory, with its normal virtual environment active, and run:

```text
python setup_admin.py
```

Enter a private password of at least 14 characters and confirm it. Input is hidden. The script stores only a scrypt hash in `instance/admin-password.hash`. It also copies still-existing messages from the last 30 days into the private chat backup; it cannot recover messages that were already deleted before this update. New successful chat messages are backed up automatically.

The script refuses to overwrite an existing password. Do not send your password in chat, put it in client files, or upload the hash publicly. For deliberate rotation, replace the server hash through your server-owner workflow; changing it invalidates existing admin sessions. As an advanced alternative, a server-only `SOLACE_ADMIN_PASSWORD_HASH` environment variable can supply an already generated password hash.

## 3. Enable accurate PythonAnywhere visitor IPs

In your PythonAnywhere **Web → WSGI configuration file**, immediately after the app import, add:

```python
from app import app as application
application.config['OPS_TRUST_X_REAL_IP'] = True
```

Use this setting only on PythonAnywhere, whose load balancer supplies the trusted `X-Real-IP` header. On other hosts, leave it off unless your own proxy guarantees that header. Otherwise the panel uses the WSGI remote address. Do not trust an arbitrary client-supplied forwarded header. See [PythonAnywhere's client-IP documentation](https://help.pythonanywhere.com/pages/WebAppClientIPAddresses) and [Flask's proxy guidance](https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/).

Keep the existing WSGI path and secret configuration. If you already wrap the app in middleware, set the Flask config before wrapping it. Click **Web → Reload** afterward.

## 4. Open the hidden panel

Visit **https://aditya211.pythonanywhere.com/ops/solace** and enter your chosen password. Access is HTTPS-only for remote devices. No normal room UI exposes this URL.

The panel provides:

- Site/server status, a room-database check, active rooms/members, recent request/error counts, handler timing, worker uptime and CPU average, and platform-provided host load where available.
- Guest display names, opaque session identifiers, IPs, active/inactive/offline status and room join/leave times. Solace does not have account login authentication; offline is inferred after 15 seconds without requests.
- Exact matching public-IP groups. Shared Wi-Fi, VPNs and carrier networks can produce matches; they are not proof of identity.
- A password-protected JSON chat-backup download and recent activity events. IPs and private logs are not included in public room responses.

Admin sessions expire after 30 minutes. Login is CSRF-protected and rate-limited to five failed attempts per IP in a 15-minute window. The panel and backup responses are not cacheable or frameable. Metrics describe this application/worker; a shared hosting machine's load is not a dedicated-server utilization measure.

### Local login reports a cross-origin error

Use the current `admin_panel.py`, restart the local server and open a fresh GET of `http://127.0.0.1:8000/ops/solace`. The updated panel uses `Referrer-Policy: same-origin`. The previous `no-referrer` header could make a browser's HTML login/logout form send `Origin: null`, which was correctly rejected by the origin guard. A new page load is needed so the browser discards the old form policy. Do not disable the origin guard or allow arbitrary `null` origins. Password and CSRF checks remain required.

## Storage and retention

Private records are stored in `instance/solace-admin.db`, separate from the room database. The visible/exportable window is **30 days**. Older records are pruned on requests, with pruning limited to about once an hour; an idle site's files are pruned when requests resume. A room's explicit last Leave still deletes its room records immediately, while the private chat-backup copy remains for the retention window.

Keep instance storage writable by the server user and protected from public file serving. Neither release ZIP contains passwords, API keys, the private database or your local instance files. Notification delivery, email and external analytics services are not used.
