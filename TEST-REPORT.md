# Validation report — 12 November 2026

**Result: local automated checks pass; the hosted deployment has a room-deletion defect. Device acceptance testing remains open.**

Target: https://aditya211.pythonanywhere.com/ and the current local Flask/mobile source. Live mutations used newly created validation rooms. Local database tests used temporary databases. No private API keys or production database contents are included in the evidence.

## Results

| Test group | Result | Evidence |
| --- | --- | --- |
| Backend functional/regression | 18/18 pass | `validation-python-tests.txt` |
| Mobile/JavaScript regression | 11/11 pass | `validation-mobile-tests.txt` |
| Type checking | Pass | `validation-typecheck.txt` |
| iOS and Android JavaScript export | Pass, exit 0 | `validation-export.txt` |
| Local concurrency, bounds, error handling and access checks | 17/17 pass | `validation-local.json` |
| Hosted API journey, smoke and asset checks | 27/29 pass | `validation-live.json` |
| Hosted YouTube search | HTTP 200, 12 results, source `youtube` | `validation-live-search.json` |
| Focused hosted Leave reproduction | Fail: both Leave requests return HTTP 404; room remains HTTP 200 | `validation-live-lifecycle.json` |
| Production dependency advisory scan | 3 moderate package findings; no high/critical findings reported | `validation-npm-audit.json` |

Exports verify that JavaScript bundles can be generated. They do not establish successful native APK/IPA builds or device playback.

## Functional, regression and smoke coverage

Verified room creation and six-digit codes, joining, persisted names/chat, shared chat with emoji, typing state, creator control permissions, host transfer, playlist additions and ordering, Next selection, pause/resume/seek state propagation, ad-notice state propagation, and activity status data. Live home page and all five linked stylesheet/script assets returned HTTP 200. One real YouTube search returned 12 results.

Regression tests cover an old pause update arriving after Resume, native playback publication races, correction timing, presence thresholds, host permissions, room cleanup, and saved profiles. On the hosted server the stale pause returned HTTP 409 and did not undo Resume. Local cleanup tests verify that the final Leave deletes room-specific data while preserving saved names; reconnect grace and expiry also pass locally.

These are API/state and automated logic checks. They do not measure whether two physical phones render the same video frame, detect a real YouTube ad, or animate every keyboard emoji correctly.

## Non-functional checks

- **Bounded concurrency:** 120 local room reads across four workers all succeeded. Median 14.9 ms, p95 149.7 ms, maximum 256.0 ms. Twenty concurrent playlist writes retained all twenty unique items.
- **Hosted latency:** eight sequential health requests had median 883 ms and maximum 903 ms from this machine, including internet/TLS overhead. This is a small sample, not a server capacity test or a response-time SLA. A half-second polling interval does not imply half-second end-to-end synchronization.
- **Limits and errors:** the 100-item playlist bound, malformed JSON rejection (400), oversized request rejection (413), and rejection of cross-origin mutations passed locally.
- **Access boundaries:** unjoined callers cannot mutate chat/playback/queue/host state. Guests cannot operate host-only playback, ordering, removal or host transfer. Session HttpOnly and SameSite flags were checked locally. This is a targeted boundary check, not a penetration test or complete security audit.
- **Duration:** the backend's simulated three-hour timeline test passes. A real continuous two-to-three-hour playback/network/memory soak was not performed.

## Findings and next actions

### High: hosted room deletion is unavailable

Both participants' `POST /api/rooms/<code>/leave` requests returned HTML HTTP 404. A subsequent room GET returned HTTP 200. This reproduces the two failed live journey assertions: last Leave does not delete the room, and its invite remains usable.

The route exists in the local `app.py` and passes local regression tests. The hosted behavior is therefore inconsistent with the current source. Deploy the current backend and reload the PythonAnywhere web app, then rerun the live validation. No production deployment changes were made during testing. Test participants were marked inactive after the missing Leave route was detected; immediate removal could not be verified remotely.

### Moderate: dependency advisory needs review

`npm audit --omit=dev` reports three affected package entries (`minimatch`, `@expo/fingerprint`, `expo`) arising from one underlying glob-pattern denial-of-service advisory, GHSA-g3hv-75wg-m249. These are not three independent vulnerabilities. The chain is associated with Expo fingerprint tooling; exploitability in a shipped phone application was not established.

Review a compatible upstream fix and rerun the tests/export after updating. The audit suggests a major Expo version change; no forced dependency change was applied during this testing task.

## Remaining acceptance checks

Browser automation was unavailable because its connection closed. The following remain unverified: visual layout/accessibility, iPhone zoom and keyboard behavior, real iOS/Android play/pause/seek/autoplay/fullscreen, background/reconnect behavior on physical devices, actual ad detection/blocking, and a real three-hour stream with memory/network monitoring. Successful automated checks do not establish universal device compatibility or ad-free YouTube playback.

## Repeatable checks

Run from the project root:

```text
python -B -m unittest discover -s tests -v
npm test --prefix mobile
npm run check --prefix mobile
python -B tests/run_validation.py
python -B tests/run_validation.py --live
```

Run the export from `mobile`:

```text
npx expo export --platform ios --platform android
```

The reusable validation runner returns a nonzero exit code if any assertion fails. Live mode performs a bounded journey in its own new room, not a load test against production. The earlier `SMOKE-TEST.md` is historical; this report supersedes its deployment findings. Raw evidence records the actual run and is not rewritten to hide failures.
