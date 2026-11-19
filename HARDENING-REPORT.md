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

# Solace experience refinement — 17 November 2026

Release: **2026.11.17.4**. Local update only; not deployed to PythonAnywhere.

## Changes and verification

Watch → Queue → Games → Room is the four-destination navigation. Queue owns Add video, and search remains a separate inert-background screen. Settings and Privacy follow parent-screen Back behavior; Android hardware Back dismisses the keyboard before navigating. Rotating while in a task screen cannot promote its hidden player to fullscreen. The saved rotate preference is shared in behavior across browser and native source; native preference writes are ordered and initial loading cannot overwrite a new selection.

Portrait keeps video/controls/activity/chat/composer/navigation in order. Readable message bodies and timestamps, larger hit areas, distinct presence shapes and explicit Loading/Buffering/Paused/Playing/Tap to resume/Offline/Reconnecting/error states are included. Chat scroll and layout operations do not change playback state or replace the mounted player. Settings → Privacy accurately distinguishes public room deletion from 30-day private backups, IP/activity records and temporary disconnect recovery.

`/iloveyou` changes only presentation CSS: larger letter text, improved framing, safe-area spacing, reduced-motion handling and a two-column landscape composition. SHA-256 checks preserve love.html, love.js, love-film.js and the original MP4 byte for byte. Dialogues, shared delivery and audible-playback behavior are unchanged.

69 Python tests, 61 client tests and 61 disposable HTTP smoke assertions passed. The server test includes admin login/logout/expiry, same-origin rejection, idempotent mutations, two-user playback, queue operations and immediate deletion after the last explicit Leave. A clock-dependent regression test was corrected to freeze after signed sessions exist, avoiding negative cookie age while still testing same-timestamp playback revisions.

Chromium integration passed 12 rapid-send cycles (12 repeated submissions per send, exactly one delivery) across iPhone visual-viewport and Android resize keyboard models. A separate 12-cycle two-user portrait/landscape test verifies keyboard opening/closing, latest message and timestamp visibility, gesture spacing, stable player identity and pause/resume/seek convergence within a 1.5-second bound. Timestamp geometry also passed narrow 320px, portrait, keyboard and landscape views. Search stays above the inert playback screen, and four-item navigation and parent Back paths pass. Real fixture-media playback advances both clients to the queued video, and duplicate end events do not skip another item.

Presence regression verifies active/inactive transitions, keyboard/gesture separation, lost-heartbeat expiry and private admin host/peer diagnostics without storing typed drafts. Haptic checks verify saved Off, no history buzz, tempo/pause suppression and zero playback writes. Full two-user hoops/Ludo checks cover charging, cancelled shots, goals/cheers and shared dice/pawn moves. Existing accelerated three-hour web/native session/model tests pass.

TypeScript passed; Android and iOS bundles exported successfully into mobile/.export-experience-nov17. Current watch, queue, room, keyboard and search preview images were regenerated from disposable data.

Limits: Chromium viewport/keyboard models do not prove actual iOS Safari or Android keyboard animation, OS background behavior, haptic feel, heat or battery life. No phones were available. Local exports are bundles, not signed APK/IPA installers. YouTube restrictions, ads and autoplay requirements remain provider/browser controlled. Deployment and physical three-hour acceptance are still pending.

---

## Earlier release verification (historical)

# Solace UI and reliability update — 14 November 2026

Release: **2026.11.17.3**. This is a local, packaged update; it has not been deployed to PythonAnywhere.

## Subtle haptics and quieter copy

Shared web/native policy validates saved preferences, accepts only chat/game/goal/song/beat feedback kinds, bounds tempo to 60–160 BPM and rate-limits pulses with no queue. Master feedback is on by default, optional Music rhythm is off by default. Room → Settings provides master/music switches and tempo/tap controls. Preferences remain local to the device and persist across sessions. Turning off and backgrounding suppress future pulses; browser vibration is cancelled on hide/exit.

Native uses the SDK-matched expo-haptics module (~58.0.8), iOS selection/soft impact and Android frequent-tick/tick effects with a selection fallback. Unsupported calls are caught and cannot fail user actions. Native game pages forward only allowed game/goal events through the authenticated-origin WebView handler; the native preference is authoritative. Existing binaries must be rebuilt with the new module. Native preference writes are serialized and initial loading cannot overwrite a newly changed choice.

