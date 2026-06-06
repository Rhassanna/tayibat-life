# Signed Android Release AAB Guide

This guide explains how to create a signed Android App Bundle for Tayibat Life using the manual GitHub Actions workflow named `Android Release AAB`.

The workflow creates an artifact named `tayibat-life-release-aab` that contains:

```text
tayibat-life-release.aab
```

## 1. Generate a release keystore

Generate the keystore locally and keep it private. Do not commit it to Git.

From the repository root:

```bash
keytool -genkeypair \
  -v \
  -keystore android/release-key.jks \
  -alias tayibat-life \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000
```

Choose strong passwords for the keystore and key. Save these values securely because Google Play releases depend on them.

Recommended values to record in a password manager:

```text
Keystore file: android/release-key.jks
Key alias: tayibat-life
Keystore password: your chosen password
Key password: your chosen password
```

## 2. Convert the keystore to base64

GitHub Secrets store text, so convert the keystore file to a single-line base64 value.

Linux:

```bash
base64 -w 0 android/release-key.jks > release-key.jks.base64
```

macOS:

```bash
base64 -i android/release-key.jks | tr -d '\n' > release-key.jks.base64
```

Windows PowerShell:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("android\release-key.jks")) | Set-Content -NoNewline release-key.jks.base64
```

Do not commit `release-key.jks`, `release-key.jks.base64`, or any password files.

## 3. Add GitHub Secrets

In GitHub, open the repository and go to:

```text
Settings > Secrets and variables > Actions > New repository secret
```

Create these four secrets:

```text
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_ALIAS
ANDROID_KEY_PASSWORD
```

Use the full single-line contents of `release-key.jks.base64` for `ANDROID_KEYSTORE_BASE64`.

Use the keystore password, key alias, and key password from the keystore generation step for the other three values.

## 4. Run the release workflow

Open:

```text
Actions > Android Release AAB > Run workflow
```

Select the branch to build, then click `Run workflow`.

The workflow will:

```text
npm ci
npm run validate
npm run cap:sync
decode ANDROID_KEYSTORE_BASE64 to android/release-key.jks
write android/key.properties
cd android && ./gradlew bundleRelease --stacktrace
upload tayibat-life-release-aab
```

## 5. Download the AAB

After the workflow succeeds:

1. Open the completed `Android Release AAB` run.
2. Scroll to `Artifacts`.
3. Download `tayibat-life-release-aab`.
4. Extract the artifact zip.
5. Use `tayibat-life-release.aab` for Google Play.

## 6. Upload to Google Play Console

In Google Play Console:

1. Open the Tayibat Life app.
2. Go to the target release track, such as `Internal testing`, `Closed testing`, or `Production`.
3. Create a new release.
4. Upload `tayibat-life-release.aab`.
5. Complete release notes and rollout settings.
6. Review and submit the release.

If Play App Signing is enabled, keep the upload keystore and passwords secure. Losing the upload key can block future releases until the key is reset through Google Play support.
