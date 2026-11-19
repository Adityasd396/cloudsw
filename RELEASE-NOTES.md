# Solace 2026.11.19.5 — Home/Profile navigation and merge recovery

Resolved 144 merge hunks across 59 files against the verified 2026.11.19.4 source, with originals backed up. Home/Friends/Rooms now render and fetch only their own sections. Removed redundant profile and room-return actions, corrected Privacy settings, made verification/picture actions contextual, and consolidated embedded auth navigation. Guest upgrades keep the player; sign-out cancellation does not leave the room. Packaging rejects merge markers and invalid Python/JSON. No new migration or credentials. See NAVIGATION-CLEANUP.md and audit-results/navigation-verification.json.

# Solace 2026.11.19.4 — seamless room navigation and community

Home, Messages, Open World and Settings now open as separate surfaces while the current player and room transport remain mounted. Games retain their existing room integration. Ordinary navigation has no room-change dialog; explicit leave/replacement actions do. A compact Return to room action keeps the destination clear. Settings centralize experience, notification, privacy and sharing controls with accessible compact switches.

Open World is now a shared persisted text/picture/GIF chat for recognized guests and accounts. Participation is explicit, with a once-only optional introduction, quiet browsing, mutable saved preferences and unique eligible online counts across tabs. Existing blocks, moderation, reporting, quotas and upload validation apply; DMs remain restricted to accepted friends. Community history is pruned after 30 days or beyond the newest 10,000 messages; see UX-COMMUNITY.md for cleanup and presence timing limits. Migration 8 is additive. Existing streaming, games and /iloveyou remain intact.

Local evidence and engine-specific limits are recorded in audit-results/community-verification.json. Physical iPhone/Android testing and existing public-launch operational gates remain outstanding. No production deployment was performed. Upload the complete generated PythonAnywhere ZIP; community.py is required. Earlier release notes follow.

Open World and safety update (2026.11.19.3): see [SAFETY-OPERATIONS.md](SAFETY-OPERATIONS.md) and [OPEN-WORLD-REQUIREMENTS.md](OPEN-WORLD-REQUIREMENTS.md). Upload the complete generated release; keep existing secrets/instance data. Named staff enrollment through setup_staff.py is required before public launch.

Current messaging/media release: [MESSAGING.md](MESSAGING.md), version 2026.11.19.2, migration 5.

Returning-user dashboard, guest profiles/history, friends and public/private invitations: see [RETURNING-USERS.md](RETURNING-USERS.md). The complete 2026.11.19.1 release requires migration 4 and a native rebuild for the mobile dashboard.

# Solace 2026.11.18.4 — launch hardening and user storage controls

Public pages, guest-compatible accounts, private profiles/pictures, measured watch history and daily activity are implemented. Email verification/recovery use expiring one-use tokens and TLS SMTP; credentials and real inbox acceptance are still required. The admin panel controls the optional love moment and default/per-user storage limits. Quotas preserve existing data and never stop streams, chat or games.

Fixed upgraded-guest authority, transactional history deletion, restored-session revival, Docker context omissions, unrelated-game resets and private key-file creation. Pillow is pinned to the verified 13.0.0 security update. Added production configuration/readiness, request IDs/safe structured logs, HTTPS handling, bounded Waitress settings, shutdown, maintenance and CI definitions. Private dedication and the personal public film are removed.

Verification: 99 Python tests, 66 client tests, 61 HTTP smoke assertions; type checks, JavaScript syntax and Android/iOS exports. Chromium real-media/account/game journeys and WebKit account/keyboard checks pass. Two-minute direct-video soak p95 drift improved from 1.142 to 0.209 seconds; home local p95 DOMContentLoaded improved from 192.2 to 47.4 ms. A separate accelerated three-hour protocol replay passed. See [LAUNCH-READINESS.md](LAUNCH-READINESS.md) for measured API/startup overhead, test boundaries and raw evidence.

**Full public launch remains blocked:** real domain/SMTP/operator setup and device/deployed acceptance are missing; WebKit local HTTPS media remains unresolved; the native build toolchain has an unpatched picomatch advisory. Its source is absent from exported runtime bundles, but the CI audit gate remains red. No production deployment or public-load test was performed. [PUBLIC-LAUNCH.md](PUBLIC-LAUNCH.md) and [.env.example](.env.example) document setup, retention, backup/restore and rollback.

---

# Solace 2026.11.18.3 — public launch foundation

