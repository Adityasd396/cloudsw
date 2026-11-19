# Solace 2026.11.19.4 — focused screens and community chat

Root source is authoritative. `app:app` remains the deployment entry point. This release adds migration 8 through the existing initializer; there is no new service, provider credential or environment variable. Install the existing locked requirements and upload the complete generated release together. Never replace the deployed `instance/` directory or secrets with local test data.

## Navigation and preferences

An active web room owns its existing player and transport. Home, Messages, Open World, Friends, Profile and Settings open as separate same-origin surfaces within that room; Games continues using its existing room game surfaces. Ordinary navigation does not recreate the player or publish playback controls. Return to room is separate from leaving. Creating/joining a replacement room and signing out require confirmation; cancellation leaves membership untouched. A confirmed replacement joins the new room before leaving the old one. Browser refresh still recreates the document and remains subject to browser autoplay rules. Native account surfaces keep the existing player mounted; changing native room membership deliberately replaces the session.

Privacy, public-profile sharing, online visibility, read receipts, activity summaries, in-app alerts, haptics, rhythm tempo, rotation and themes live in Settings. Compact accessible switches replace exposed checkbox forms on ordinary screens. Rhythm is a configured tempo pulse, not audio beat analysis. No OS notification permission request is introduced.

Accounts and recognized guests persist preferences server-side. Existing local experience preferences migrate once when Settings is first opened. Guest registration retains the same profile and preferences. Clearing the guest cookie may remove access; an account is needed for recovery across devices. Public-profile discovery remains a separate default-off permission; community participation does not enable avatar or stats sharing.

The first Open World visit offers Join the conversation or Browse quietly. An atomic server claim records that this optional step was shown; navigating away defaults to quiet browsing and does not repeat the question. Joining is explicit, and every choice can be changed later in Settings.

## Open World behavior and privacy

`/world` is a shared community chat for recognized guests and accounts. Joining does not require a room or friendship. Private direct messages still require accepted friendship. Existing profile previews, blocks, report evidence, staff permissions, emergency switches, upload validation and storage quotas apply to community messages and GIFs. Messages have idempotent request IDs; retries cannot create duplicates with the same ID. Authors can remove their messages and staff with the existing content permission can remove reported content. Media is authorized through the existing chat-media service. Community uploads are public to eligible authenticated/recognized community visitors, not restricted to friends.

The online number means **eligible joined visitors with online visibility enabled who currently have Open World visible**, not all visitors to the website. One identity is counted once across up to eight tab leases. Heartbeats run every 15 seconds, leases expire after 32 seconds, and background/unload signals remove the current tab. Revoked account sessions, blocked pairs and platform restrictions are filtered server-side. An abrupt disconnect can remain visible until lease expiry. People browsing quietly are not counted. Polling is 1.2 seconds while visible; reconnects refresh from persisted state. This is bounded polling, not an instantaneous WebSocket guarantee.

Community history is retained for up to 30 days or the newest 10,000 messages, whichever prunes first. Cleanup runs at most once per minute during use, so the count is a cleanup target rather than a hard instantaneous cap. Attached community media is purged with the source message. Retry receipts expire after 30 days and are bounded to 100,000. The browser keeps at most 250 message nodes and paginates older history; Latest returns to the recent window. Reports retain independent minimal evidence under the existing 30-day evidence / 180-day case policy. Account deletion clears the owner's public text/media and preferences. Moderation evidence remains separately restricted as documented in SAFETY-OPERATIONS.md.

Community pages/APIs remain authorized, noindex and no-store. Neither posts nor online lists are added to public SEO or routine operations telemetry. Public `/open-world` marketing text describes the community and consent accurately. No personal data is added to the sitemap.

## Verification and limits

The new backend tests cover stranger chat, accepted-friend-only DMs, guest upgrades, one-time preference claims across concurrent tabs, unique/stale/revoked presence, block filtering, media access, moderation, input/CSRF checks, retention, pagination and unchanged room playback state. Browser checks cover two users, GIF playback/pause, saved preferences, multiple tabs, room-switch cancellation/approval, portrait/landscape viewport and keyboard models, latest-message visibility, composer width and preserved player/command revision.

See `audit-results/community-verification.json` for final counts and `audit-results/community-browser-results.json` for engine-specific evidence. Chromium decodes synthetic HTTPS video in the community navigation checks; the corresponding WebKit navigation check uses a simulated player. Physical iPhone/Android keyboards, native builds, battery/background behavior and real WAN sessions are not certified by these tests. Existing physical-device, operator configuration, named staff enrollment, dependency and hosting launch gates remain in LAUNCH-READINESS.md.

## Release, backup and rollback

Run `python tools/build_release.py --version 2026.11.19.4`. It copies `community.py`, migrations, templates, assets and documentation and verifies both ZIP archives. PythonAnywhere uses the whole **Solace-pythonanywhere.zip**, not selected frontend files. Reload the existing web app and verify `/api/health`, `/api/ready`, `/api/me/preferences`, ordinary room playback and `/world` with a disposable user. Installed native apps need a rebuilt binary; web assets alone cannot update native code.

Use the existing `tools/storage.py` backup/restore procedure before changing production files. Restore clears ephemeral community leases, so clients reacquire presence. Migration 8 is additive; rolling back code leaves its tables intact, but old code cannot display new community messages or settings. Preserve a matched code/database backup for a full rollback. See DEPLOYMENT-RELIABILITY.md and PYTHONANYWHERE.md for existing commands and operational checks. No public deployment or production data access is part of this local verification.
