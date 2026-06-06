# AdMob and Google Play Release Checklist

Generated: 2026-06-06

## Current AdMob Files

Verified files:

```text
app-ads.txt
privacy.html
assets/config/admob.config.json
```

Current placeholder fields:

```json
{
  "androidAppId": "ca-app-pub-XXXXXXXXXXXXXXXX~XXXXXXXXXX",
  "appId": "ca-app-pub-XXXXXXXXXXXXXXXX~XXXXXXXXXX",
  "bannerAdUnitId": "ca-app-pub-XXXXXXXXXXXXXXXX/XXXXXXXXXX",
  "interstitialAdUnitId": "ca-app-pub-XXXXXXXXXXXXXXXX/XXXXXXXXXX",
  "rewardedAdUnitId": "ca-app-pub-XXXXXXXXXXXXXXXX/XXXXXXXXXX",
  "testMode": true
}
```

Current `app-ads.txt` placeholder:

```text
google.com, pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0
```

Keep `testMode` set to `true` until AdMob app and ad unit IDs are approved and the app is ready for production ads.

## Google Play Upload Steps

1. Add the Android signing secrets in GitHub:

   ```text
   ANDROID_KEYSTORE_BASE64
   ANDROID_KEYSTORE_PASSWORD
   ANDROID_KEY_ALIAS = tayibat-life
   ANDROID_KEY_PASSWORD
   ```

2. Run:

   ```text
   Actions > Android Release AAB > Run workflow
   ```

3. Confirm the workflow succeeds.
4. Download artifact:

   ```text
   tayibat-life-release-aab
   ```

5. Extract:

   ```text
   tayibat-life-release.aab
   ```

6. Open Google Play Console.
7. Select the Tayibat Life app.
8. Upload `tayibat-life-release.aab` to an internal testing track first.
9. Complete store listing, content rating, data safety, target audience, and privacy policy requirements.
10. Review warnings and fix any policy or signing issues before production rollout.

## AdMob Setup Steps

1. Create or open the Tayibat Life Android app in AdMob.
2. Copy the AdMob Android app ID.
3. Create ad units:

   ```text
   Banner
   Interstitial
   Rewarded
   ```

4. Replace placeholders in `assets/config/admob.config.json`:

   ```text
   androidAppId
   appId
   bannerAdUnitId
   interstitialAdUnitId
   rewardedAdUnitId
   ```

5. Keep:

   ```json
   "testMode": true
   ```

6. Test the app through an internal test release.
7. After AdMob approval and policy review, switch to production IDs and set:

   ```json
   "testMode": false
   ```

## App Ads Verification

1. Replace `pub-XXXXXXXXXXXXXXXX` in `app-ads.txt` with the real AdMob publisher ID.
2. Deploy the web app so the file is available at:

   ```text
   https://<production-domain>/app-ads.txt
   ```

3. Confirm the file returns HTTP 200 and plain text.
4. In AdMob, open:

   ```text
   Apps > Tayibat Life > app-ads.txt
   ```

5. Wait for AdMob crawler verification.
6. Do not enable production ads until app-ads.txt is verified.

## Production Release Steps

1. Generate and upload the signed release AAB.
2. Run the app through internal testing.
3. Confirm app startup, navigation, local data storage, and offline behavior.
4. Confirm privacy policy URL is live and accurate.
5. Confirm AdMob remains in test mode during testing.
6. Confirm app-ads.txt is deployed and verified.
7. Replace AdMob placeholders with approved production IDs.
8. Disable AdMob test mode only after approval.
9. Create release notes.
10. Promote from internal testing to closed testing or production.

## Remaining AdMob Blockers

- Real AdMob Android app ID is not configured.
- Real banner, interstitial, and rewarded ad unit IDs are not configured.
- `app-ads.txt` still contains a placeholder publisher ID.
- AdMob test mode is intentionally enabled.
- Native Android AdMob dependency/plugin presence should be confirmed before production monetization testing.