Public branding removes the personal dedication from UI, metadata and native descriptions. The personal film is outside static/ and excluded from the release; /iloveyou is optional, off by default and controlled by the private admin panel. Existing romantic copy is anonymized. Hug, kiss, cuddle, missing-you and cheering prompts now use three-second screen effects and a matching chat treatment without taking input focus or publishing playback commands.

Flask-rendered Home, Features, How It Works, About, FAQ, Contact, Privacy and Terms pages have centralized metadata, safe configured-origin canonical/social URLs, a local social image, structured data, robots and a public-only sitemap. Private pages and APIs use noindex/no-store plus server authorization. Missing production-domain configuration deliberately keeps indexing off.

Email/password accounts use scrypt hashes, revocable hashed session tokens, CSRF validation, persistent limits and 30-day sessions. Guests remain supported and registration upgrades their current identity/history. Private profiles support names, creation date and validated/re-encoded pictures. Watch history survives room deletion, deduplicates reconnects, strips URL query tokens, exposes only companions' display names, and has timezone-aware daily activity plus deletion controls. Account deletion revokes sessions and anonymizes the participant in companions' histories. Signing out leaves active rooms and rotates the guest identity. A pre-upgrade guest cookie cannot retain upgraded-account authority.

Native apps include a separate account sheet and playback history sampling. Physical cookie handoff, keyboard and haptics remain device acceptance gates. No covert fingerprinting or broad private-device collection was added. Existing bounded operations records and account security events are disclosed in the public policy and remain behind admin authentication.

Verification: 90 backend tests, 66 client tests and 61 HTTP smoke checks pass; native type checking and Android/iOS exports succeed. Two-user browser journeys cover real synthetic playback, guest upgrade, picture upload/removal, private history/graph/deletion, signout, three-second hug effects, keyboard models in portrait/landscape, all-game synchronization, queue advancement, shared dice and live admin disabling of the love moment. Tests use disposable data. Physical phones and production have not been tested or changed.

Read [PUBLIC-LAUNCH.md](PUBLIC-LAUNCH.md) before upload. Set SOLACE_PUBLIC_URL and SOLACE_CONTACT_EMAIL, preserve SECRET_KEY and instance/, and install the new Pillow/tzdata requirements in the app virtual environment. Remove the obsolete film from a previously deployed static directory. Legal/operator/contact review, email verification/recovery configuration, backup policy and deployed/device acceptance remain launch gates. No SEO ranking, provider availability or ad-free guarantee is made.

---

# Solace 2026.11.18.2 — shared reactions and streaming audit

Love, heart glitter and claps now give both participants a three-second screen effect. Effects respect reduced motion and existing haptic preferences. Ludo offers available player colors before the match starts, symbol pawns, a cute pip-only die and a large shared 3D result on game and streaming screens. /iloveyou dialogue and media are unchanged.

Fixed unnecessary room/game database writer contention, overlapping direct-media play attempts, stale pause/metadata races, non-seekable drift corrections, misleading late YouTube errors and missing Docker package modules. Existing data and streams are preserved.

Local audit: 81 Python tests and 65 client tests passed; native type checking and Android/iOS exports succeeded. Two-user browser checks cover effects, colors, public dice results, real synthetic playback, keyboard models, orientations, game independence and control synchronization. Physical phones, production and a real three-hour session remain untested. See [STREAMING-AUDIT.md](STREAMING-AUDIT.md) for measurements, failure cases, limitations and reproduction commands. Four-client room p95 was 122.599 → 36.094 ms; no media-delivery speedup is claimed.

Upload the complete Solace-pythonanywhere.zip contents together, preserving instance/ and server credentials. Reload the Web app and refresh both clients. Rebuild installed mobile apps for native changes. The source ZIP includes the audit report, disposable tests and raw results; audit endpoints are not production routes.

---

# Solace 2026.11.18.1 — Ludo table rebuild · 18 November 2026

Ludo now prioritizes the board: edge-to-edge phone layout, larger cream-and-pastel table, beveled frame, clearer safe stars, directional route markers, colored home lanes and a four-color finish. Sculpted pawn heads/bodies, highlights, shadows and offset stacks replace numbered dots. Visible pawn nodes stay mounted through polling and animations; large alternative move buttons remain available. The browser's Ludo iframe can use the full phone width. Native game pages already receive the full WebView width.

