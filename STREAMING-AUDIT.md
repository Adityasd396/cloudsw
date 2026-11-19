# Solace streaming audit — 18 November 2026

Release 2026.11.18.2. All measurements were local, with disposable rooms, names, storage and synthetic media. Production was not contacted or changed. No personal media, chat history or credentials were used. No dependencies were installed system-wide.

## Implemented

- Room polling avoids unchanged heartbeat writes within one second. Game reads use read transactions; mutations retain write transactions. This removes unnecessary SQLite writer contention without changing stored schemas or playback command ordering.
- Direct media coalesces overlapping play promises, bounds transient abort retries, cancels stale retries on pause/source replacement, times out pending starts, and requires user intent after autoplay denial. Late metadata respects a newer pause. Non-seekable streams skip automatic drift seeks and report unavailable manual seeking. A late YouTube loader error cannot overwrite a direct-media notice.
- Docker now copies ludo_game.py, game_options.py and release.json. Its previous manifest could not import the application. A regression test copies the declared files into an isolated directory and imports the actual application.
- Love, heart glitter and clap reactions cover the screen for three seconds, including fullscreen. Effects are bounded, non-interactive, cleaned up and respect reduced motion. Native haptics use the existing settings and rate limits; browsers depend on device support. /iloveyou dialogue and media are unchanged.
- Ludo has selectable available colors before play, server validation, cute symbol pawns and pip-only dice. Both participants see the authoritative roll as a large shaded 3D die, including on the streaming screen. The public roll contains only its identity, value, time and display name. Switching color after starting is rejected.

## Playback architecture and boundaries

Flask/SQLite manages rooms, polling, chat, queue and revisioned playback intents. YouTube uses its player API on the web and provider pages in the native WebView. Direct HTTPS media is decoded by the client HTML video element; Flask does not download, proxy or transcode those URLs. The host is not a media server for the peer. Queue advancement remains server-authoritative and revision checked.

MP4 progressive/HTTP Range playback is supported when the source supports it. HLS depends on native browser support; the installed Chromium actually played the synthetic HLS fixture. There is no bundled DASH player, transcoder, DRM/Netflix integration or generic signed media-link service. Provider restrictions, advertising and mobile autoplay rules remain outside this audit's guarantees. Authentication/expiry fixtures below verify error handling, not a new authentication system for arbitrary third-party streams.

## Baseline and repeat measurements

Same machine, Waitress with eight threads, loopback HTTP, fresh disposable database each phase. Generated 18 seconds of H264/AAC, 640×360 at 30 fps, MP4 faststart, 1,914,020 bytes; also HLS segments. Each server run increases concurrency 1 → 2 → 4, 96 mixed requests per worker, 672 total requests per phase. Stop conditions: errors above 2%, server RSS above 512 MiB, CPU above 300% of one logical core, or request failure. None triggered. Four clients are a limited local sample, not a capacity certification.

Server table: four-client stage, 128 samples per operation; milliseconds unless stated. Baseline is the unmodified 2026.11.18.1 release, saved public modules in audit-results/baseline-source. Fingerprints in raw results distinguish phases. These are short runs; repeat under representative staging load before capacity decisions.

| Metric | Before p50 / p95 | After p50 / p95 |
|---|---:|---:|
| Room GET | 48.904 / 122.599 | 12.323 / 36.094 |
| Game GET | 8.065 / 78.433 | 8.625 / 15.969 |
| Full MP4 request | 11.315 / 24.299 | 18.367 / 25.501 |
| Mixed payload throughput, MiB/s | 76.714 | 147.115 |
| Server RSS, MiB, entire run | — / 47.277 | — / 47.383 |
| Server CPU, % of one core, entire run | 56.5 / 131.1 | 77.6 / 187.1 |

Both phases had zero HTTP errors. The room p95 improvement is approximately 71%; game p95 approximately 80%. Full media median became slower, so this is not evidence of faster media delivery. CPU time was 3.047 → 3.203 seconds, and peak CPU 141.7% → 227.5% of one core. Faster completion did not mean lower CPU consumption. Peak server RSS was 47.324 → 47.445 MiB.

Five isolated process startups, including import, temporary schema creation and first HTTP response: p50 878.805 → 875.394 ms, maxima 884.102 → 880.486 ms. No p95 is reported for five samples; no meaningful startup improvement is claimed.

Real browser playback uses actual H264/AAC decoding, 24 starts/seeks/resumes per phase, then five seconds of sustained playback, plus two/four concurrent players:

| Browser metric, ms | Before p50 / p95 | After p50 / p95 |
|---|---:|---:|
| Start to playing event | 29.55 / 520.9 | 29.35 / 103.4 |
| Seek completion | 4.5 / 5.6 | 4.5 / 5.8 |
| Resume event | 0.3 / 0.5 | 0.3 / 0.6 |

These small cached loopback event timings are not user-perceived WAN latencies. Browser/GPU warmup and caching vary: do not attribute the startup tail change to code. Both phases had zero normal-playback errors, zero unexpected rebuffers, and zero reported dropped frames in the sustained sample (159/158 total frames). Expected startup/seek waiting events are counted separately in the raw JSON. Two and four concurrent clients advanced successfully.

A requested 64 KiB/s, 100 ms browser network profile produced startup 1322.31 → 1300.33 ms and two rebuffers totaling 644.4 → 646.3 ms. Its nominal bandwidth is below this fixture's average bitrate; this remains the observed next playback constraint. Browser shaping on loopback is not a calibrated mobile WAN. A one-second offline interval was covered by the already buffered 18-second file; reconnect/reload played successfully. This does not test an exhausted buffer during a prolonged outage.

