# GitHub Cloud Android Build Guide

This project can build the Tayibat Life Android APK in GitHub Actions. You do not need local Administrator rights, Java, Android Studio, or the Android SDK on your Windows machine.

## What The Workflow Does

The workflow is saved at `.github/workflows/android-build.yml`.

It runs in GitHub's cloud runner and performs:

1. Ubuntu latest runner.
2. Node.js 20 setup.
3. Java 17 Temurin setup.
4. `npm ci`.
5. `npm run validate`.
6. `npm run cap:sync`.
7. Android debug APK build with Gradle.
8. APK upload as a GitHub Actions artifact.

The APK output path is:

```text
android/app/build/outputs/apk/debug/app-debug.apk
```

The uploaded artifact is named:

```text
tayibat-life-debug-apk
```

## Push The Project To GitHub

Create a new empty GitHub repository first, then run these commands from the Tayibat Life project folder:

```bash
git init
git add .
git commit -m "Prepare cloud Android APK build"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

If the repository is already initialized, use:

```bash
git add .
git commit -m "Prepare cloud Android APK build"
git push
```

## Run The APK Build

1. Open your GitHub repository.
2. Go to the `Actions` tab.
3. Select `Android APK Build`.
4. Click `Run workflow`.
5. Choose the branch, usually `main`.
6. Click the green `Run workflow` button.

The workflow also runs automatically when you push to `main` or `master`.

## Download The APK

1. Open the completed workflow run.
2. Scroll to `Artifacts`.
3. Download `tayibat-life-debug-apk`.
4. Unzip the downloaded file.
5. Install or share `app-debug.apk` for testing.

This APK is a debug build. It is useful for testing on Android devices, but it is not the final Google Play upload format.

## Build An AAB Later For Google Play

Google Play normally requires a signed release Android App Bundle, not a debug APK.

When you are ready for Play Store release, change or add a workflow build step like this:

```bash
cd android
./gradlew bundleRelease --stacktrace
```

The AAB output path will be:

```text
android/app/build/outputs/bundle/release/app-release.aab
```

For a real Play Store release, add Android signing secrets in GitHub Actions, such as:

```text
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_ALIAS
ANDROID_KEY_PASSWORD
```

Then configure the Android Gradle release signing step to decode the keystore during the workflow. Keep the keystore file and passwords private.

## Important Notes

- Local Java is not required.
- Local Android Studio is not required.
- Local Android SDK is not required.
- The app version remains controlled by the project files.
- The current Capacitor Android project already exists under `android/`.
- Capacitor uses `www` as the web build folder from `capacitor.config.json`.