The ivory 3D die is 82px in portrait (76px landscape), with six correctly arranged pip faces, opposite faces totaling seven, recessed pips, shaded sides, a rolling tumble, table bounce and moving shadow. The server persists one identity/value for each roll and its timestamp. Both clients use that result and catch up to the same animation timeline; polling and reloads do not replay old rolls. No client-side random outcome is substituted. Pending requests have a short waiting motion and errors retain the authoritative result.

Tap a legal pawn once to move. Hold for a destination preview; releasing a preview does not move it. Pointer cancellation and scrolling cancel the gesture. Optional Auto move a single legal pawn is saved on the device, defaults off, and never rolls automatically. Pawn moves hop through the route, settle at their destination, show capture returns and brief safe/home moments. Animations are queued independently of authoritative state, timers are cleaned up, and reduced motion settles directly. Match length, soft sound and optional automation are in a separate Match settings screen, keeping the game surface quiet. Player avatars and the active turn stay visible.

Validation: 75 Python tests, the existing 62 client tests and 61 HTTP smoke assertions passed. New two-user Chromium checks observed all six die faces/results, actual roll animations, one-tap movement, hold/cancel previews, optional automatic movement, stable die/pawn nodes, no history replay after reload, and portrait/landscape/320px layout fit. Deterministic presentation fixtures cover capture and exact-home animations; server rule tests cover their legality separately. All-game two-user regression also passed, with ongoing room play/seek convergence inside the existing 1.5-second bound. The game-only journey leaves video, position, playing state, playback ID and playback revision unchanged. Physical Android/iPhone testing remains unavailable; browser layouts and input are simulated. Native source/bridge is unchanged and loads the updated shared game pages from the server. /iloveyou assets remain unchanged.

Deployment: upload the complete PythonAnywhere ZIP contents, including ludo_game.py and the new static/ludo-table.css, preserving instance/ and credentials. Reload the Web app and refresh clients. This is a local release and has not been deployed.

---

# Solace 2026.11.17.6 — games and chat themes

Love Hoops adds Together mode (eight combined goals), relaxed/challenging aim timing, original SVG bear/bunny mascots with reactions, shot rotation/arc/landing bounce, shadow movement, rim/net reactions and distinct swish/rim-kiss celebrations. Mode/difficulty changes require both players to agree. Existing shared live charging, streaks and cheers remain.

Little Ludo adds agreed two-pawn quick matches, shaded pawns, step-by-step movement with landing animation, destination preview plus confirmation, shared selection feedback and capture/home/safe-arrival effects. Classic four-pawn matches remain. Tic-tac-toe adds optional hearts/stars, animated marks, a winning line, single/best-of-three/best-of-five matches, series scores and alternating round starters. All games require mutual rematch agreement, retain state across temporary disconnects, use quiet optional sound (off by default), share cheers and respect reduced motion. Game actions remain separate from playback mutations. An orphaned tic-tac-toe roster no longer discards nested game state.

Settings → Chat theme offers Solace, Rose, Moonlit ocean and Secret garden in browser and native source. Choices persist locally and independently per device. Themes change chat surfaces and bubbles while preserving readable message text and timestamps. Native preference loading cannot overwrite a new choice, and writes are serialized. /iloveyou dialogue, trigger, presentation and original media remain unchanged from the preceding release.

Validation: 74 Python tests, 62 client tests, 61 HTTP smoke checks and TypeScript passed. Android/iOS bundles exported to mobile/.export-games-themes-nov17. Two independent browser participants verified series wins/round starters/mutual rematch, cooperative Hoops completion, shared cheers, quick Ludo roll/preview/confirmation/movement, saved distinct themes, reduced motion and portrait/landscape fit. The mounted streaming player remained present and two-user play/seek convergence stayed within a 1.5-second bound during games. The 12-cycle iPhone visual-viewport/Android resize keyboard test also passed with visible latest messages/times and no overlaps. Existing two-user live charge/cancel/cheer/Ludo regression passed. No physical phones were available: Safari/native keyboard feel, haptic intensity, OS audio focus, battery/heat and physical three-hour playback remain unverified. Browser sync tests use a simulated player with real room transport; the earlier real fixture-video queue test remains separate coverage.

Deployment: replace all server ZIP contents together, including the new game_options.py and complete static/templates folders. Preserve instance/ and existing credentials; reload PythonAnywhere and refresh clients. Installed native apps require rebuilding. The release is local and has not been deployed.

---

# Solace 2026.11.17.5 — compact watch controls

