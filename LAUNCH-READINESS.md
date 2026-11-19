# Navigation cleanup — 19 November 2026

Version **2026.11.19.5** restores the verified current code from 59 conflicted files and fixes duplicated Home/Profile actions and embedded auth navigation. Local verification: 169 backend tests, 68 client tests, TypeScript and both mobile JS exports. Final browser and archive evidence is in audit-results/navigation-verification.json; physical phones and the operational launch gates below remain outstanding. Schema stays at version 8. No production deployment was performed.

# Community/navigation update — 19 November 2026

Version **2026.11.19.4** adds migration 8, uninterrupted room navigation through separate app surfaces, centralized persisted preferences and Open World community chat. Verified locally: **162 backend tests**, **68 client tests**, TypeScript, Android/iOS JS exports and **61 HTTP smoke checks**. Browser evidence covers community chat, unique tab counts, room-switch cancellation/approval, saved settings, media, moderation and existing playback/game/keyboard regressions. See UX-COMMUNITY.md and audit-results/community-verification.json for final checks and limitations. Chromium community checks use decoded synthetic video; WebKit uses a simulated player. Physical phones remain untested. The launch blockers below remain; this is not public deployment approval.

# Open World and safety update — 19 November 2026

Recommendation: **blocked for unrestricted public launch** until named staff enrollment, production domain/operator contact/SMTP, the existing mobile build-tool advisory and physical-device acceptance are resolved. Verified locally: 150 backend tests (23 new safety tests), 68 client tests, TypeScript, JavaScript syntax, 61 HTTP checks, Chromium/WebKit safety flows, keyboard models, all games and real synthetic playback/queue regressions. Local verification and exact limits are in SAFETY-OPERATIONS.md, OPEN-WORLD-REQUIREMENTS.md and audit-results/safety-verification.json. No production data was used and no deployment was performed.

# Messaging/media baseline — 19 November 2026

Version 2026.11.19.2 adds optional room names, short friend codes/previews, moonlit separate screens, private friend messaging and validated room/DM pictures and GIFs. See MESSAGING.md and audit-results/messaging-verification.json. Verified: 127 backend tests, 68 client tests, TypeScript, JavaScript syntax, 61 HTTP smoke checks, Chromium/WebKit flows, lost-response and offline retries, upload retry/in-flight cancellation, keyboard models, existing games and actual local synthetic playback. Android/iOS JS exports pass; signed binaries and physical devices are not verified.

A sequential loopback measurement with one synthetic attachment reduced unchanged-poll response size from 1,110 to 851 bytes; p50/p95 were 4.635/6.575 ms with full metadata and 4.349/4.804 ms with the revision hint (25 samples each). These are not WAN or capacity claims. Pictures are never embedded in polling JSON. Root source is authoritative; packaging is rebuilt by tools/build_release.py and must include messaging.py.

Public launch remains blocked by the operational/device/dependency items below. Follow-on discovery and moderation requirements are tracked separately; they must not be advertised before implementation and verification.

## Remaining launch gates (current release)

| Severity | Gate | Required acceptance |
|---|---|---|
| P1 | Named administrator enrollment is operator-controlled and has not been applied to production | Enroll individual MFA staff in the configured server instance; verify recovery access. |
| P1 | Production domain, operator identity/contact, SMTP and policy review | Configure and verify the real HTTPS deployment and account email flows; review the public terms/privacy and moderation process. |
| P1 | Existing unpatched mobile build-tool dependency advisory | Resolve or explicitly assess the documented picomatch advisory before release builds; do not mistake a passing JS export for a clean dependency audit. |
| P1 | Physical-device and signed-app acceptance unavailable | Test actual iPhone/Android keyboards, sound, rotation/fullscreen, media picker, background recovery and sustained playback. |
| P2 | Hosting capacity, monitoring and upstream abuse protection | Validate the intended host with bounded staging tests. SQLite state is supported only on the same local database files, not independent multi-host replicas. |
| P2 | Container/remote CI not executed here | Docker is unavailable locally. The updated workflow and deployment image still require their external build checks. |

