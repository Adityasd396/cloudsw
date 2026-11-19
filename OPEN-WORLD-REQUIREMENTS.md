# Open World and safety requirements matrix

## Current community update: 2026.11.19.4

The main `/world` screen is now community chat. The older people-discovery API and explicit public-profile permissions remain available for compatibility; their Settings controls are separate from joining the chat. This supersedes references below to the former World grid.

| Current requirement | Status | Implementation and evidence |
|---|---|---|
| Focused screens and centralized preferences | Implemented; local browser checks | space-settings.html/js, app-space.js; settings auto-save, themes and compact switches |
| Navigate without losing room/player | Implemented; two-user Chromium/WebKit checks | moon-room.js, rooms.js; object identity, unchanged command revision, explicit cancel/approved room replacement |
| Shared community, no friendship prerequisite | Implemented; backend and browser checks | community.py, world.html/js/css; stranger text/GIFs, DM friendship restriction preserved |
| Unique eligible online visitors, stale/revoked sessions | Implemented; bounded 32-second lease semantics | world_presence; tests/test_community.py; multi-tab browser check |
| Once-only optional choice, quiet default, Settings changes, guest upgrades | Implemented; concurrency/persistence tests | user_preferences, atomic world-intro claim; test_community.py |
| Existing blocks, reports, moderation, quotas and media reuse | Implemented; integration regressions | messaging.py, platform_safety.py, user_storage.py; world message/media authorization and staff removal |
| Retention and private indexing | Implemented; retention/header tests | 30-day/newest-10,000 cleanup, bounded receipts, noindex/no-store; UX-COMMUNITY.md |
| Portrait/landscape keyboard and existing features | Browser models verified; physical acceptance blocked | community, messaging, keyboard, safety, games, queue and public-launch browser scripts; community-verification.json |
| Complete release and PythonAnywhere ZIP | Generated through existing builder; checksum verification | community.py in SERVER allowlist; release/MANIFEST.json and builder integrity checks |


19 November 2026. Root source is authoritative; production imports `app:app` through the existing Waitress/PythonAnywhere entry point. The existing release builder now includes messaging, people, platform safety, named staff authentication, setup tools, migrations, templates and assets. No production deployment or data was accessed.

| Requirement | Implementation status | Files and verification evidence |
|---|---|---|
| Optional room names, host rename, saved identities | Implemented and locally verified | app.py, social.py; test_messaging.py; Chromium/WebKit messaging journeys |
| Friend codes/previews, requests, acceptance/decline, blocks | Implemented and locally verified | social.py; existing social/messaging tests; persistent rejection cooldown increased to 24 hours |
| Returning-user routing, persistent guests/account upgrades | Implemented and locally verified | launch.py, social.py; existing upgrade tests plus discovery lease/identity upgrade regressions |
| Public/private rooms, invitation revocation and host controls | Existing implementation preserved and tested | social.py; existing tests/test_social.py and messaging regressions |
| Text, pictures/GIFs, room chat and independent friend DMs | Existing implementation preserved and tested | messaging.py; test_messaging.py; browser upload, retry, keyboard and private-access checks |
| Default-off discovery consent | Implemented and locally verified | people.py, world.html, world.js; test_safety.py; direct-world first visit regression |
| Multi-tab, background, stale and revoked-session presence | Implemented and locally verified | discovery_leases; 32-second expiry, eight-tab cap, account-session binding, old guest lease cleanup; test_safety.py |
| Discovery pagination and non-sensitive cards | Implemented; bounded local tests | people.py; 12-result pages/100-row scan, signed viewer-bound cursor, separate avatar/stats consent; synthetic loopback measurements |
| Consistent tap-to-profile and actions | Implemented; browser layouts verified | people.js, people-room.js, home.js, messages.js, room-control.js; native room/chat entry points reuse the panel; TypeScript checked, physical devices untested |
| Accepted-friend messaging only; no second social system | Implemented and locally verified | existing social.py/messaging.py reused; block, acceptance, unauthorized access and media regressions |
| Authorized reports for all requested source types | Implemented and locally verified | platform_safety.py; profile/user/DM/room text/media/room/invitation capture; private-access, duplicate/flood, race and block tests |
| Minimal retained evidence and justified access | Implemented and locally verified | separate safety tables, 30-day evidence, 180-day case/appeal cleanup; copied evidence survives source deletion; permission/expiry tests |
| Guidelines and appeals | Implemented and locally verified | /community-guidelines, /safety; private owner restrictions/appeal workflow, named staff decisions and explicit reversal |
| Extend existing dashboard, not replace it | Implemented and browser verified | admin_panel.py/admin.html/admin-safety.js; report queues, evidence, assignments, reviews, appeals, inventories, staff and switches remain under /ops/solace |
| Named staff, MFA, roles, granular permissions, last admin | Implemented and locally verified; owner enrollment required | staff_auth.py/setup_staff.py; TOTP reference vector/replay, role denial/session revocation/last-admin tests and browser login/logout |
| Attributable append-only action audit | Implemented and locally verified, with documented limits | platform_safety.py; transactional main-DB audit, update/delete triggers and HMAC verification; not external immutable storage; cross-DB staff changes use intent/outcome |
| Platform restrictions, bans, session revocation | Implemented and locally verified | centralized gate; immediate next-request enforcement, account and copied-guest-cookie revocation, member/lease removal, host succession, feature gates and reversal; native/web player exit paths |
| Independent emergency switches | Implemented and locally verified | persisted switches for seven features; explicit semantics in SAFETY-OPERATIONS.md; controls do not interrupt unrelated playback |
| Abuse controls | Implemented bounded protection; infrastructure required | identity/IP request budgets, persistent cooldowns, staff limits, input validation, upload caps, expiring leases and bounded pages; no automatic report-count punishment; no complete DDoS guarantee |
| Operational privacy review | Implemented and locally verified | new room-text archiving off by default; named staff raw telemetry redacted; unrestricted chat export disabled; justified evidence path; DM bodies excluded from telemetry |
| Public SEO and feature content | Implemented and locally verified | central PUBLIC/seo, Jinja pages, metadata, canonicals, sitemap/robots; 14 public pages only; private routes noindex/no-store and authorized |
| Playback, queue, chat and all three games | Preserved; existing automated regressions rerun | backend suite, browser game/keyboard and synthetic playback checks; real phone acceptance remains outstanding |
| Release packaging and deployment | Generated and checksum verified | tools/build_release.py, Dockerfile, startup/restart migration tests, release/MANIFEST.json; see safety-verification.json for final archive results |
| Real iOS/Android, sustained WAN capacity and public readiness | Blocked by available hardware/operator setup | no phones available; unsigned exports/engine emulation only. Domain/contact/SMTP, named staff enrollment, dependency advisory and infrastructure acceptance remain owner launch gates |

Verification output is summarized in audit-results/safety-verification.json and SAFETY-OPERATIONS.md. Implemented behavior is distinct from physical-device, production-capacity and deployment assumptions. No ranking, abuse-prevention or unrestricted production-readiness claim is made.