Restored a quiet Solace wordmark with a small heart above the stream. Portrait playback controls use smaller 44px rounded pills, softer lilac/rose colors and a highlighted play/pause button. Landscape controls retain their overlay behavior. The wordmark clears while typing or in fullscreen to keep space for chat/video. Native portrait controls include extra touch padding.

TypeScript passed. All 61 disposable HTTP smoke checks and 12 two-user portrait/landscape keyboard/sync cycles passed. Android/iOS exports succeeded in mobile/.export-compact-nov17; phone keyboard behavior remains simulated. Current preview images show the new design. The release packages include web and native source; native installations require a rebuild.

---

# Solace 2026.11.17.4 — 17 November 2026

Four main destinations: Watch, Queue, Games and Room. Add video lives inside Queue; search, settings, privacy and games remain isolated screens. Back follows the screen hierarchy and dismisses an open keyboard first. Rotation cannot expand a hidden player over another task. Fullscreen on rotate is an optional saved device preference on web and native.

Portrait keeps video, controls, activity and chat in a stable order, with navigation present during playback and hidden while typing. Larger touch areas, readable message text and timestamps, distinguishable presence dots and explicit local playback states improve clarity. Existing draft preservation, history anchoring, keyboard following and reduced-motion behavior remain. Settings → Privacy explains final-leave deletion, disconnect grace and private 30-day chat backup/IP/activity retention.

`/iloveyou` now has a roomier letter, refined video framing, safe-area spacing and a side-by-side landscape layout. Every dialogue, shared trigger, audible-playback logic and original video is unchanged.

Validation: 69 backend tests, 61 client tests and 61 HTTP smoke assertions passed. Two-browser tests cover iPhone visual-viewport and Android resize keyboard models in portrait and landscape, rapid typing, repeated Send, retained drafts, visible latest messages/times, gesture spacing and shared play/pause/seek. Real fixture-video playback advances the queue for both users. Presence, admin diagnostics, haptic preferences and shared games passed regression checks. TypeScript and Android/iOS bundle exports passed. These are local Chromium simulations and automated checks, not physical iPhone/Android or Safari acceptance tests. Signed apps and real three-hour device playback remain unverified.

---

# Solace 2026.11.17.3 — 17 November 2026

Added subtle feedback for game actions/goals, successful chat sends/new incoming messages and playback controls. Room → Settings has a saved master haptics switch and a separate optional Music rhythm switch, BPM controls and Tap tempo. Music rhythm starts off, pulses every other tempo beat using media position, and stops on pause/buffering/background or when disabled. This is a set/tap-matched rhythm, not automatic YouTube audio beat detection. No audio capture, audio rerouting or playback changes are used. Supported browsers use brief vibration; others retain the small visual rhythm indicator. Native builds use expo-haptics for iPhone/Android and require a rebuild.

Removed longer game tutorials, idle explanations, repeated match commentary and the native empty-chat slogan. Turn/status labels, live aim/power, errors, cute gestures, the love-goal message and `/iloveyou` remain.

69 backend tests, 58 client tests, 61 HTTP smoke assertions, TypeScript and Android/iOS bundle exports passed. Browser interaction tests verified settings persistence, no history buzz, chat/game feedback, tempo tapping, rhythm/pause/off behavior, cross-page preferences, removed tutorials and no media writes. Vibration calls were stubbed; physical feel on actual phones remains unverified.

Love Hoops is now Moonlight Duo: a two-stage aim/hold/release game with textured, shaded basketball artwork, curved flight, changing hoop/power targets, streaks, shot counts, perfect swishes, a first-to-five match and rematches. The other viewer sees live aiming and power while a shot is prepared. Cancelling a hold does not submit a shot; live state expires, and goal/cheer effects are bounded and respect reduced motion. Shared cute cheers and mascot reactions remain available. The hoop stays in place during a shot before moving to the next target.

Added Little Ludo as a separate web/native game, for two to four players. Server-generated dice, four pawns, six-to-enter, safe stars, captures, non-safe blockades, bonus turns, three-sixes forfeiture, exact finishes, wins and rematches are implemented. Large pawn buttons supplement board taps on phones. Dice, pawns and turns are shared between participants. The native game bridge now allows only the current room's Ludo endpoint alongside the existing games, and guards late responses when switching games.

69 backend tests, 53 client tests, TypeScript and 61 HTTP smoke assertions passed. Two independent browser participants verified live charging, scoring, cancelled holds, cheers and shared Ludo rolls/moves in portrait and landscape. A deterministic accelerated Ludo match reached completion in backend tests. Physical phone testing remains pending. Netflix remains an external handoff; no Netflix protected-player integration was added. `/iloveyou` assets are unchanged.