Web emits 4–10ms vibration requests only on supported, activated browsers. Unsupported hardware/browser APIs fail quietly, and Settings explains visual-only browser feedback. Music also uses a tiny heart indicator. Browser/API/device policy determines actual vibration; no physical haptic intensity was measured. See [Expo Haptics](https://docs.expo.dev/versions/latest/sdk/haptics/) and [MDN Vibration API](https://developer.mozilla.org/en-US/docs/Web/API/Vibration_API).

Music rhythm is explicitly tempo-based, not audio beat detection. YouTube iframe audio is not analysed. There is no microphone, AudioContext graph, stream capture, decoding proxy or media rerouting, avoiding cross-origin silence or interference with playback. A read-only media-position clock pulses on alternate tempo beats; startup, pause, buffering, stale native samples, ad state, seek jumps, track/tempo changes and non-Watch screens reset or suppress it. Native position is briefly extrapolated from fresh samples and stops if samples age beyond 2.5s; web requires recent room contact. No catch-up pulse burst is queued after a seek or resume. Feedback adds no server requests.

Game feedback occurs on acknowledged local actions and new goal events; typing and repeated game polling do not buzz. Chat history joins/restores do not replay feedback. Native and web share the same core policy. Long game tutorials, repeated idle/challenge/winner commentary and the native empty-chat slogan were removed; meaningful turn/status/error labels, live aim/power, cute gesture responses and the requested love-goal and `/iloveyou` content remain.

Validation: 69 Python tests, 58 client tests, 61 HTTP smoke assertions and TypeScript passed. Android/iOS exports succeeded in `mobile/.export-haptics-nov17`; these are not signed installers. New unit tests cover bounded preferences, off/background suppression, emission limits, rhythm startup/pause/seek/tempo/source resets, shared policy parity and emitter failures. Chromium integration with a stubbed Vibration API verified successful chat feedback, saved Off after refresh, no initial-history buzz, tempo tapping, alternate media pulses, pause/off suppression, zero media writes, unchanged server playback revision, game preference propagation and tutorial removal with no page errors. Actual iPhone/Android hardware feel, browser vibration support and real-song tempo matching remain unverified. All five love assets remain unchanged. Browser regression: `tests/check_haptic_ui.py` against the disposable server on port 8017.

## Moonlight Duo and Little Ludo

Hoops now uses an original, code-rendered textured SVG ball, spherical shading/seams, curved Web Animations flight, adaptive shot targets and a power mechanic. Press locks the moving aim, holding builds power, and release submits both. Server validation checks bounds, current player and shot revision. Targets change after each shot and narrow with scoring. Perfect swishes, streak/attempt stats, first-to-five wins/rematches, gentle misses, mascot movement, hearts and shared cheers form the cute match concept. The next hoop target waits for the current shot animation; reduced motion bypasses flight/particle animation.

Authenticated aiming/charging/idle snapshots share aim and power at bounded foreground rates (about 280ms while engaged, server throttled to 150ms except idle). Opponents see names, action labels and power rather than camera video. Snapshots expire after 2.5s without updates; cancelled pointer holds publish idle without shooting. A pending idle snapshot is coalesced behind an in-flight update. Live updates and cheers do not change shot revisions, so they cannot invalidate an otherwise current shot. Revision-checked shots remain exactly once; shared game state does not alter room playback state.

Little Ludo uses a separate member-only endpoint and nested room-game state, preserving tic-tac-toe and basketball. Two to four players join a lobby before starting. The server generates dice and validates every revision, turn and pawn move. The documented rule set includes four pawns, six-to-enter, safe star cells, captures, opponent pair blockades on non-safe paths, six/capture/finish bonus turns, three consecutive sixes passing the turn, exact finish and all-four-home victory. Remaining-player matches reset if an explicit departure makes their stored roster invalid. Dice and legal choices are shown on both clients, and large pawn buttons supplement the board. Spectators can watch; late joining an active round is rejected. Game controls are accessible with keyboard and have portrait/landscape layouts.

Native Games lists all three separate pages and scrolls on short screens. Its bridge allowlist includes the current room's `/ludo` endpoint and uses generation checks to prevent old game replies reaching a newly selected page. No account cookies are exposed to the game page. Server deployment must include `ludo_game.py` and all new static files.

Validation: 69 backend tests, 53 client tests, TypeScript and 61 real-HTTP smoke assertions passed. New tests cover live power/aim authority, invalid/stale actions, power misses/swishes, server dice, stale rolls, captures, blockades, exact finishes, three sixes, four-player capacity, other-game coexistence, explicit room deletion and a deterministic whole Ludo match through victory/rematch. Two Chromium sessions verified peer-visible charging before release, a shared power goal, cancelled holds causing no shot, idle recovery, textured ball rendering, cheers, shared Ludo dice/pawn moves and portrait/landscape bounds with no page errors. No physical iPhone/Android hardware or camera video was used. The browser regression is `tests/check_full_games.py` against the disposable server on port 8017.

Netflix clarification: this release does not implement Netflix sign-in or protected playback. Rave's official FAQ confirms Netflix support with a paid service subscription; its internal playback integration was not established from public documentation. Solace's Flask room coordination does not itself provide a Netflix-capable protected player. A future implementation would require a separately validated provider/player integration on the actual target platforms; a YouTube/direct-video adapter is not evidence of Netflix support. References: [Rave FAQ](https://dl.rave.io/faq), [Netflix supported browsers](https://help.netflix.com/en/node/30081), [Netflix protected-content error guidance](https://help.netflix.com/en/node/27451/). Existing Netflix links remain labelled as external, unsynced handoffs. All five love assets remain unchanged.

## Streaming sources, entry isolation and mobile experience

Renamed the global `screen()` task helper, which was masking the browser's built-in screen object. Auto-landscape now consults the actual device orientation and defers during chat/picker use; portrait normal playback retains navigation. The menu still hides for deliberate fullscreen or the active keyboard layout. Home contains only the two entry options. Flask serves `/create` and `/join` separately; these retain the appropriate form on refresh, and a pre-entry CSS gate prevents flashes of legacy room content. Invite-link entry remains supported.

Added a direct-media adapter implementing the room's existing play/pause/seek/queue interface. Server parsing accepts HTTPS MP4, WebM, M4V and HLS paths, rejects credentials/non-media provider pages and never fetches these URLs itself. Supported codecs, live-seek behavior and HLS vary by device; source access, browser media policy and permissions remain the stream owner's responsibility. Native direct media uses an escaped inline HTML page, checks bridge URL/room identity, and reuses playback coordination. Signed URLs are shared with room members as necessary for playback; direct URLs are not sent to YouTube thumbnail endpoints. Cached YouTube readiness and stale-source events are guarded during transitions. Direct-media ended events require actual ended state and the current playback instance.

The source picker has YouTube, Video URL and Netflix pages. Netflix opens its own app/browser; web users can share a validated Netflix title URL to chat. Solace does not embed, decrypt or synchronize Netflix protected media. YouTube search now uses the public API without embed/syndicated-only filtering, with channel/description metadata, 20-result pages and a Show more control. It cannot promise every video or playback: account access, API quota, region/age/private content and uploader restrictions still apply. Reference: [YouTube Search API](https://developers.google.com/youtube/data/reference/rest/v3/search/list), [Netflix browser requirements](https://help.netflix.com/en/node/30081).

Love Hoops uses a richer code-rendered court, mascot spectators, improved meter/score styling, layered net/board and bounded goal particles. New shared cheers are restricted to joined players, accept three fixed emojis, rate-limit to one per second, and do not change shot revisions. Pointer shooting remains; Space is supported. Goal and cheer animations respect reduced motion. Misses receive brief encouragement. Mobile composer/results/source controls and native bubbles were refined.

Validation: 63 Python tests, 53 client tests, TypeScript and 61 HTTP smoke assertions passed. New backend tests cover separate routes, direct URL rejection, mixed queue progression/stale end protection and cheers without shot conflicts. Native helper tests cover URL checks and escaped inline media. Chromium integration used actual media elements and an included six-second synthetic MP4 with two room sessions: both played direct media and automatically advanced together, the portrait footer stayed visible, and a synthetic stray end event did not consume another item. Entry refresh, device-portrait/short-viewport behavior, stubbed rich search and pagination, provider pages, shared goal effects and cheers passed with no page errors. These are local browser tests, not physical iPhone/WebKit or Android installed-app tests; no live API key search, DRM streaming or Netflix playback was tested. Native apps need rebuilding. All five `/iloveyou` assets are unchanged.

Android and iOS JavaScript/Hermes bundle exports also passed in `mobile/.export-nov17` (626/628 modules). These generated bundles are excluded from the source/server ZIPs and are not signed installable apps.

For the browser integration regression, run the disposable server from `tests/run_local_smoke.py --serve --port 8017`, then `python tests/check_stream_upgrade.py` with Playwright/Chromium installed. Its media and YouTube responses are test fixtures; it does not stream external test content.

## Portrait activity placement correction

Moved the web/native portrait activity row above the chat rather than under the composer. On web it follows the video stage and any player notices; every render restores this order before the chat. The native row follows video controls/notices before chat content. Portrait visibility, presence data and landscape video overlays are unchanged.

Two-user browser layout checks confirmed activity sits below the video and above chat, separate from the composer/footer. Gesture-picker checks passed at portrait, simulated iPhone keyboard, Android resized keyboard and landscape sizes, preserving draft/focus and keeping all composer/picker bounds within the viewport. TypeScript and 61 HTTP smoke assertions passed. Existing presence integration assertions were updated for the new row order. Physical phone testing remains unavailable. No backend, diagnostics, playback or love asset behavior changed.

## Presence validation and private diagnostics

Foreground polling now uses a 500ms playing / 750ms paused target (scheduled on the existing 500ms loop), retaining error backoff and hidden/background suspension. It cannot promise instantaneous status after silent network loss: explicit visibility updates are immediate server writes, whereas heartbeat age becomes reconnecting at 2.5s and inactive at 8s.

Two isolated browser participants exercised both directions of active/inactive updates across 844px, 504px and restored 844px portrait viewports, with the gesture picker open and a private unsent draft. Twelve explicit transitions arrived in 194–992ms on localhost. Message/tray/composer/activity bounds stayed separate. A simulated silent network drop became reconnecting then inactive in 8.31s, and reconnect presence returned active. This is browser simulation, not physical OS background lifecycle or actual YouTube testing.

Automatic member-authenticated diagnostics use a separate endpoint and private admin SQLite tables, preserving room/playback transactions. Reports contain allowlisted, bounded operational values only: client/platform/release, viewport, orientation, supported locale/timezone/network estimates, visibility/connectivity, keyboard/typing booleans, fullscreen, supported player state/position/duration/mute/volume/drift and request timing. Browser identity/IP come from existing server logs. Host/peer role and playback revision come from the server. Native provides the supported subset of these fields. No typed drafts, passwords, arbitrary URLs, clipboard, location, contacts, microphone, camera or battery APIs are collected. No permission API or push notification is used.

Normal reports are sent about every 15s plus coalesced state changes; writes are bounded per room/member to at most once per 2s and history transitions to once per 5s, with periodic history samples at 30s. History and current snapshots expire under the existing 30-day retention. Storage is separate, indexed and time-bounded; logging failure returns a best-effort accepted response without modifying playback. A maximum 3s browser request timeout and one in-flight report prevent diagnostics retry buildup. Browser class mutations with unchanged state do not trigger continuous reporting. Native installed apps require rebuilding.

The private panel now displays host/peer snapshots, player/connection/app states and recent diagnostic history; stale reports and estimated values are labelled, and refresh is 3s. Client-reported metrics are diagnostic observations, not trusted proof of identity or device health. Existing admin authentication/logout and IP matching behavior remain intact.

Validation: 60 Python tests, 52 JS/native-client tests, TypeScript and 61 real-HTTP smoke assertions passed. New tests cover member-only submission, server-assigned roles, dropping arbitrary draft/credential/IP payloads, numeric/type bounds, write-rate limits, 30-day retention, logging-storage failure isolation, permission-free read-only collection and bounded event storms. Actual browser integration verified both participant reports in the authenticated panel and absence of the unsent draft. All five love assets remain unchanged.

Packaging was also hardened: core server and native source files now come from explicit allowlists rather than depending on a previous release manifest. Local generated state found in the release folder was preserved under `.openai/release-local-state-*`, outside public artifacts. Both archive contents and source/release hashes were checked, private/generated paths excluded, and an extracted PythonAnywhere package successfully started and served all 18 referenced assets.

## Search cleanup and portrait activity

The web video picker no longer fetches or displays featured suggestions on empty search. A search epoch discards late responses after clearing/replacing a query. Actual query search remains available. Room details no longer include the two requested Privacy & room history / Little gestures sections; the native retention explanation was removed as well. Documentation and actual retention behavior remain unchanged.

Portrait Watch now displays a compact participant row with status dots and names below the composer and above navigation. It uses existing presence updates and remains visible while the keyboard is open. Web render ordering explicitly keeps it before the bottom navigation. Native includes a corresponding horizontal activity row. Landscape video presence remains unchanged.

50 client tests, TypeScript and 61 HTTP smoke assertions passed. Local browser checks verified initially empty results, stubbed query results, blank clearing, removed Room sections, two-member portrait activity and composer/activity/navigation boundaries. Gesture-picker regression checks passed in portrait, landscape, simulated iPhone visual viewport and Android resized viewport, preserving draft/focus and keeping composer/tray clear of viewport/footer. No physical phone or live YouTube testing was performed. All love assets are unchanged.

## Timestamp regression fix

An old, more-specific grouped-message selector clipped timestamps to 1px, overriding the later inline timestamp layout. Removed timestamps from that rule. Grouping now reads `state.messages` after merging incremental responses, so empty/new-message-only polls cannot incorrectly change grouping of existing rows. Native grouped bubbles also always render their time metadata.

Two-member browser regression checks verified all six timestamps (four grouped bubbles) remained unclipped, nonzero-sized and within bubble bounds at 390×844, 390×504, 320×450, restored 390×844 and 844×390. Covered both senders, short text, long wrapping text, emoji-only bodies, typing and a live incoming reply. 50 client tests, TypeScript and 61 HTTP smoke assertions passed. These are local browser checks, not physical phone tests. No playback or love asset changes.

## Compact gesture picker

Added a compact heart toggle beside the web/native chat input. Five quick-send choices use the existing shared gesture commands without changing the message draft or reply. The tray occupies normal layout space above the composer, reserves chat space and never positions itself over the keyboard. Selection uses the synchronous send guard; success closes the tray, failure leaves it available. Web touch interactions preserve existing composer focus, outside tap/Escape dismiss, and keyboard selection returns focus to the toggle. Native uses an in-flow horizontal tray with keyboard-persistent taps. Landscape auto-fullscreen on the web now defers while chat is focused or the tray is open. Short-height video sizing reserves footer space.

50 client tests, TypeScript and 61 real-HTTP smoke assertions passed. Chromium touch checks at 390×844, 390×844 with a 504px visual viewport, 390×504 resized viewport and 844×390 verified message/tray/composer boundaries, composer above viewport/footer, five options, draft/focus preservation and shared command delivery to a second member. Outside-tap and Escape dismissal passed with no page errors. These remain simulated mobile keyboard checks; no physical phone testing was available. The native source requires rebuilding. All five love asset hashes remain unchanged.

## Rapid messaging and shared gestures

Web and native now guard in-flight chat submission synchronously. Repeated Enter cannot enqueue duplicate sends, and a changed draft or reply is preserved after an earlier web request completes. Failed requests retain the draft. Server chat pacing remains unchanged.

Five exact commands (`/hug`, `/kiss`, `/cuddle`, `/missyou`, `/cheer`) use shared chat messages to display a bounded 3.2-second, pointer-transparent gesture. They do not call playback, audio, focus or network APIs. Only new messages trigger effects; join history, database generation changes and duplicate polls do not replay them. Reduced motion is respected. Web help lives in Room details. Native apps require rebuilding. The five love assets remain byte-for-byte unchanged.

Validation: 50 client tests and TypeScript passed, alongside 61 real-HTTP smoke assertions. Two isolated Chromium participants ran six cycles per keyboard model (12 total), rapidly typing and issuing 12 form submissions per send. Each body was stored once; next drafts survived; sampled keyboard frames and final composer/chat bounds did not overlap; latest chat remained pinned; no page errors occurred. Alternating participants sent play/pause/seek commands during these cycles. The receiving browser applied them through ordinary polling and sync code, without a forced resync. Both simulated players agreed within 0.032 seconds at sampled checks and the player nodes remained mounted. This sampled model result is not a real-media latency guarantee. Shared `/hug` delivery was verified in both browser sessions. Physical phone keyboards and actual YouTube media were not available in this test.

## Keyboard coordination follow-up

Frame-coalesced viewport handling replaces synchronous repeated writes and the delayed focusout reset. A separate closing threshold retains the keyboard layout until the viewport recovers; orientation resets the baseline, and pinch zoom is ignored. Only the chat composer can enter Watch keyboard mode. Resize-induced chat scroll events cannot detach a pinned conversation during closing, while a deliberate history gesture can. Pointer Send retains web input focus. Native iOS uses system keyboard layout animation timing; Return submits without blurring. Video control/sync code and all love assets are untouched.

47 client tests passed, including viewport storms (1000 events produce one pending frame), iPhone-style viewport offsets/closing, Android resized viewport/rotation, pinch zoom, focus-preserving Send and closing-scroll pinning. TypeScript and 61 real-HTTP smoke assertions passed. Chromium interaction simulation verified touch Send kept focus, footer returned after closing, latest message remained pinned, the player node remained mounted, playback revision was unchanged and no page errors occurred. Four layout sizes were rechecked. This is local simulated keyboard coverage, not an actual iOS or Android keyboard/performance guarantee. The native app must be rebuilt; its earlier bundle export predates this small source update.

## Compact chat follow-up

Removed the Watch header, moved recovery status/retry into Room details, narrowed the composer height to 40px, and reduced bottom menu padding/icon sizes while retaining 44px navigation targets. Telegram-inspired outgoing bubbles hide the repeated own name/avatar; timestamps follow text, including grouped messages. Incoming messages retain sender labels. Reply controls and `/iloveyou` remain intact. Short viewport video sizing reserves composer space even with a player error notice.

Follow-up validation: all 42 client tests and 61 real HTTP smoke assertions passed. Chromium checks at 390×844, 844×390, 390×500 and 943×903 confirmed no header, 40px composer, visible inline timestamps, no horizontal overflow and composer/footer separation. Search remains isolated with the Watch shell inert. All five love asset hashes match the preserved baseline. No playback sync logic changed. Physical phones were unavailable; the reduced viewport check does not emulate an actual OS keyboard. The broader test results below were obtained for the preceding reliability release.

## Product and frontend

- Independent full-page website screens: Home, Create, Join, Watch, Search, Queue, Games, game play and Room details. Only one task screen is visible at a time. Covered Watch controls are inert and hidden from accessibility navigation. The mounted video session continues behind task screens; returning restores focus. The love surprise retains its existing modal behavior.
- Warm plum/lilac/rose tokens, consistent corner shapes and spacing, comfortable playback controls, readable message typography, grouped consecutive messages, a softer composer and a quiet room/status header. Secondary sharing, activity, hosting, ad reporting and Leave actions have moved into Room details. Queue has Playing now and Up next sections with named play/remove/reorder actions.
- Chat follows the latest message while typing and through keyboard resizing. Reading older messages preserves the visible anchor, with a New messages shortcut. Native lists use the same follow-versus-read intent and expose a latest-message shortcut.
- Native Search, Queue and Room details are separate screens; Games uses a dedicated selector and shared Love hoops/tic-tac-toe pages. A narrow bridge sends only the current room's two game endpoints through the authenticated native transport, keeping session credentials out of page JavaScript. Settings/error recovery and Back navigation are separate from room entry. Native controls respect screen readers and reduced motion; reaction movement respects reduced-motion preference.
- **/iloveyou is unchanged:** its five static love assets/video are checked byte-for-byte against the saved pre-update hashes. Both independent browser users received the surprise during the smoke test. Its message and video were not edited.

## Backend and app reliability

- A server-issued playback revision orders accepted clock/video changes, even when timestamps are equal. Modern observations require the current revision and the host role. Explicit commands can rebase over intervening observations; an older competing intent or video instance returns a conflict and triggers fresh-state recovery rather than silently overwriting the clock.
- Room mutations and their request receipts commit together. Create/chat/add/move/select/watch/playback and other room mutations can safely retry with the same request ID; reusing an ID for another payload is rejected. The shared web/native transport preserves the exact ID/body on a bounded network/502/503/504 retry and does not retry a conflict. Updated clients check backend capabilities before mutation.
- Full room responses read a consistent database snapshot. GET snapshots and telemetry require room membership. SQLite mutations are serialized, busy waits bounded, relevant lookups indexed and contention returns a retryable error. Startup migrations and secret creation are covered by a three-worker cold-start test.
- Thirty-minute abandoned-room recovery grace replaces two minutes. Explicit final Leave still deletes all public room data. Native/browser recovery prevents stale media observations while a fresh authoritative snapshot is being obtained.
- Backup/verify/restore tooling copies SQLite online, checks integrity/hashes, refuses to overwrite an existing restore target and excludes secrets. Restore changes the storage generation so old chat cursors and lower restored playback revisions do not strand clients. Restored admin sessions are revoked.
- Private operations adds bounded numeric drift/reconnect/conflict/replay aggregates without storing message bodies in metrics. Browser drift uses elapsed time since receipt rather than assuming the device clock matches the server.
- Found and fixed a real concurrent admin logout race: ordinary room responses could resurrect an old Flask auth cookie. Admin auth now uses its own HttpOnly, SameSite=Strict, admin-path cookie and expiring server-side session. Logout revokes it; replayed old cookies cannot reopen stats or backup. Cached admin pages revalidate on return.
- Repeatable allowlisted ZIP building identifies the release, verifies source hashes/archive contents, excludes private/generated data and retains a public-code rollback archive. A deployment verifier checks version/assets and can run a disposable two-user journey.

## Validation

- 57 backend/startup/storage tests passed, including duplicate/concurrent requests, same-timestamp playback order, access checks, legacy/fresh migration, three-worker startup, backup/restore, live WAL backup, retention safety, restored generation/cursors, and replayed admin cookies.
- 42 JavaScript/native tests passed, including request retry identity, conflict handling, adaptive polling, restored-generation reconciliation, native game-bridge allowlist, keyboard event storms, older-history reading, autoplay recovery and existing sync/love regressions.
- 61 real-HTTP smoke assertions passed: auth/CSRF/logout/expiry, modern capability check, retry-safe chat/video add, ordered controls, games, queues, backups and final-Leave deletion. JavaScript syntax and TypeScript checks passed.
- 12 bounded local concurrency/security checks passed. 120 room reads across four concurrent workers measured approximately 32 ms median and 126 ms p95 in the local Flask-client run; these are not internet latency or deployed capacity figures. Twenty concurrent queue additions retained every item.
- Accelerated three-hour backend replay: 10,800 simulated seconds, 4,253 polls, 20,065 assertions; all passed. Android-model/iPhone-model media tests also passed. The replay is not a three-hour wall-clock phone run.
- Actual independent browser sessions verified: portrait controls below video; Search/Queue/Games/Room isolation; keyboard-sized latest-message/draft preservation; history anchor plus New messages; two-user pause/forward seek/resume; host transfer; landscape fullscreen/search isolation; the unchanged love surprise; admin login/logout with active room polling. A paused seek left both video elements at the same timestamp (160.899121 seconds) in the captured sample. This is an observation, not a drift guarantee.
- Android/iOS JavaScript bundle export passed. This does not create signed installers or verify native physical-device rendering.

Evidence beside this report: solace-v2-watch.jpg, solace-v2-queue.jpg, solace-v2-room.jpg, solace-v2-keyboard.jpg and solace-v2-search-landscape.jpg. Exact archive file counts, hashes and build ID are emitted by tools/build_release.py and release/MANIFEST.json.

## Limits and deployment

No phones were available. Physical keyboard behavior, battery/heat, calls, OS suspension, actual mobile ad delivery and a three-hour physical-device run remain unverified. The live PythonAnywhere site has not been changed. Installed apps require a rebuild. Backups are individually consistent per database, and private operational logging remains best effort. Production sockets/managed-database migration and scheduled backups require hosting/account configuration; the package supplies compatible polling, tools and instructions rather than changing that account silently.

YouTube still controls embedding permission, audible autoplay and its own branding/paused overlays. A fully unbranded or universally ad-free YouTube player is not promised. See DEPLOYMENT-RELIABILITY.md for upload, backup, rollback, monitoring and the physical-device release gate. Older report files describe earlier snapshots; this report is current for this release.
