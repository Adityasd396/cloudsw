# Solace for Android and iPhone

This is the native phone client. Its top panel loads **https://m.youtube.com/** directly in a native WebView, not a YouTube iframe. Search, browse, and select videos on the actual mobile YouTube website. Chat, reactions, playlist order, and host controls are native app controls underneath.

For installed standalone apps that do **not** require Expo Go, see [the deployment guide](../DEPLOYMENT.md). The included `eas.json` has preview APK/iPhone internal-testing and production store profiles. The QR flow below is only for development previews.

Opening a video switches the top half to a player-focused view. Tap **Show page** to reveal the surrounding watch page or **Browse** to search the site again. **Expand** enlarges the player; **Chat** restores the split layout. The complete YouTube player and its controls remain intact. The Ad filter on/off control enables filtering and reloads the current page.

## Try on two phones

1. Install Expo Go from the official app store on each phone.
2. Connect both phones and this computer to the same Wi-Fi.
3. From the project root, double-click **start-mobile.bat**.
4. Scan the QR code in the launcher with Expo Go (Android) or the Camera app (iPhone). Expo may require you to sign into the same Expo account as the development server.
5. The server address is filled in automatically. Create a room on one phone. Use Invite to send the server address and room code to the other phone, then choose Join room there.

Keep the launcher open. If Windows asks about network access, allow your trusted private Wi-Fi network. No firewall settings are changed by the launcher. Guest Wi-Fi isolation, VPNs, and firewalls can prevent phone-to-computer connections.

If there are multiple network adapters and the auto-detected address is incorrect, enter the correct computer Wi-Fi IPv4 address in the phone's Room server field with port **8001**, or set `AFTERGLOW_LAN_IP` before launching. Never use `localhost` or `127.0.0.1` on the phone: that points to the phone itself.

## Watching together

- The host searches the YouTube website in the top panel and starts a video. The selected video, playback position, play, and pause state are sent to the Flask room.
- A following guest loads the same full YouTube watch page and corrects drift beyond about three seconds. Each phone may need one initial tap to enable video playback.
- Guests can tap **Browse freely** to explore YouTube without being sent back to the host's video. Tap **Follow host** to return.
- Tap **＋ Playlist** to add the currently open video, or paste a link in the Playlist tab. Hosts can move items up/down, remove items, play an item, or use Next.
- People lists participants and supports host handover. A participant can claim hosting after the host has disconnected for 30 seconds.
- The player observer only exchanges video URL, title, playback position, and state. It does not read Google login fields, cookies, or passwords, and server/session credentials are never injected into YouTube.

## Practical limits

This removes the **iframe embedding requirement**, not all YouTube restrictions. Google can still restrict in-app browser sign-in, age-restricted or private videos, regional availability, or playback in a WebView. The ad filter attempts to reduce advertising, but no account access control, age gate, payment requirement, or DRM is bypassed. Playback synchronization pauses during detected ads; differing ads or buffering can temporarily desynchronize phones. Backgrounded phones may suspend JavaScript, and guests may have to tap Play after returning. This client depends on YouTube's page structure, which can change. Real-device testing is required before treating it as a release build.

For phones on different networks, deploy Flask to a Python-capable HTTPS host with persistent storage and use that HTTPS address on both phones. An Expo tunnel forwards the app bundle; it does not publish the Flask room server. The current guest room model is intended for trusted groups, not an unrestricted public service.

## Development checks

```text
npm run check
node --test tests/sync.test.cjs
npx expo export --platform ios --platform android
```

The project can run in Expo Go. Store-ready standalone builds additionally require platform signing and Apple/Google developer accounts. No APK, IPA, App Store release, or verified two-phone playback is implied by a successful JavaScript export.

## Ad filtering

Ad filtering is on by default. The toolbar toggle saves your preference and reloads the page. Standalone builds include native request/content filters installed by the package postinstall script. Expo Go can only run the JavaScript page filter; it cannot load our native changes. The filter is not Brave's engine and cannot promise ad-free playback. See the deployment guide for filter behavior and native build limitations. Run `npm test` for filtering, sync, layout, and release-configuration checks.