Browser/driver process-tree RSS p50/p95 was 523.506/701.344 → 529.516/748.926 MiB, peak 965.832 → 973.598 MiB across the multi-page run. These include Chromium and its helper processes, not just one player; no memory reduction or three-hour leak claim is supported.

I/O and network observations, before → after:

- Windows process I/O read 494,975,612 → 483,496,304 bytes; write 2,154,352 → 2,120,036 bytes. Windows process I/O includes network; it is not physical disk traffic.
- Host-wide physical disk read 475,136 → 32,768 bytes; write 6,846,464 → 12,891,136 bytes. These counters also include unrelated host activity and cannot isolate SQLite cost.
- Host NIC receive 6,848 → 14,052 bytes; send 5,721 → 31,298 bytes. These counters may exclude loopback and include unrelated traffic. The four-client measured response payload was 233.763 → 233.766 MiB; use payload throughput for this local benchmark.

## Failures, expected behavior and reproducible checks

| Case | Expected / baseline finding | Verified outcome and reproduction |
|---|---|---|
| Repeated heartbeat and game reads | Reads should not serialize as needless writes; baseline acquired writer locks | No-op heartbeat skips UPDATE; game GET uses BEGIN, POST BEGIN IMMEDIATE. test_stream_audit_fixes.py |
| Docker startup | Declared files must import app; baseline omitted required modules | Manifest-copy/import regression passes. Docker daemon unavailable; actual image build untested. test_stream_audit_fixes.py |
| Pending repeated play | One pending call; stale retries must not restart paused media | Coalescing, cancellation, timeout, bounded abort/autoplay handling pass. mobile/tests/direct-playback.test.cjs; check_reactions_results.py |
| Missing/malformed source | Recoverable error, no silent fake playback | Missing404/malformed container give browser media error4. Retry with valid source plays. measure_playback.py; check_direct_failures.py |
| Non-seekable source | Do not repeatedly seek an empty seekable range | Injected empty TimeRanges skips correction; manual seek is unavailable. check_direct_failures.py |
| Range/cache | Partial content and conditional cache behavior | Prefix/suffix206, unsatisfiable416, ETag304 with empty body. measure_playback.py |
| Protected/expired media | Respect source denial | Fixture unauthenticated401, authorized206, expired403. No token bypass or renewal invented. measure_playback.py |
| Interrupted/slow connection | Buffered playback continues; reconnect can retry | One-second buffered interruption and reload pass; slow-profile buffering measured above. measure_playback.py |
| Shared controls and queue | Both users converge, one next-track transition | Two-user pause/resume/seek, autoqueue, game independence and room deletion checks pass. check_stream_upgrade.py; check_game_polish.py; Python regression suite |
| Mobile keyboard/layout | Latest chat stays visible without changing player identity | Simulated iPhone viewport/Android resize, portrait/landscape and repeated keyboard cycles pass. check_experience_refinements.py. Physical devices untested |
| New effects/Ludo | Both clients receive once; no input interception or playback interruption | Three-second effects, preserved draft/focus, actual decoded video progress, color locks and shared result pass. check_reactions_results.py |

## Hardware and deployment

Verification completed: 81/81 Python tests, 65/65 client tests and 61/61 HTTP smoke assertions, including private administrator login/logout. Native type checking and both Android/iOS exports succeeded. Browser journeys passed for all three games with two users, keyboard models in both orientations, real direct-media autoqueue, reactions and dice results. Layout/synchronization fixtures are distinguished from actual decoded-media tests above.

Measured Windows laptop: eight physical/twelve logical cores, 15.71 GiB RAM, approximately 131.5 GiB free disk; RTX 3050 Laptop GPU with 4 GiB. Restricted CIM access prevented reliable CPU model and storage-type identification. FFmpeg is already installed; available encoder listings are not proof of actual hardware encoding performance. Application playback does not transcode, so a software-versus-GPU encoding benchmark would not measure this product's streaming path and was not run.

No measured server saturation at four clients justifies buying hardware or increasing the tested eight worker threads. Keep SQLite on local durable storage, use the supplied production server configuration, and measure realistic deployment concurrency before changing it. PythonAnywhere workers, WAN bandwidth, external providers, thermal/battery behavior, iOS Safari, Android browser hardware decoding and native haptic feel were not measured here. Native type checking and both platform exports validate source compatibility, not physical performance. Existing accelerated three-hour state tests do not replace a real three-hour two-phone session.

## Reproduce locally

Optional audit dependencies are listed in requirements-audit.txt; the running environment already contained them. FFmpeg and a Playwright Chromium browser must already be available. These audit endpoints must never be deployed publicly.

```powershell
python -B tools/generate_audit_media.py
python -B tests/run_stream_audit.py --port 8027
# In another terminal:
python -B tools/benchmark_local.py --base http://127.0.0.1:8027 --output after-server.json
python -B tests/measure_playback.py --base http://127.0.0.1:8027 --output after-playback.json
python -B tools/measure_startup.py --source workspace --output after-startup.json
python -B -m unittest discover -s tests -p 'test_*.py'
```

Browser application checks require a disposable application server at port8017. The same audit server can be started with --port 8017. Baseline public modules and original manifests are archived for provenance, not deployment. Full source ZIP contains the audit tools/results; the PythonAnywhere ZIP contains production code only.

Raw measurements: [before server](audit-results/before-server.json), [after server](audit-results/after-server.json), [before playback](audit-results/before-playback.json), [after playback](audit-results/after-playback.json), [before startup](audit-results/before-startup.json), [after startup](audit-results/after-startup.json), [hardware](audit-results/hardware.json).