Fixed portrait footer/fullscreen coordination, including a global `screen` helper collision with the browser's device-screen object. Portrait device orientation now prevents accidental auto-fullscreen on a short viewport. Home shows only Create/Join; `/create` and `/join` are separate refreshable entry pages, and the old combined UI is hidden during initial loading.

Added shared direct HTTPS MP4/WebM/M4V/HLS URLs using browser-supported formats and existing ordered room controls/queue. Direct media stays client-side; the server does not fetch arbitrary URLs. Native clients include a trusted inline media page and shared controls. Netflix is an external app/browser handoff, with title-link sharing on web; protected Netflix playback is not embedded or synchronized. YouTube search now removes embed/syndication-only filters, returns richer 20-result pages and has Show more pagination. Private/unavailable/restricted videos and API quota limitations still apply.

Love Hoops has a refreshed court, mascot spectators, layered board/net, goal hearts, encouragement after misses, Space-key shooting and shared love/sparkle/applause cheers. Cheers are member-only, rate-limited and do not invalidate shot revisions. Mobile results, source tabs and composer styling were refined. `/iloveyou` is unchanged.

Validation: 63 Python tests, 53 client tests, TypeScript and 61 real-HTTP smoke assertions passed. Two real browser media elements played a synthetic video, retained portrait footer navigation, and automatically advanced both participants to the next direct queue item. Stray ended events did not skip another item. Separate entry refresh, short physical-portrait viewport, search pagination/provider screens, shared goals and cheers passed. No physical iPhone/Android, live YouTube-account search or actual Netflix playback was tested. Native source requires rebuilding.

Android/iOS JavaScript bundle exports passed; signed installers were not built.

Moved the portrait participant/activity row from below the message field to the top of chat, directly after the video and its notices/controls. Web and native use this order. Activity still updates from the same presence data; landscape video presence is unchanged. Checked two-user portrait positioning plus keyboard/picker spacing in four local layouts. TypeScript and 61 HTTP smoke assertions passed. `/iloveyou` remains unchanged.

Faster foreground presence polling and expanded private host/peer diagnostics. Browser/native clients automatically submit bounded operational reports: app/device state, visibility, keyboard/typing booleans, player status/position and supported connection/sync estimates. Server assigns role and playback revision. The password-protected admin panel adds per-participant snapshots and diagnostic history, refreshed every three seconds. No permission prompts or push notifications; no unsent draft text or sensor data. Retention remains thirty days. Diagnostics failures do not change playback or fail room requests.

Two-user portrait testing covered both participants becoming inactive/active while the keyboard opened/closed and the gesture picker was visible. Twelve explicit transitions reached the other viewer in 194–992ms locally; no overlap was observed. Silent disconnect detection took 8.31s, including reconnecting state, and recovery was verified. Browser reports for both roles appeared in the private panel without the unsent draft. 60 Python tests, 52 client tests, TypeScript and 61 HTTP smoke assertions passed. Mobile keyboard/media simulation does not replace physical phone/YouTube testing. `/iloveyou` is unchanged.

Removed default suggested videos from the web search picker: empty search now stays blank, and outdated search responses cannot restore a cleared list. Removed the Privacy & room history and Little gestures information sections from Room details. Added a compact participant/activity row below the portrait chat composer on web and native, keeping it clear of the footer. Landscape video activity is unchanged. Data retention behavior is unchanged; only the requested information UI was removed.

Validated blank search, stubbed search-result rendering, clearing results, removed Room sections, two-person portrait activity and spacing. Gesture picker portrait/landscape and simulated iPhone/Android keyboard checks passed with the new activity row. 50 client tests, TypeScript and 61 HTTP smoke assertions passed. `/iloveyou` remains unchanged.

Fixed disappearing chat timestamps: consecutive-message styling no longer clips the time. Grouping now uses the merged message history rather than the latest incremental response. Native grouped bubbles retain their timestamps too. Browser regression checks passed for outgoing/incoming short, long and emoji messages in portrait, landscape, open/closed keyboard and narrow keyboard layouts, including a live incoming reply. 50 client tests, TypeScript and 61 HTTP smoke assertions passed. `/iloveyou` remains unchanged.

