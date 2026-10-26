# App footage (optional)

Show the product instead of talking about it. There are three ways in, from the easiest:

## 1. The user provides recordings
Ask for screen recordings of the exact moments the video mentions: phone recordings (iOS Control Center → Screen
Recording, or Android Quick Settings → Screen record) or desktop recordings (OBS, QuickTime, `wf-recorder`).
Put them in `_inbox/`, then `ose broll ingest`. This is always the best fallback.

## 2. Web apps (any OS): agent-browser
```bash
npm i -g agent-browser && agent-browser install       # once (downloads Chromium)
scripts/capture_web.sh shot   https://myapp.dev hero               # phone viewport 430x932 @3x
scripts/capture_web.sh full   https://myapp.dev landing            # full-page (pan it as B-roll)
scripts/capture_web.sh record https://myapp.dev scroll-demo 8      # auto slow-scroll recording
# custom interaction:
scripts/capture_web.sh start https://myapp.dev signup-flow
agent-browser snapshot -i          # find refs
agent-browser click @e3; agent-browser fill @e5 "hello"; agent-browser scroll down 400
scripts/capture_web.sh stop
```
If the user gives a **repo**, run it locally first: read the README and package.json for the dev command, start
it in the background, wait until it's ready, capture `http://localhost:PORT`, then stop the server. Seed realistic
demo data and never record real secrets or personal data. Use `VIEWPORT="1280 800 2"` for desktop-style footage.

## 3. Native mobile apps
**Android (Linux/macOS/Windows):** Android SDK platform-tools plus an emulator (Android Studio AVD) or a USB
device with debugging enabled.
```bash
scripts/capture_android.sh devices
scripts/capture_android.sh launch com.example.app
scripts/capture_android.sh record onboarding 12        # records while you drive it from another shell:
scripts/capture_android.sh tap 540 1650 ; scripts/capture_android.sh swipe 540 1600 540 600 400
scripts/capture_android.sh demo com.example.app flow.txt   # scripted: lines like "tap 540 1650", "sleep 1", "text hello"
```
To build from a repo: `./gradlew installDebug` (native) or `npx expo run:android` / `npx react-native run-android`.

**iOS Simulator (macOS + Xcode only):** this is the "Mac Mini running an iPhone simulator that Claude taps" setup
from the original workflow.
```bash
scripts/capture_ios.sh boot "iPhone 16 Pro"
scripts/capture_ios.sh launch com.example.app
scripts/capture_ios.sh demo com.example.app flow.txt   # taps via idb (brew install facebook/fb/idb-companion; pip install fb-idb)
```
Build from a repo with `xcodebuild -scheme X -destination 'platform=iOS Simulator,name=iPhone 16 Pro'` or
`npx expo run:ios`. On Linux, iOS capture isn't possible: say so and fall back to option 1. A remote Mac over SSH
works too: run the script there and `scp` the file back.

## Tips
- Record 2–3× longer than needed and let the edit pick the best 2 s.
- Slow down: pause about 0.5 s after each tap so the viewer can follow. Use `sleep` lines in demo scripts.
- Use a clean status bar: `xcrun simctl status_bar booted override --time 9:41 --batteryLevel 100`, or Android
  demo mode.
- Phone footage is already vertical. Use `mode: "full"` B-roll, or `pip` to keep the face visible.
