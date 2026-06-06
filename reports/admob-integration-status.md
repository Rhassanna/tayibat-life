# AdMob Integration Status

Generated: June 6, 2026

## Production IDs

- Android App ID: `ca-app-pub-4441958861355825~6983634337`
- Banner Ad Unit ID: `ca-app-pub-4441958861355825/8264926419`
- Interstitial Ad Unit ID: `ca-app-pub-4441958861355825/5478980972`

## Configuration

- `assets/config/admob.config.json` uses the production IDs with `bannerEnabled=true`, `interstitialEnabled=true`, `rewardedEnabled=false`, and `testMode=false`.
- `android/app/src/main/res/values/strings.xml` defines `admob_app_id` with the production Android App ID.
- `android/app/src/main/AndroidManifest.xml` includes `com.google.android.gms.ads.APPLICATION_ID` metadata pointing to `@string/admob_app_id`.
- `@capacitor-community/admob` is installed and synced into the Android project.
- `android/app/src/main/assets/public/assets/config/admob.config.json` is release/main synced with `testMode=false`.
- `android/app/src/debug/assets/public/assets/config/admob.config.json` overrides the asset for debug builds with `testMode=true`.

## Ad Placement

- Banner ads are enabled on the Home screen bottom only.
- Native Android banners use `ADAPTIVE_BANNER` at `BOTTOM_CENTER` for responsive width.
- The web fallback banner is also Home-only and responsive.
- Interstitial ads are throttled:
  - after 3 opened tips,
  - after 4 qualifying section navigations,
  - with a 4-minute cooldown after a shown interstitial.
- Interstitials are skipped for Premium users and guarded against repeat display while one is already showing.

## app-ads.txt

- Local root file is active and contains:
  `google.com, pub-4441958861355825, DIRECT, f08c47fec0942fa0`
- `npm run cap:sync` copied `app-ads.txt` into `www/` and Android web assets.
- Netlify routing/header entries were added for `/app-ads.txt`.
- Live verification attempted:
  - `https://tayibat-life.netlify.app/` returned 404.
  - `https://tayibat-life.netlify.app/app-ads.txt` returned 404.
- Result: local/deploy source is configured correctly, but the current live Netlify site is not reachable at that domain at verification time.

## Privacy Policy

- `privacy.html` was updated on June 6, 2026.
- The policy now discloses Google AdMob banner and interstitial ads and possible processing of device information, advertising identifiers, approximate location, ad interactions, and diagnostics.

## Commands

- `npm run validate`: passed.
- `npm run cap:sync`: passed.
- `android/gradlew assembleDebug`: attempted, blocked locally because no Android SDK is configured.
- `android/gradlew bundleRelease`: attempted, blocked locally because no Android SDK is configured.

## Build Status

- Local APK build: not generated locally; blocked by missing `ANDROID_HOME`/`android/local.properties`.
- Local release AAB build: not generated locally; blocked by missing `ANDROID_HOME`/`android/local.properties`.
- GitHub Actions has an `Android APK Build` workflow that installs the Android SDK and runs on push to `main`.
- GitHub Actions has an `Android Release AAB` workflow that installs the Android SDK but is manual `workflow_dispatch` only and requires release signing secrets.