Compact gesture picker: a heart button beside the composer opens one in-flow row of Hug, Kiss, Cuddle, Miss you and Cheer. Selecting sends the shared command, closes the tray and preserves the text draft/reply and existing keyboard focus. Outside tap/Escape dismiss the web tray; accessibility labels and expanded state are included. Native includes the same compact composer picker. Active chat or an open gesture tray prevents automatic web landscape fullscreen from covering it. Short landscape sizing reserves footer space.

Picker validation: 50 client tests, TypeScript and 61 HTTP smoke assertions passed. Touch-browser checks covered portrait, landscape, simulated iPhone keyboard and Android resized-keyboard layouts, including tray/message/composer/footer boundaries, draft and focus preservation, shared delivery to another room participant, outside dismissal and keyboard Escape. Physical phone keyboards remain unverified; installed native apps need rebuilding. `/iloveyou` assets remain unchanged.

Shared stream gestures: `/hug`, `/kiss`, `/cuddle`, `/missyou`, `/cheer` show brief, non-interactive overlays on web and native. Web Room details includes command help. Commands use existing shared chat delivery, skip join/restore history, deduplicate polling and respect reduced motion; they never pause or mute the video. `/iloveyou` remains unchanged. In-flight guards prevent repeated Enter/submit events from duplicating a pending chat message and preserve a newly typed draft.

Rapid-chat follow-up passed: 50 client tests, TypeScript and 61 HTTP smoke assertions. Two isolated browser participants exercised 12 keyboard open/type/send/close cycles across iPhone-style visual viewport and Android-style resizing, with 12 repeated submissions per send. Each message arrived once, the next draft survived, composer/message regions did not overlap during sampled opening frames, latest chat stayed pinned, and the player node remained mounted. Automatic play/pause/seek correction continued with real room API requests and simulated media players; `/hug` was visible to both. This does not verify actual YouTube playback or physical phone keyboard animation.

Keyboard coordination: viewport layout writes are coalesced to animation frames; closing keyboard hysteresis prevents footer flashing; pinch zoom and video-search fields do not trigger the Watch keyboard layout. Chat remains pinned through transient resize/scroll events while intentional history reading remains available. Touching Send retains web input focus. Native iOS layout follows system keyboard animation timing and native Return submits without dismissing the keyboard. No playback protocol or love assets changed.

Keyboard follow-up: 47 client tests, TypeScript and 61 HTTP smoke assertions passed. Local Chromium checks covered animated viewport opening/closing, touch Send focus, latest-message visibility, player retention, unchanged playback revision and no page errors; portrait/landscape/desktop/reduced-height layout checks passed. Real iOS/Android keyboard, predictive-text and browser-toolbar behavior still require physical-device verification. Native source changes require rebuilding the installed app.

Compact chat refinement: removed the Watch header, reduced the composer to 40px, slimmed the bottom navigation, and added Telegram-inspired lavender outgoing bubbles with inline timestamps and no repeated own name/avatar. Incoming sender names remain available. Reply, typing, recovery and room details remain available; `/iloveyou` assets are unchanged. Short-screen video sizing prevents the footer covering the composer, including when a playback error is shown.

Rechecked this refinement with 42 passing client tests, 61 passing real-HTTP smoke assertions and Chromium portrait/landscape/desktop/reduced-height keyboard layout checks. These are browser viewport checks, not physical phone keyboard testing. Earlier broader reliability results below belong to the preceding release.

Separate Watch, Search, Queue, Games and Room screens replace competing panels. Create and Join remain simple entry screens. Refined plum/lilac styling, grouped chat, a quieter composer, readable controls, clear playback status and history-aware scrolling make the mobile flow more consistent. The love command, personal message and video remain unchanged.

Playback now has server revisions, mutation retries use transactional request IDs, reconnect grace is thirty minutes, and fresh snapshots handle database restoration. Native clients receive safe transport, separate queue/room/search/game views, shared games, reduced-motion handling and stronger chat following. The private admin logout cookie race is fixed with server-side revocation and a separate scoped cookie.

Verified SQLite backup/restore, release building and deployed-version smoke tools are included. Local results: 57 backend tests, 42 client tests, 61 real-HTTP smoke assertions, 12 bounded checks and an accelerated three-hour protocol replay passed. TypeScript and Android/iOS bundle export passed. See HARDENING-REPORT.md for evidence and practical limits.

Upload Solace-pythonanywhere.zip into the existing WSGI application directory, preserve instance/configuration, Reload and refresh clients. Rebuild installed native apps. No live deployment, signed native installer or physical iPhone/Android soak has been completed. See DEPLOYMENT-RELIABILITY.md for the exact release and rollback procedure.
