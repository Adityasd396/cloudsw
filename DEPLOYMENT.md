# Server deployment and standalone phone apps

The Python server and installed phone apps are separate deliverables. A server runs Flask, room state, chat, playlists, and synchronization. Android and iPhone apps run the full YouTube website in a native browser view. Uploading the server does not turn the phone client into a browser website.

## 1. Deploy Flask

Use a Python host or the included Dockerfile. Start command: `python serve.py`. The server listens on `0.0.0.0` and the host-provided `PORT` (8080 by default). Terminate HTTPS at your hosting provider or reverse proxy.

Mount persistent writable storage at `/app/instance` in the Docker image, with ownership writable by UID 10001. This stores the SQLite database and optional locally configured YouTube API key. Set a long random `SECRET_KEY` in the host's secret settings. Do not upload your local `instance/` folder or its secrets.

`COOKIE_SECURE=1` is enabled by default for HTTPS deployments. For a temporary local HTTP container test only, use `COOKIE_SECURE=0`. If the service is reachable **only through one trusted reverse proxy**, set `TRUST_PROXY=1` so Flask recognizes the forwarded HTTPS scheme and host. Otherwise leave it unset.

Health check: `GET /api/health`. No API keys or session secrets are returned.

The SQLite backend is intended for one server instance with a persistent local disk. Do not scale replicas with separate SQLite files. Before an unrestricted public launch, add account authentication, invitation controls, operational monitoring, backups, and deployment-level rate limits. Existing guest rooms are for trusted groups.

## 2. Build installed apps—no Expo Go

From `mobile/`:

```text
npm ci
npx eas-cli login
npx eas-cli build --platform android --profile preview
```

The preview profile creates a signed installable Android APK with the JavaScript bundle inside. It does not need Expo Go, Metro, a QR preview, or your development computer. You can put the APK download on your HTTPS server.

For iPhone internal testing:

```text
npx eas-cli build --platform ios --profile preview
```

iPhone internal builds require an Apple Developer account and registered test devices. For wider iPhone distribution, build with `--profile production` and distribute through TestFlight or the App Store. Uploading an arbitrary IPA to a website is not a general iPhone installation method.

For Android Play Store distribution, use `--platform android --profile production` to create an AAB.

Expo's framework remains part of the app's implementation; **Expo Go is not installed or required by these standalone builds**. Cloud builds require your Expo account and platform signing credentials. No signed APK/IPA is included until you complete that account setup and build.

## 3. Set the server address later

The room server field remains editable on the phone setup screen. Once you choose the domain, enter the same public **HTTPS** URL on both phones. You can also set `EXPO_PUBLIC_API_URL` in the build environment before building to prefill it. That value is public, not a secret; never put YouTube API keys or credentials in `EXPO_PUBLIC_` variables.

Standalone release profiles block unencrypted Android backend traffic and retain default iOS HTTPS transport protection. The development launcher still supports local Wi-Fi HTTP for testing.

## 4. Video layout and ads

The top half switches to a player-focused view when a video opens. The entire YouTube player is fitted into that space, including its own controls and any ads. **Browse** returns to the full website. **Expand** gives the player more screen space; **Chat** restores the split layout.

Ad filtering is enabled by default, with an **Ad filter on/off** control in the player toolbar. Toggling reloads the current page. The preference is saved on the phone.

The standalone apps use Android resource-request filtering and Apple WebKit content rules to block a bundled set of ad/tracker domains. Page filtering also removes known ad fields from YouTube player responses, hides sponsored ad slots, and clicks YouTube's Skip button when it becomes available. Ordinary video-stream domains, thumbnails, and Google authentication domains are not blocked.

This is a small maintained filter implementation, not Brave's browser engine or its complete filter ecosystem. It does not guarantee removal of every YouTube ad: first-party or server-inserted advertising and YouTube changes can defeat filtering or cause playback errors. If playback breaks, turn filtering off. No private-video, age, region, account, payment, or DRM controls are bypassed.

Native filters require **new standalone builds**. Expo Go uses its own precompiled WebView, so it can only exercise the page-level filter. Native Android/iPhone compilation and actual device behavior are not verified on this Windows machine.

`npm ci` runs `scripts/install-content-blocker.cjs` to integrate the filters into the pinned `react-native-webview` version 14.0.1. This step is deterministic and refuses unknown native source layouts. Keep that postinstall step in cloud builds; review the integration before upgrading WebView. Filter definitions are in `mobile/blocker.cjs` and require rebuilding after changes.


## Rooms, saved data, and presence

New rooms use six-digit numeric codes; invitations from older 12-character prototype rooms remain valid. The code appears beside the room name and can be copied. Room codes grant guest access, so share them only with your group.

Chat messages and participant display names are stored in SQLite. A saved profile is associated with the device's long-lived signed session; mobile/browser preferences also remember the display name. There is no cross-device account identity or account recovery. Keep the same persistent instance storage and SECRET_KEY when redeploying to retain sessions and data.

Typing indicators refresh while a participant types, exclude the current viewer, and expire after four seconds without a refresh. Sending a message clears typing state. Emoji reactions support joined emoji, skin tones, and flags; the mobile client animates extracted emoji, and the browser provides an expanded emoji picker plus chat/video animations.

YouTube API setup is a one-time server operation. Once a key is saved, the setup panel disappears from the web interface and the setup endpoint rejects replacement requests. For later key rotation, replace the server-side secret deliberately and restart the server. Never bundle secrets into the client. The native phone client browses the YouTube website without this search API key.