Final local evidence: 150 backend tests (23 safety), 68 client tests, 56 browser-script syntax checks, TypeScript, both native JS exports, 61 HTTP checks, packaged Chromium/WebKit safety and messaging, keyboard models, all games and real synthetic playback/queue checks. Final loopback p50/p95: room poll 15.919/27.275 ms, discovery 29.288/34.723 ms, empty private inbox 16.128/29.153 ms (25 samples each). No errors at the small two/four-request concurrency check; this does not establish production capacity. The next scaling constraint remains same-file SQLite write contention and hosting limits, not a measured need for a hardware purchase. See audit-results/safety-measurements.json for sample limits.

---

# Returning-user release verification — 19 November 2026

The dashboard, persistent guest profiles/history, explicit friendships/privacy, public/private rooms and friend invitations are implemented. See RETURNING-USERS.md for behavior, migration 4 and rollout/rollback details. Existing unrestricted-public-launch blockers below remain; this update does not certify physical phones or enable production services.

| Check | Evidence |
|---|---|
| Backend | 112/112 tests passed. Final unit/integration suite includes identity restoration/expiry, guest avatars/upgrades, history access, friends/blocks/privacy, visibility, capacity, invite deduplication/accept/decline/expiry/revocation, bans, malformed inputs, native one-use handoff, restarts, migration and verified restore. A further 12 identity tests passed after clearing stale expiry notices. See `audit-results/returning-user-verification.json`. |
| Client | 67 Node tests passed, including cancellation without retry; TypeScript passed. Android and iOS JavaScript exports completed; these are not signed native binaries. |
| Two-user browser smoke | Chromium and WebKit passed saved guest visits, create/join without another name prompt, accepted friends/in-app invites, public visibility confirmation, responsive 390×844 / 844×390 / 1280×800 layouts and shared playback intent. Phone-sized and desktop screenshots saved in audit-results. The same check passed against the packaged release in both engines; zero application errors or unload diagnostics in that final run. |
| Keyboard/chat regression | 12 simulated iPhone visual-viewport/Android resize cycles passed across portrait/landscape: latest message visible, no overlap; simulated-player drift samples 0–0.029 s with real Flask transport. This is not a physical keyboard or decoded-media drift guarantee. |
| Actual media | Chromium two-player synthetic-media test passed playback, shared 3-second hugs, retained draft/video, guest upgrade/history, picture edit/remove and signout. WebKit decoded HTTPS media limitation remains documented below; WebKit identity/layout checks passed. |
| HTTP and games | 61/61 existing local HTTP smoke checks passed. All game rules remain covered by backend/client tests; two-player browser game checks are recorded in the verification artifact. |
| Isolation | Disposable local databases and synthetic media only. No production data, deployment, system-wide dependency install or paid service used. |

No new credentials are needed for these features. Configure the HTTPS production origin, operator contact and existing optional SMTP/YouTube services as documented. Native Home and Room tools require rebuilding the standalone apps and real-device acceptance. Discovery refreshes within its 2.5-second foreground polling interval; background tabs do not promise instant updates. Short room codes are independent of revocable invite links. No multi-server capacity claim is added. Guest blocks/bans are identity-scoped and can be evaded by creating another anonymous identity; public operation needs an abuse-response process.

---

# Solace public launch review — 18 November 2026

**Recommendation: blocked for an unrestricted public launch.** The implementation and local release are prepared. Production credentials/configuration, operator/legal decisions and real-device acceptance remain outstanding. A known unpatched advisory remains in the native build toolchain. A limited web beta can be considered only after the operational setup below and explicit acceptance of the listed limits. Production was not accessed, deployed, load tested or changed.

The web frontend is vanilla JavaScript/CSS with Flask/Jinja pages; native source uses React Native/Expo/WebView. SQLite holds rooms, chat, games, accounts and history; operations data is in a separate SQLite file. Room communication is HTTP polling (typically 500 ms playing, 750 ms paused, with background backoff), not WebSockets. Ordered revisions and request receipts protect shared controls. Read/write timeouts, bounded retries and cancellation are covered by client tests.

