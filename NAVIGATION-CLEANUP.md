# Solace 2026.11.19.5 — Home and Profile cleanup

The authoritative root source was recovered from 144 merge conflicts in 59 files. Each newer resolved file matched the previously verified 2026.11.19.4 source archive, including its non-conflicting content. Originals are saved locally in `.openai/pre-navigation-merge-20261119.zip`; the separate UI baseline is `.openai/pre-navigation-ui-20261119.zip`. Neither backup contains the deployed database. No Git reset, production data access, secret rotation or public deployment was performed.

## Changes

- Home, Friends and Rooms render only their relevant sections. Their script skips requests for absent sections and stops periodic refresh while its embedded surface is hidden. Friend-code preview and room-refresh controls reject repeated submissions while pending.
- Home uses the shared profile entry instead of a second Edit profile link. Games/Public rooms shortcuts remain on mobile, where they are absent from the bottom menu, and disappear when desktop navigation provides them.
- Desktop active-room surfaces use the existing sidebar instead of a second matching row of destination tabs; compact tabs remain on mobile.
- Profile and History use one shared Return to room action. Without an active room, there is no misleading Back to watching link. Profile does not link to itself through the sidebar/mobile header. Recognized app screens no longer render the hidden marketing header. Room Settings uses its own correctly targeted return action, and embedded room tools tolerate an absent marketing header.
- Friends' Privacy settings link goes directly to `/settings#privacy`, distinct from the legal Privacy page. Account verification is offered only while unverified. Picture removal appears only when a picture exists; upload is disabled until a file is selected and after it is saved. Disabled buttons have a visible treatment.
- Sign-in, sign-out, account deletion and guest upgrade have one navigation owner. Embedded identity changes notify the room parent and do not independently redirect the child. The parent finishes guest upgrades by restoring CSRF/history identity and opening Home while retaining the player. Native WebView handoff behavior remains supported. Successful identity transitions keep their submit action locked.
- The room navigation bridge loads before form handlers, so fast taps cannot bypass an active-room confirmation. A personal video resurrected by the merge was preserved outside public assets; configured /iloveyou behavior was retained.
- Release packaging refuses unresolved conflict markers, invalid Python and invalid JSON before changing release files. Regression tests cover these rejection paths.

## Verification

See `audit-results/navigation-verification.json` and `audit-results/navigation-browser-results.json`. New backend tests cover screen-specific rendering, guest/account actions, verified-email state and release-source validation. Two-engine browser tests cover first/returning guests, signed-in users, names, picture upload/removal, screen-specific requests, portrait/landscape/desktop layouts, guest upgrade during playback, one auth transition, cancelled sign-out and host transfer. Existing messaging, community, invitations, visibility, keyboard, games and queue checks are also rerun.

Chromium uses decoded synthetic HTTPS media for active-room upgrade checks. WebKit uses a simulated player for those checks. Physical iPhone/Android keyboards and installed app acceptance remain untested. The local test report records transient SQLite retries and test-fixture limitations; no production capacity claim is made. Existing launch gates in LAUNCH-READINESS.md remain.

## Update

There is no new migration or environment variable; schema version remains 8. Use the complete generated **Solace-pythonanywhere.zip**, including all Python modules, templates and static assets. Preserve the existing instance directory, signing secret, account/guest cookies, API key and administrator credentials. Follow PYTHONANYWHERE.md for verified backups and reload steps. A reload can briefly reconnect playback; ordinary in-app navigation retains the player. Existing chat/room retention rules continue to apply. Native changes recovered from the prior verified release require rebuilding installed apps if they were not already updated.
