import hashlib
import json

from app.routes import android_app


def test_android_install_page_and_version_manifest(client, tmp_path, monkeypatch):
    apk = tmp_path / "NeginAI-1.2.0.apk"
    apk.write_bytes(b"signed-apk-test")
    metadata = {
        "version_code": 3,
        "version_name": "1.2.0",
        "file_name": apk.name,
        "sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "size_bytes": apk.stat().st_size,
        "mandatory": False,
        "release_notes": "test",
    }
    (tmp_path / "version.json").write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(android_app, "_release_dir", lambda: tmp_path)

    install = client.get("/install/android")
    assert install.status_code == 200
    assert "دانلود و نصب اپ اندروید" in install.text

    version = client.get("/app/android/version.json")
    assert version.status_code == 200
    assert version.json()["version_code"] == 3
    assert version.json()["download_url"] == "/download/android"

    download = client.get("/download/android")
    assert download.status_code == 200
    assert download.content == apk.read_bytes()
    assert download.headers["content-type"] == "application/vnd.android.package-archive"


def test_android_webview_requests_microphone_only_for_trusted_app_origin():
    manifest = open(
        "android/SellerNavigator/app/src/main/AndroidManifest.xml", encoding="utf-8"
    ).read()
    activity = open(
        "android/SellerNavigator/app/src/main/java/ir/neginpakhsh/seller/AssistantActivity.kt",
        encoding="utf-8",
    ).read()

    assert "android.permission.RECORD_AUDIO" in manifest
    assert "override fun onPermissionRequest(request: PermissionRequest)" in activity
    assert "PermissionRequest.RESOURCE_AUDIO_CAPTURE" in activity
    assert "isTrustedWebOrigin(request.origin)" in activity
    assert "ActivityResultContracts.RequestPermission()" in activity
    assert "fun hasMicrophonePermission()" in activity
    assert "fun requestMicrophonePermission()" in activity
    assert "negin-microphone-permission" in activity
    assert "fun startOrderVoiceRecording()" in activity
    assert "fun stopOrderVoiceRecording()" in activity
    assert "MediaRecorder.AudioSource.MIC" in activity
    assert "negin-native-order-voice" in activity


def test_android_webview_bridge_and_neshan_assets_are_origin_hardened():
    activity = open(
        "android/SellerNavigator/app/src/main/java/ir/neginpakhsh/seller/AssistantActivity.kt",
        encoding="utf-8",
    ).read()
    page = open("app/static/assistant.html", encoding="utf-8").read()

    assert "setAcceptThirdPartyCookies(webView, false)" in activity
    assert "allowFileAccess = false" in activity
    assert "detachNativeBridge()" in activity
    assert "attachNativeBridgeIfTrusted(url)" in activity
    assert "expectedIsSafe && sameOrigin(origin, expected)" in activity
    assert "callback.invoke(origin, false, false)" in activity
    assert page.count('integrity="sha384-') == 2
    assert page.count('crossorigin="anonymous"') == 2


def test_android_update_blocks_app_until_download_or_install_finishes():
    activity = open(
        "android/SellerNavigator/app/src/main/java/ir/neginpakhsh/seller/AssistantActivity.kt",
        encoding="utf-8",
    ).read()

    assert "private lateinit var updateOverlay" in activity
    assert "progressBarStyleLarge" in activity
    assert "showUpdateLock" in activity
    assert "hideUpdateLock" in activity
    assert ".followRedirects(false)" in activity
    assert "expectedSha256" in activity
    assert "MessageDigest.isEqual" in activity
    assert "verifyUpdatePackage(destination)" in activity
    assert "takeIf { it.exists() }" in activity
    assert "updateOverlay.visibility == View.VISIBLE -> Unit" in activity


def test_android_updater_pins_origin_path_hash_and_signing_certificate():
    activity = open(
        "android/SellerNavigator/app/src/main/java/ir/neginpakhsh/seller/AssistantActivity.kt",
        encoding="utf-8",
    ).read()
    manifest = open(
        "android/SellerNavigator/app/src/main/AndroidManifest.xml", encoding="utf-8"
    ).read()

    assert 'const val UPDATE_DOWNLOAD_PATH = "/download/android"' in activity
    assert "if (rawUrl != UPDATE_DOWNLOAD_PATH) return null" in activity
    assert '!base.scheme.equals("https", ignoreCase = true)' in activity
    assert "base.userInfo != null || base.query != null || base.fragment != null" in activity
    assert "it.priorResponse == null" in activity
    assert "metadataLength in 1L..MAX_UPDATE_METADATA_BYTES" in activity
    assert 'Regex("^[0-9a-f]{64}$")' in activity
    assert "written == length" in activity
    assert "candidate.packageName != packageName" in activity
    assert "signingCertificateHistory" in activity
    assert "installedCertificates.intersect(candidateCertificates).isNotEmpty()" in activity
    assert "androidx.core.content.FileProvider" in manifest
    assert '${applicationId}.update-files' in manifest


def test_android_webview_keeps_ordering_ui_above_system_navigation_and_refreshes_shell():
    activity = open(
        "android/SellerNavigator/app/src/main/java/ir/neginpakhsh/seller/AssistantActivity.kt",
        encoding="utf-8",
    ).read()
    script = open("app/static/assistant.js", encoding="utf-8").read()
    styles = open("app/static/previsit-workspace.css", encoding="utf-8").read()

    assert "WindowCompat.setDecorFitsSystemWindows(window, false)" in activity
    assert "WindowInsetsCompat.Type.systemBars()" in activity
    assert "systemBars.bottom" in activity
    assert "webView.clearCache(true)" in activity
    assert "webView.restoreState(savedInstanceState)" not in activity
    assert "negin-android-app" in script
    assert "html.negin-android-app .previsit-mobile-dock" in styles
    assert "--previsit-native-bottom-inset" in styles


def test_android_saved_request_can_open_system_pdf_print_dialog():
    activity = open(
        "android/SellerNavigator/app/src/main/java/ir/neginpakhsh/seller/AssistantActivity.kt",
        encoding="utf-8",
    ).read()

    assert "fun printHtml(title: String, html: String): Boolean" in activity
    assert "PrintManager" in activity
    assert "createPrintDocumentAdapter(title)" in activity
    assert "PrintAttributes.MediaSize.ISO_A4.asLandscape()" in activity