## Requirements and evidence

| Area | Implementation status | Verification / limit |
|---|---|---|
| Public branding and SEO | Implemented | Personal dedication removed; original film removed from public assets/ZIPs; eight Jinja-rendered public pages; configured-origin metadata, social image, JSON-LD, robots and public-only sitemap. Missing domain keeps indexing off. |
| Accounts and guests | Implemented | Scrypt hashes; revocable hashed 30-day sessions; CSRF, secure cookies and limits; registration preserves the guest UID/history; signout rotates it. Recovery/verification use one-use hashed email tokens. Mock SMTP tested; real delivery requires configuration. |
| Profiles and uploads | Implemented | Own-name/date/picture screens; JPEG/PNG/WebP content decoding, 2 MiB/16 MP limits; re-encoded private PNG with metadata stripped. Pillow 13.0.0 pinned after advisory verification. |
| Private history and activity | Implemented | Actual local playback samples plus server intent; deduplicated playback instances; timezone/local-midnight aggregation; query tokens stripped; deletion suppression is transactional; account deletion anonymizes companions. |
| User storage controls | Implemented | Admin default 50 MiB per identity, adjustable 1–1024 MiB; per-user override/reset; guest coverage; private support reference and usage. Quota stops new history/uploads, preserves data and never stops video/chat/games. Logical payload only; shared chat/backups and SQLite overhead are separate. |
| Authorization and security | Implemented/tested | Owner-only profiles/history/pictures; membership checks; host-only transfer; game turns; CSRF/CORS/origin checks; limits; HTTPS enforcement; safe request IDs; CSP on account/public/admin pages; no-store/noindex on private routes. No claim of a formal penetration test. |
| Playback and synchronization | Verified locally | Real H264/AAC decoding, start/pause/resume/seek, two/four concurrent players, autoqueue, invalid files, Range/cache/auth/expiry fixtures, HLS and reconnect. Two-account real-media soak improved drift p95 from 1.142 to 0.209 seconds. |
| All three games | Verified | Little Hearts & Stars / tic-tac-toe, Moonlight / Love Hoops, Little Ludo: legal turns, score/win/draw, dice, replay rejection, agreement/rematches, previews and two-user play. A player exit now resets affected games only. Rules are visible before play. Casual games do not promise competitive anti-cheat. |
| Persistence and recovery | Verified | Four additive migration versions; concurrent-process migration/write and restart test; verified SQLite online backups, safe new-directory restore, generation reset and session/email-token revocation. |
| Operations/deployment | Prepared | Readiness checks configuration, DB migrations and 256 MiB free-disk floor; private disk/DB metrics; structured request logs exclude bodies/query strings/identifiers. Bounded Waitress settings, shutdown, locks, CI and deployment tools supplied. |

## Highest-impact findings fixed

| Severity | Reproducible finding | Change and test |
|---|---|---|
| P0 | Personal film was a directly served static file | Removed from static/release; legacy Flask paths reject it; optional private licensed film requires admin enablement and room membership. Existing deployed static copies still require operator removal. |
| P1 | Installed Pillow 12.3.0 matched image-parser advisories, including EXIF handling | Project-local environment upgraded; production pins 13.0.0; uploads reject an older runtime. Same OSV dependency-closure audit now reports zero known advisories. Format/pixel/body restrictions remain. |
| P1 | Old guest cookies could retain an upgraded account's room authority | Invalid/revoked account sessions rotate identity; regression checks a copied pre-upgrade guest cookie. |
| P1 | History deletion could race a heartbeat and recreate the entry | Suppression check and history mutation share a write transaction; concurrent delete/heartbeat test passes. |
| P1 | Restore could revive valid account sessions/email links | Restore clears authentication and email tokens, preserves profiles/content and changes storage generation. |
| P1 | Docker ignore rules omitted required modules despite COPY declarations | Corrected build context/COPY list, pinned requirements; isolated manifest-import test passes. Actual Docker engine unavailable locally. |
| P1 | Leaving tic-tac-toe could erase an unrelated ongoing Ludo/Hoops state | Targeted participant-game cleanup, with an unrelated Ludo match preservation regression. |
| P2 | Room/game reads unnecessarily acquired SQLite writer locks | Prior release fix preserved; read/no-op-heartbeat regression tests pass. |
| P2 | Repeated play promises, stale metadata/pause and non-seekable correction could interrupt playback | Bounded/coalesced play controller, cancellation, intent checks and seekability guard preserved. Direct sources now use a 0.5-second correction tolerance with readiness/seeking guards and a 1.5-second correction cooldown. YouTube keeps its more conservative tolerance. |
| P2 | Authentication loaded picture BLOBs on every poll; bulk history deletion materialized all rows | Auth reads only picture presence; BLOB fetched only for an authorized image GET. Bulk deletion uses SQL subqueries in one transaction. |
| P2 | YouTube key setup used a shared temporary filename and permissive file creation | Unique private temporary file, fsync, atomic replacement and transactional once-only configuration; core setup tests pass. |

