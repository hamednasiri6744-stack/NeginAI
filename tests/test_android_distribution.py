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


def test_android_update_blocks_app_until_download_or_install_finishes():
    activity = open(
        "android/SellerNavigator/app/src/main/java/ir/neginpakhsh/seller/AssistantActivity.kt",
        encoding="utf-8",
    ).read()

    assert "private lateinit var updateOverlay" in activity
    assert "progressBarStyleLarge" in activity
    assert "showUpdateLock" in activity
    assert "hideUpdateLock" in activity
    assert "DownloadManager.STATUS_SUCCESSFUL" in activity
    assert "Context.RECEIVER_EXPORTED" in activity
    assert "takeIf { it.exists() }" in activity
    assert "updateOverlay.visibility == View.VISIBLE -> Unit" in activity


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