The web browser still uses YouTube's iframe player and remains subject to uploader embedding restrictions. It cannot be turned into the native full-website browser by uploading the same files to a server. The installed Android/iPhone client must be rebuilt to receive native updates. Neither code checks nor bundle exports establish 100% compatibility; native builds and two-device playback require testing on real Android/iPhone hardware.


## Simplified interface

Room creation now asks only for a display name and generates a room code. Room names are no longer displayed or requested. The custom Explore YouTube section and all Add to playlist entry points have been removed. Existing saved playlists remain viewable and reorderable. On phones, YouTube browsing is still available inside the native YouTube view.


## Chat and mobile controls update

Chat and typing state refresh every 500 ms while active; network and server latency add to this interval. Video titles use 10px text. Joined participant names appear below the chat. Inline video-link entry is available in the playlist on both interfaces. The native toolbar also offers Add current video and Playlist, with up/down, play and remove controls for hosts. No modal dialogs are used for these actions. Installed phone builds must be rebuilt to receive this update.


## Focused room layout

Connected rooms hide the header and use a fixed-screen video/chat layout with active names at the bottom. Only the chat, queue, and selection page scroll internally. Host controls provide ten-second rewind/forward, play/pause, and fullscreen/exit fullscreen. Creating a room opens video selection. In the native phone app this is the full YouTube site in a separate view; Add to playlist reopens that view and selecting a video saves it once, closes the picker, and returns to chat without replacing the current video. The browser uses the configured YouTube search API for its inline selection page because it cannot embed the full YouTube website. Native click/navigation behavior still requires real-device verification.


## Minimal home and playback isolation

The initial web and native home screens expose only Create room and Join room. Required setup fields appear after selecting an action. Native Leave room returns to the two-option home. Playback updates use a dedicated compact API response and an independent client request path; they do not queue behind chat sends or carry chat history. Video media comes directly from YouTube. Network round-trip time, shared bandwidth, buffering, server write contention, and geography can still affect synchronization; zero-latency or distance-independent playback is not guaranteed.


## Shared control permissions

Every joined participant can now play/pause, seek, select a video, add songs, advance, reorder, and remove playlist items. Unjoined callers are still rejected. A single internal clock publisher is retained to avoid competing automatic updates; this does not limit participant controls. Automatic clock samples include an expected state timestamp and are rejected if another participant changed playback since that state. Explicit user controls take priority over stale automatic samples.


## Activity colors and long sessions

Dots before each participant name use green for a current heartbeat (under 2.5 seconds), yellow for delayed updates (2.5–8 seconds), and red for explicit inactivity or no heartbeat for 8 seconds. Closing/backgrounding reports inactivity when the platform permits; abrupt network loss is detected by timeout. A quiet viewer with a healthy connection stays green.

Long-session changes reduce heartbeat disk writes to at most once per second per participant, cap pending user commands at 12, and keep fetched chat history to the most recent 100 messages while retaining all messages in SQLite. Playback requests remain independent of chat commands. Automated tests cover a simulated three-hour timeline, saved history, shared controls, and presence transitions. This is not a real-time video soak test: continuous playback and recovery still require testing on real Android and iPhone devices and the chosen host. Network loss, platform suspension, hosting limits, and YouTube restrictions can interrupt playback.


## Creator-host and streamlined room update

Every joined participant can now control playback, seek, add videos and manage the queue. The creator remains the host for host transfer and clock/ad reporting. Tap an active participant name to transfer hosting. The room code plus Share link and Invite friends are visible at the bottom. Create room asks only for a display name and a create button. The emoji reaction strip is hidden; typed emoji (including flags, skin tones, joined sequences, and keycaps) animate on receipt.

The resume fix prevents host polling from enforcing an older paused state on the local host player. Guests follow the shared state. Host-ad notices rely on the native full-site observer detecting known ad indicators; the YouTube iframe API does not provide reliable ad detection, so browser-host ads cannot be reliably announced. Notices expire after ten seconds without renewal. Input font sizing avoids common iPhone focus-zoom behavior without disabling user-controlled pinch zoom. Real iPhone/Android player behavior still needs device verification.


## Playback resume race fixes

Deliberate play/pause/seek commands take priority over observer samples for three seconds. Native queued heartbeat samples cannot replace pending explicit commands, buffering/seeking samples are not published as pauses, and blocked autoplay is surfaced for a user tap instead of broadcasting a false pause. Web explicit controls are serialized separately from heartbeats. Guests apply drift correction beyond 1.25 seconds and avoid concurrent play promises. Host polling does not enforce previous remote play/pause state on the local authoritative player. Automated regressions cover stale pause after Resume, delayed command responses, guest pause/resume/seek, and repeated play attempts. Actual iOS/Android playback permission, network and buffering behavior still need real-device testing.


## Empty-room lifecycle

The Leave button removes the current participant. When the last participant explicitly leaves, the room, messages, queue, typing, presence, and ad-status records are deleted transactionally. Saved display-name profiles remain. If the host leaves while others remain, hosting passes to a remaining participant. Backgrounding, refresh, and closing only report inactivity; they do not immediately erase the room. If every participant stops sending heartbeats, the room expires after two minutes and is cleaned on the next API request. Reconnecting within the grace window preserves it. Clients return to the home screen when an expired room returns 404.


## Solace shared-playback/game update

See PYTHONANYWHERE.md and UPDATE-REPORT.md for the 13 November update. Upload room_game.py beside app.py and replace static/ and templates/ together. Rebuild installed phone apps for shared controls, sender bubbles, game UI and stronger native filters. The queue is inside Add to playlist below search. The website cannot apply native ad filters to YouTube iframe traffic.