No server-side media proxy or transcoder exists. User-supplied direct media is fetched by each client. The server's YouTube request uses a fixed Google endpoint and encoded parameters; arbitrary media URLs are not fetched server-side. Consequently there is no user-controlled server media-fetch SSRF path or hardware-transcoding capacity to benchmark. Do not add one without a separate SSRF/size/redirect review.

## Measured performance

Windows laptop: eight physical/twelve logical cores, 15.71 GiB RAM, RTX 3050 Laptop GPU. All tests used loopback, disposable data and synthetic media. Gradual loads were 1/2/4 clients, 96 mixed operations per worker, 672 requests per run; stop limits were >2% errors, server RSS >512 MiB or CPU >300% of one logical core. No load stop condition fired. Four clients are a measurement ceiling, not a supported-user capacity claim.

Baseline is release 2026.11.18.2, already containing earlier contention fixes. Short runs are sensitive to host activity. The new security/features add some API/startup overhead; this is not represented as an across-the-board speedup.

| Metric | Before p50 / p95 | Launch p50 / p95 |
|---|---:|---:|
| Home DOMContentLoaded, ms, 24 fresh contexts | 147.9 / 192.2 | 22.05 / 47.4 |
| Home subresource requests | 36 / 36 | 1 / 1 |
| Home subresource transfer bytes | 197,088 / 197,088 | 7,841 / 7,841 |
| Room GET, ms, 4 clients / 128 samples | 9.139 / 18.652 | 11.666 / 25.197 |
| Game GET, ms, same workload | 7.865 / 12.567 | 9.048 / 15.000 |
| Full MP4 GET, ms, same workload | 16.417 / 23.413 | 17.332 / 28.643 |
| Server RSS, MiB, entire load run | — / 46.973 | — / 50.191 |
| Two-user direct-video drift, seconds, short real-media soak | 0.974 / 1.142 | 0.029 / 0.209 |

Authenticated steady-state room GET: p50 10.065 ms / p95 27.900 ms, 128 samples at four clients; zero request errors. Four synthetic accounts were created before this run, preserving normal signup limits. An earlier attempt exceeded the configured signup limit and correctly received 429; limits were not weakened to hide it.

Five process startups: median 898.151 → 1184.376 ms (max 902.475 → 1196.827); no p95 for five samples. This includes import and a fresh disposable schema, not PythonAnywhere cold start. Windows virtual-environment launcher child PIDs initially confused the timing harness; descendant verification/cleanup was corrected before recording these values.

Mixed response throughput: 180.061 → 150.462 MiB/s on loopback. CPU time 2.750 → 3.719 seconds; peak 186.5% → 212.4% of one logical core. Peak server RSS 47.031 → 50.352 MiB. These do not show saturation or justify a hardware upgrade. The server does not carry external video bandwidth.

Windows process I/O read/write deltas were 489,064,396/2,094,912 → 495,929,156/2,463,048 bytes; process I/O includes network. Host-wide disk read/write was 0/13,827,584 → 30,501,888/8,826,368 bytes. NIC receive/send was 43,937/19,366 → 11,170/21,442 bytes. Host counters include unrelated traffic and may exclude loopback; they cannot establish application disk/network savings. Measured payload throughput is reported separately.

