# Google Play Release Status

Generated: 2026-06-06

## Summary

The Android release AAB pipeline is configured, but the signed release AAB has not been generated yet from this environment.

Current status:

- AAB generated: No
- Expected artifact: `tayibat-life-release-aab`
- Expected file: `tayibat-life-release.aab`
- Signing config: Configured for release builds
- Release workflow: Present and manual-only
- Release readiness: Blocked until GitHub signing secrets are saved and the release workflow is run

## Verified Configuration

`android/app/build.gradle` reads signing values from:

```text
android/key.properties
```

The release build applies signing only when `android/key.properties` exists and contains:

```text
storeFile
storePassword
keyAlias
keyPassword
```

The release workflow `.github/workflows/android-release-aab.yml`:

- Uses `workflow_dispatch`
- Uses Node.js 22
- Uses Temurin Java 21
- Runs `npm ci`
- Runs `npm run validate`
- Runs `npm run cap:sync`
- Decodes `ANDROID_KEYSTORE_BASE64` to `android/release-key.jks`
- Creates `android/key.properties`
- Runs `cd android && ./gradlew bundleRelease --stacktrace`
- Renames `app-release.aab` to `tayibat-life-release.aab`
- Uploads artifact `tayibat-life-release-aab`

## Keystore Artifact

The temporary keystore workflow succeeded:

```text
Workflow: TEMP Generate Android Release Keystore
Run ID: 27061390393
Artifact: temporary-android-release-keystore
Artifact ID: 7454101429
Artifact size: 4661 bytes
Expires: 2026-06-07T11:44:40Z
```

Expected artifact contents:

```text
release-key.jks
release-key.base64.txt
```

I could read the artifact metadata through the GitHub API, but downloading the artifact bytes returned:

```text
401 Requires authentication
```

Because this environment has no `gh` CLI and no `GITHUB_TOKEN` or `GH_TOKEN`, I could not automatically download the artifact, create repository secrets, or dispatch the release workflow.

## Required GitHub Secrets

Create these repository secrets in GitHub:

```text
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_ALIAS
ANDROID_KEY_PASSWORD
```

Use these values:

```text
ANDROID_KEYSTORE_BASE64 = contents of release-key.base64.txt
ANDROID_KEYSTORE_PASSWORD = keystore password entered when running the temporary keystore workflow
ANDROID_KEY_ALIAS = tayibat-life
ANDROID_KEY_PASSWORD = key password entered when running the temporary keystore workflow
```

The passwords are not stored in this repository and are not recoverable from the workflow files. Use the exact values entered in the successful temporary keystore workflow run.

## Manual Next Steps

1. Open the successful temporary keystore workflow run:

   ```text
   https://github.com/Rhassanna/tayibat-life/actions/runs/27061390393
   ```

2. Download artifact `temporary-android-release-keystore`.
3. Extract the artifact.
4. Copy the full single-line contents of `release-key.base64.txt`.
5. Add the four GitHub repository secrets listed above.
6. Run the manual workflow:

   ```text
   Actions > Android Release AAB > Run workflow
   ```

7. After it succeeds, download artifact `tayibat-life-release-aab`.
8. Extract `tayibat-life-release.aab`.
9. Upload `tayibat-life-release.aab` to Google Play Console.
10. Delete the temporary workflow:

    ```text
    .github/workflows/generate-keystore.yml
    ```

## Remaining Blockers

- GitHub signing secrets are not confirmed as saved.
- The release AAB workflow has not been run after secrets were configured.
- The signed `tayibat-life-release.aab` artifact has not been verified yet.
- `app-ads.txt` uses a placeholder publisher ID and must be replaced before production ads.
- `assets/config/admob.config.json` uses placeholder AdMob IDs and test mode remains enabled.
- `privacy.html` exists and mentions advertising, but the localized policy text should be reviewed before production release.
