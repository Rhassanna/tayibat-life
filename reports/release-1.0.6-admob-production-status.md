# Tayibat Life 1.0.6 AdMob Production Status

Date: 2026-06-08

## Root Cause

The APKPure 1.0.5 APK showed Google AdMob test creatives because the available APK workflow built and uploaded a debug APK with `assembleDebug`. Android debug builds include the tracked debug asset overlay at `android/app/src/debug/assets/public/assets/config/admob.config.json`, where `testMode` is intentionally `true`. The app code then passes that value to AdMob through `isTesting: isAdMobTestMode()`, so debug APKs request AdMob test ads.

The production/root config already used production AdMob IDs and `testMode=false`, but APKPure needs a release APK built from the release/main assets, not the debug artifact.

## Files Changed

- `.github/workflows/android-release-aab.yml`
- `android/app/build.gradle`
- `app.js`
- `index.html`
- `package.json`
- `package-lock.json`
- `scripts/validate-deploy.js`
- `sw.js`
- `reports/release-1.0.6-admob-production-status.md`

Generated but not committed:

- `www/`
- `android/app/src/main/assets/public/`
- `android/app/build/`
- `android/release-key.jks`
- `android/key.properties`
- `tmp/`

## Version

- `versionName`: `1.0.6`
- `versionCode`: `6`
- Web/package version: `1.0.6`
- App cache version: `v83`
- Package name: `com.tayibat.life`

## Final Artifact Paths

- Final APK: `android/app/build/outputs/apk/release/tayibat-life-1.0.6-apkpure-release.apk`
- Final AAB: `android/app/build/outputs/bundle/release/tayibat-life-1.0.6-release.aab`

## Build Notes

- `npm run validate`: passed.
- `npm run cap:sync`: passed.
- `assembleRelease bundleRelease`: passed.
- Android command-line tools were installed locally under `tmp/android-sdk`.
- The signed release APK was produced using the untracked local release keystore at `android/release-key.jks` because no release keystore was present in the workspace.

## AdMob Configuration

Release/main production config:

- `androidAppId`: `ca-app-pub-4441958861355825~6983634337`
- `appId`: `ca-app-pub-4441958861355825~6983634337`
- `bannerAdUnitId`: `ca-app-pub-4441958861355825/8264926419`
- `interstitialAdUnitId`: `ca-app-pub-4441958861355825/5478980972`
- `testMode`: `false`

Debug config:

- `android/app/src/debug/assets/public/assets/config/admob.config.json`
- `testMode`: `true`

## Verification Results

- APK contains exactly one AdMob config entry: `assets/public/assets/config/admob.config.json`.
- AAB contains exactly one AdMob config entry: `base/assets/public/assets/config/admob.config.json`.
- APK packaged AdMob config has `testMode=false`.
- AAB packaged AdMob config has `testMode=false`.
- APK packaged AdMob config contains the production App ID, banner unit ID, and interstitial unit ID.
- AAB packaged AdMob config contains the production App ID, banner unit ID, and interstitial unit ID.
- APK and AAB packaged AdMob configs do not contain `testMode=true`.
- APK and AAB packaged AdMob configs do not contain the Google sample ad unit prefix `ca-app-pub-3940256099942544`.
- APK package badging: `package: name='com.tayibat.life' versionCode='6' versionName='1.0.6'`.
- APK signature verification: `Verifies`.
- APK Signature Scheme v2: `true`.
- Local `app-ads.txt`, APK packaged `app-ads.txt`, AAB packaged `app-ads.txt`, and live `https://tayibat-life.netlify.app/app-ads.txt` all contain:
  `google.com, pub-4441958861355825, DIRECT, f08c47fec0942fa0`

## Production Ad Readiness

From the app/build side, real AdMob ads are ready for production in the 1.0.6 release APK and AAB: release artifacts use production AdMob IDs and `testMode=false`, while debug builds still use `testMode=true`.

Actual live ad fill still depends on AdMob account status, app/ad unit approval, policy status, inventory, and normal Google serving behavior.