The final decoded-media sample (24 each) had start p50/p95 30.45/533.6 ms, seek 4.6/5.9 ms and resume 0.4/0.5 ms; zero normal-playback errors/unexpected rebuffers and zero dropped frames in the sustained sample. These are cached local event timings, not WAN latency. Requested 64 KiB/s with 100 ms shaping produced two rebuffers totaling 633 ms; this is below the synthetic video's bitrate. A one-second connection interruption was covered by an already buffered file; reconnect/reload recovered. Prolonged unbuffered outages remain untested.

The repeated 121-second real playback soak had 55 drift samples, p95 0.209 s, max 0.899 s, zero browser errors, server RSS peak 50.02 MiB and API roundtrip p95 31.481 ms. It included pause/resume/seeks every 20 seconds and chat/rotations every 25 seconds. The acceptance target was 1.5 seconds; this is a short desktop-browser result. A separate accelerated three-hour replay passed 20,065 assertions across 4,253 polls in 94 seconds; it is not a real three-hour phone soak.

## Remaining launch gates, ranked

1. **P1 — Production setup and business decisions.** Set the real HTTPS origin/contact, persistent storage/secret and admin credentials. Configure SMTP, verify delivery and sender-domain setup. Review operator identity, eligible audience/jurisdiction, Privacy/Terms and backup rotation. None was invented. Full production mode refuses missing essential domain/contact/email configuration; a deliberately limited launch can set SOLACE_REQUIRE_EMAIL=0.
2. **P1 — Mobile/browser acceptance.** No physical Android/iPhone devices were available. Chromium real-media/account/game journeys pass. Installed WebKit passes account/picture/history/signout and simulated keyboard/layout checks. Its full local HTTPS/intercepted media fixture returned media error 4; a standalone real HTTP fixture played successfully. Cause between fixture/native networking/TLS is unresolved, so full Safari/iOS playback is not certified. Firefox is not installed. Native cookie handoff, thermal/battery/background behavior and a real three-hour session need actual phones.
3. **P1 for native build security — Unpatched upstream tool dependency.** npm audit reports 25 affected dependency entries stemming from picomatch GHSA-fc5q-39xc-vjpf, not 25 independently proven runtime exploits. The advisory lists no patched version. No forced Expo/React Native downgrade was applied. Both exported source maps (637/639 sources) contain no picomatch runtime source. This limits demonstrated exposure to build tooling, but the CI audit gate intentionally remains failing until a fix or documented risk acceptance. Use isolated time-limited builders without production secrets and do not accept untrusted glob configuration. [Advisory](https://github.com/advisories/GHSA-fc5q-39xc-vjpf).
4. **P2 — Capacity and operations.** Only local four-client capacity was measured. SQLite state sharing is tested across processes on one local instance directory; separate-instance/multi-machine deployment is unsupported. Keep one authoritative durable SQLite volume; do not assume network-filesystem WAL or independent replicas are safe. Measure staging, concurrent account hashing, email latency and representative long histories before increasing workers/resources. Schedule maintenance/backup retention and monitor provider search quota.

No evidence supports buying a GPU or adding transcoding hardware. The next demonstrated playback constraint is bandwidth/source/browser behavior; the next scale validation is realistic staging concurrency and SQLite write contention. Keep the tested eight-thread production setting until measurements justify a change.

## Setup, deployment and rollback

1. Use Python 3.13+ and the pinned requirements.lock; native source uses the committed npm lockfile and was checked with Node 26.13.0. The new Python environment here was project-local; system packages were not changed. Copy all contents of Solace-pythonanywhere.zip together, including new modules, templates/static files, lockfile and tools. Preserve instance/, existing keys and admin hash. Remove the old deployed static/media/for-jaanu.mp4, particularly when PythonAnywhere serves static directly.
2. Configure .env.example values in the process/WSGI environment **before importing app**. It is documentation, not an automatic dotenv loader. Required: SOLACE_ENV=production, SOLACE_PUBLIC_URL, SOLACE_CONTACT_EMAIL, persistent SECRET_KEY/file, secure cookies, admin password hash/file. SMTP uses SOLACE_SMTP_HOST, SOLACE_SMTP_PORT, SOLACE_SMTP_SSL, SOLACE_SMTP_USERNAME, SOLACE_SMTP_PASSWORD and SOLACE_MAIL_FROM, always TLS/STARTTLS. YOUTUBE_API_KEY or its saved server file enables search. Optional SOLACE_LOVE_VIDEO must be licensed and outside static; enable it in admin explicitly. SOLACE_INSTANCE_PATH can name an absolute persistent directory. Proxy trust flags must match a real trusted proxy that overwrites forwarded headers.
3. Before replacement, create and verify a new private backup directory:

```text
python tools/storage.py backup --instance instance --output backups/solace-backup-prelaunch
python tools/storage.py verify --backup backups/solace-backup-prelaunch
```

SQLite online backup includes committed WAL data. Secret/API/admin files are deliberately excluded; preserve them separately with restricted access and encryption. The two databases are individually consistent snapshots, not a cross-database atomic snapshot. Do not use a raw copy of an active database file alone.

4. Reload the WSGI app (or run the hardened serve.py behind HTTPS). Startup applies additive migrations; there is no manual destructive schema conversion. Check /api/health and /api/ready on the configured origin. Run tools/verify_deployment.py with --expected-version 2026.11.18.4; its optional --journey mutates one disposable room and must be explicitly authorized for a deployed host. CI definitions are supplied; external CI and actual Docker execution have not been run here.
5. Verify restore using a **new directory**, never overwriting live data:

```text
python tools/storage.py restore --backup backups/solace-backup-prelaunch --target restored-instance
```

Restore checks hashes/integrity, changes generation and revokes account/admin sessions and email links. Point an isolated app at that directory, check profiles/history/rooms and sign in again. For rollback, stop/reload into the saved compatible code and point at the verified new restore directory if data rollback is required. Keep the original instance untouched. Do not re-expose the old personal static film or silently downgrade the patched image library when rolling back.
6. Schedule owner-run maintenance hourly and verified-backup pruning according to the reviewed policy:

```text
python tools/maintenance.py --instance instance
python tools/storage.py prune --folder backups --days 7
```

Cleanup removes expired sessions/tokens, unclaimed guest history and 30-day operations data. Account history remains until its owner deletes it. Request-driven cleanup is a fallback; dormant records may persist until the next cleanup unless scheduling is configured. Hosting/platform access logs and off-host backup retention need their own configuration.

Monitor readiness/availability, 5xx and storage-busy rates, p95 handler latency, request volume, free disk, private DB sizes, provider quota errors, stale playback/reconnect/drift aggregates and failed mail delivery. Logs use server-safe request IDs, endpoint names, status and handler time; no bodies/query strings/email/media tokens are logged. Redact query strings in upstream access logs too. Waitress caps connections, headers/body and pending output, hides tracebacks, and drains with bounded shutdown. A disposable Windows CTRL_BREAK test exited in 1.063 seconds, retained committed state, passed integrity and released its listener; Linux SIGTERM remains a CI acceptance path.

## Verification inventory

99 Python tests; 66 client tests; 61 HTTP smoke assertions; JS syntax and native type checks; Android/iOS exports; account/quota/recovery UX; Chromium real media; WebKit account/keyboard checks; all-game two-user journeys; concurrent history delete and multi-process migration/restart; backup/restore/retention; shutdown; bounded benchmarks and two short decoded-media soaks. Mocked SMTP tests cover one-use/expiry/revocation and non-enumerating recovery responses; actual delivery is unverified. Some expected injected failure cases log 503 during tests.

Raw data lives in audit-results/ (launch-before/after-server, authenticated-server, page, startup, playback, soak, dependency and shutdown JSON). Previous audit measurements are retained as historical evidence, not substituted for this launch branch's results. No test suite proves absence of all vulnerabilities or production-scale compatibility.
