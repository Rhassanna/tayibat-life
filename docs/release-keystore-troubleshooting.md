# Android release keystore troubleshooting

Use this when the Android Release AAB workflow fails in the `Decode release keystore` step.

## What the workflow checks

The workflow reads the `ANDROID_KEYSTORE_BASE64` GitHub secret, removes CRLF, newlines, tabs, and spaces, validates that the remaining value is base64, decodes it into `android/release-key.jks`, and confirms that the decoded keystore is not empty.

The workflow only prints safe diagnostics:

- Normalized base64 length
- Decoded keystore file size

It never prints the secret value or the decoded keystore.

## Invalid base64

If the workflow prints:

```text
ANDROID_KEYSTORE_BASE64 is invalid.
Download temporary-android-release-keystore artifact and paste the FULL content of release-key.base64.txt into the GitHub secret.
```

the GitHub secret is not the exact base64 text generated from the release keystore.

Fix:

1. Run the `TEMP Generate Android Release Keystore` workflow if you need a fresh temporary artifact.
2. Download the `temporary-android-release-keystore` artifact.
3. Open `release-key.base64.txt`.
4. Copy the full file content.
5. Replace the `ANDROID_KEYSTORE_BASE64` GitHub secret with that full content.

## Wrong file copied

`ANDROID_KEYSTORE_BASE64` must contain the text from `release-key.base64.txt`.

Do not paste:

- `release-key.jks`
- `github-secret-values.txt`
- A path to a file
- A downloaded zip file
- Only part of the base64 text

The raw `.jks` file is binary. It is not valid text for a GitHub secret unless it has first been base64 encoded.

## CRLF, spaces, and copied formatting

The release workflow now removes CRLF, newlines, tabs, and spaces before validating the secret. This makes normal copy/paste line wrapping safe.

If the secret still fails, the copied value likely contains something other than base64 text, such as quotes, labels, punctuation, or missing characters.

## Secret truncation

A truncated secret usually fails validation or decodes to an unusable keystore.

Compare the safe length shown in the workflow log with the size of `release-key.base64.txt` from the downloaded artifact. The numbers should match after removing whitespace.

If they do not match, replace the GitHub secret by copying the full `release-key.base64.txt` content again.

## Missing secret

If the workflow prints that `ANDROID_KEYSTORE_BASE64` is required, the secret is missing or empty.

Fix:

1. Go to the repository GitHub Secrets settings.
2. Create or update `ANDROID_KEYSTORE_BASE64`.
3. Paste the full content of `release-key.base64.txt`.
4. Confirm the other signing secrets also exist:
   - `ANDROID_KEYSTORE_PASSWORD`
   - `ANDROID_KEY_ALIAS`
   - `ANDROID_KEY_PASSWORD`

## Fallback behavior

If `ANDROID_KEYSTORE_BASE64` is present but invalid, the release workflow checks for an existing keystore in the workflow workspace before failing:

- `android/release-key.jks`
- `release-key.jks`

If one exists and is not empty, the workflow uses it and prints only the file size. If no fallback file exists, the workflow fails with the precise invalid-secret message.
