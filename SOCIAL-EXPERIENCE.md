# Solace social experience — 2026.11.20.1

## Consolidated navigation

User Settings at /settings is the single destination for personal experience, notifications, privacy, read receipts, viewing and chat themes. Room management is inline on the Room page: name, visibility, capacity, invitations, host transfer and moderation. Old Settings entry points open the canonical page. Home, Friends, Messages, Open World and Profile use the available width with responsive columns and compact mobile navigation. The portrait room navigation remains visible during playback, source changes and portrait fullscreen fallback; landscape retains the immersive video layout. Essential errors, consent and explicit leave/replacement confirmations remain. The retired personal video prompt is no longer available.

## Implemented and verified requirements

| Requirement | Implementation | Verification |
| --- | --- | --- |
| Single personal Settings; management-only Room | space-settings.html, social-room.js, room-control.js, moon-room.js | template regression; two-user Chromium/WebKit |
| Profile panel, compact Friends/Messages/World | people.js, home.js, companions.css | browser profiles, friend search and three viewport sizes |
| Compact footer, contained switches | companions.css, fullscreen.js | browser portrait play/source changes and fullscreen fallback; client fullscreen test |
| Room, direct and World avatars/reactions | companions.py, companions.js | authorized metadata/avatar tests; browser long press and reactions |
| GIFs, preview, pause, media access controls | existing messaging.py/community.py and chat-media.js reused | backend media ACL tests; Chromium/WebKit GIF upload/viewer checks |
| Read receipts | existing DM receipts; bounded room/World read cursors | mutual saved preference and blocked-reader tests; browser receipts |
| Games without a streaming room | companions.py, play-session.html, games-lobby.js; existing game rules reused | all three games with two users; no room rows created |
| Friend invitations and in-app notifications | companions.py, companions.js | friendship/block/capacity tests; persistent Games invitation inbox; atomic cross-tab claims |
| Real Moments summaries | companions.py, home.js | reconnect/history aggregation tests, own-only access |
| Packaging | tools/build_release.py | manifest and extracted ZIP checks; see verification JSON |

Detailed machine-readable results are in audit-results/companion-verification.json. Browser viewport/keyboard simulations do not certify physical devices.

## Data, privacy and behavior

Migration 9 is additive. It creates reaction/read-cursor/notification-receipt and standalone game/invitation tables. Existing users, settings, rooms, messages and histories are preserved. No new external service or environment variable is required. Include companions.py with every deployment. Keep the same instance directory, signing secret and environment settings.

Avatars are authorized per scope; existing sharing opt-outs remain effective. Receipt indicators require mutual permission, and quiet World browsing does not publish reads. No email, IP, private media URL or internal owner identifier is returned by chat metadata. Reactions allow one supported emoji per user/message; repeats toggle it off. Reporting is available through the message action menu rather than beside every message. Existing validated picture and animated GIF uploads, storage limits and moderation are reused. Direct GIF upload needs no provider credentials.

Standalone games expire after 24 hours. Invitations expire after 15 minutes, require accepted friendship, respect blocks and have a two-player capacity. Joining an accepted invitation is idempotent. The Games page lists pending invitations even if notification alerts are disabled or a toast has been dismissed. An existing streaming room uses its current games rather than showing standalone friend invitation controls. No second game engine or friendship system was introduced.

In-app alerts cover friend requests, unread private messages and room/game invitations; they do not request phone push-notification permission. Alert preferences restore before polling. Delivery uses foreground polling and persistent cross-tab claims, so backgrounded browsers may delay it. Haptic feedback depends on browser/device support; the native bridge requires a new app build. Physical iOS vibration and keyboard behavior were not tested.

Moments uses actual stored watch-history rows: session starts by the requested timezone over 14 days, recorded watched time, distinct participant identities and repeated content entries. Reconnect heartbeats do not create additional history sessions. Titles and counts are shown without publishing private source URLs.

Run tools/maintenance.py through the existing maintenance schedule. It prunes reactions, read cursors and notification claims after 30 days and removes expired standalone games, state, memberships and invitations. Room and DM media retain their existing deletion and quota policy. Account deletion erases the new owner records through the existing deletion workflow. SQLite single-writer and deployment limitations remain unchanged.

## Verification limits and launch gates

Tests use synthetic identities and media on local disposable servers. Chromium exercised decoded synthetic HTTPS video; the principal WebKit synchronization checks use a simulated player. No physical Android/iPhone, production hosting, YouTube advertisements or live Netflix/DRM behavior was certified. Existing operator configuration, SMTP, named staff/MFA enrollment and deployment acceptance gates still apply. This update was not deployed publicly.
