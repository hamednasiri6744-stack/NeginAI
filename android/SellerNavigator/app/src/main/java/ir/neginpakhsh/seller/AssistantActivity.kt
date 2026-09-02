package ir.neginpakhsh.seller

import android.Manifest
import android.app.AlertDialog
import android.app.DownloadManager
import android.content.ActivityNotFoundException
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.media.AudioAttributes
import android.media.MediaRecorder
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.Settings as AndroidSettings
import android.print.PrintAttributes
import android.print.PrintManager
import android.speech.tts.TextToSpeech
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.GeolocationPermissions
import android.webkit.JavascriptInterface
import android.webkit.PermissionRequest
import android.webkit.URLUtil
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import android.util.Base64
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import okhttp3.Call
import okhttp3.Callback
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.util.Locale

/**
 * Android container for the complete Negin web application.
 *
 * Debug builds open the development server on the host machine. Release builds
 * open the production assistant. Cookies and WebStorage persist login sessions.
 */
class AssistantActivity : ComponentActivity() {
    private lateinit var root: FrameLayout
    private lateinit var webView: WebView
    private lateinit var progress: ProgressBar
    private lateinit var errorPanel: LinearLayout
    private lateinit var updateOverlay: LinearLayout
    private lateinit var updateStatus: TextView

    private var uploadCallback: ValueCallback<Array<Uri>>? = null
    private var geolocationCallback: GeolocationPermissions.Callback? = null
    private var geolocationOrigin: String? = null
    private var microphoneRequest: PermissionRequest? = null
    private var fullscreenView: View? = null
    private var fullscreenCallback: WebChromeClient.CustomViewCallback? = null
    private var updateDownloadId = -1L
    private var pendingUpdateUri: Uri? = null
    private var updateCheckInProgress = false
    private var updateReceiverRegistered = false
    private var waitingForUpdateSettings = false
    private var waitingForUpdateInstaller = false
    @Volatile private var orderVoiceRecorder: MediaRecorder? = null
    private var orderVoiceFile: File? = null
    private var navigationTts: TextToSpeech? = null
    private var printWebView: WebView? = null
    @Volatile private var navigationTtsReady = false
    private var navigationLocationReceiverRegistered = false

    private val navigationLocationReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action != NavigationLocationService.ACTION_LOCATION) return
            val latitude = intent.getDoubleExtra(NavigationLocationService.EXTRA_LATITUDE, Double.NaN)
            val longitude = intent.getDoubleExtra(NavigationLocationService.EXTRA_LONGITUDE, Double.NaN)
            if (!latitude.isFinite() || !longitude.isFinite()) return
            val accuracy = intent.getFloatExtra(NavigationLocationService.EXTRA_ACCURACY, Float.NaN)
            if (accuracy.isFinite() && accuracy > 100f) return
            val payload = JSONObject().apply {
                put("latitude", latitude)
                put("longitude", longitude)
                put("accuracy", accuracy.takeIf { it.isFinite() })
                put("heading", intent.getFloatExtra(NavigationLocationService.EXTRA_HEADING, Float.NaN).takeIf { it.isFinite() })
                put("speed", intent.getFloatExtra(NavigationLocationService.EXTRA_SPEED, Float.NaN).takeIf { it.isFinite() })
                put("timestamp", intent.getLongExtra(NavigationLocationService.EXTRA_TIMESTAMP, System.currentTimeMillis()))
            }
            webView.post {
                webView.evaluateJavascript(
                    "window.dispatchEvent(new CustomEvent('negin-native-location', {detail: ${payload}}));",
                    null
                )
            }
        }
    }

    private val httpClient = OkHttpClient()
    private val updateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action != DownloadManager.ACTION_DOWNLOAD_COMPLETE) return
            val completedId = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1L)
            if (completedId != updateDownloadId) return
            val manager = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            val successful = manager.query(
                DownloadManager.Query().setFilterById(completedId)
            ).use { cursor ->
                if (!cursor.moveToFirst()) false
                else cursor.getInt(cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_STATUS)) ==
                    DownloadManager.STATUS_SUCCESSFUL
            }
            if (!successful) {
                updateDownloadId = -1L
                hideUpdateLock()
                Toast.makeText(
                    this@AssistantActivity,
                    "دانلود به‌روزرسانی کامل نشد؛ دوباره تلاش کنید.",
                    Toast.LENGTH_LONG
                ).show()
                return
            }
            val uri = manager.getUriForDownloadedFile(completedId)
            if (uri == null) {
                updateDownloadId = -1L
                hideUpdateLock()
                Toast.makeText(this@AssistantActivity, "فایل به‌روزرسانی پیدا نشد.", Toast.LENGTH_LONG).show()
                return
            }
            updateDownloadId = -1L
            showUpdateLock("دانلود کامل شد؛ در حال بازکردن نصب…")
            installUpdate(uri)
        }
    }

    private val fileChooser = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        uploadCallback?.onReceiveValue(
            WebChromeClient.FileChooserParams.parseResult(result.resultCode, result.data)
        )
        uploadCallback = null
    }

    private val locationPermission = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        geolocationCallback?.invoke(geolocationOrigin, result.values.any { it }, false)
        geolocationCallback = null
        geolocationOrigin = null
    }

    private val microphonePermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        val request = microphoneRequest
        microphoneRequest = null
        if (
            granted && request != null && isTrustedWebOrigin(request.origin) &&
            request.resources.contains(PermissionRequest.RESOURCE_AUDIO_CAPTURE)
        ) {
            request.grant(arrayOf(PermissionRequest.RESOURCE_AUDIO_CAPTURE))
        } else {
            request?.deny()
            if (!granted) {
                Toast.makeText(
                    this,
                    "دسترسی میکروفن رد شد؛ از تنظیمات برنامه «نگین فروش» آن را فعال کنید.",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
        dispatchMicrophonePermission(granted)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
        buildLayout()
        configureNavigationVoice()
        configureWebView()
        refreshWebShellForInstalledVersion()
        configureBackNavigation()
        registerUpdateReceiver()
        registerNavigationLocationReceiver()

        webView.loadUrl(BuildConfig.ASSISTANT_URL)
        if (!BuildConfig.DEBUG) checkForUpdate(manual = false)
    }

    override fun onResume() {
        super.onResume()
        if (waitingForUpdateSettings) {
            waitingForUpdateSettings = false
            val uri = pendingUpdateUri
            if (
                uri != null &&
                (Build.VERSION.SDK_INT < Build.VERSION_CODES.O || packageManager.canRequestPackageInstalls())
            ) {
                pendingUpdateUri = null
                showUpdateLock("اجازه نصب فعال شد؛ در حال بازکردن نصب…")
                installUpdate(uri)
            } else if (uri != null) {
                pendingUpdateUri = null
                hideUpdateLock()
                Toast.makeText(
                    this,
                    "اجازه نصب نسخه جدید فعال نشد؛ می‌توانید دوباره تلاش کنید.",
                    Toast.LENGTH_LONG
                ).show()
            }
            return
        }
        if (waitingForUpdateInstaller) {
            waitingForUpdateInstaller = false
            hideUpdateLock()
        }
    }

    private fun buildLayout() {
        root = FrameLayout(this)
        webView = WebView(this)
        progress = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            visibility = View.GONE
        }
        errorPanel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            visibility = View.GONE
            setPadding(dp(28), dp(28), dp(28), dp(28))
            addView(TextView(this@AssistantActivity).apply {
                text = "ارتباط با نگین برقرار نشد"
                textSize = 20f
                gravity = Gravity.CENTER
                setTextColor(0xFF173D35.toInt())
            })
            addView(TextView(this@AssistantActivity).apply {
                text = if (BuildConfig.DEBUG) {
                    "سرور محلی پورت ۸۰۰۰ را بررسی کنید."
                } else {
                    "اینترنت گوشی را بررسی و دوباره تلاش کنید."
                }
                textSize = 15f
                gravity = Gravity.CENTER
                setPadding(0, dp(10), 0, dp(18))
                setTextColor(0xFF5E6E69.toInt())
            })
            addView(Button(this@AssistantActivity).apply {
                text = "تلاش دوباره"
                setOnClickListener { webView.reload() }
            })
        }
        updateOverlay = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            visibility = View.GONE
            isClickable = true
            isFocusable = true
            elevation = dp(24).toFloat()
            setBackgroundColor(0xF7FFFFFF.toInt())
            setPadding(dp(32), dp(32), dp(32), dp(32))
            addView(
                ProgressBar(
                    this@AssistantActivity,
                    null,
                    android.R.attr.progressBarStyleLarge
                ).apply { isIndeterminate = true },
                LinearLayout.LayoutParams(dp(72), dp(72)).apply {
                    gravity = Gravity.CENTER_HORIZONTAL
                    bottomMargin = dp(24)
                }
            )
            updateStatus = TextView(this@AssistantActivity).apply {
                text = "در حال دریافت نسخه جدید…"
                textSize = 18f
                gravity = Gravity.CENTER
                setTextColor(0xFF173D35.toInt())
            }
            addView(
                updateStatus,
                LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT
                )
            )
        }

        root.addView(
            webView,
            FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        )
        root.addView(
            errorPanel,
            FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        )
        root.addView(
            progress,
            FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(4),
                Gravity.TOP
            )
        )
        root.addView(
            updateOverlay,
            FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        )
        setContentView(root)
        ViewCompat.setOnApplyWindowInsetsListener(root) { view, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }
        ViewCompat.requestApplyInsets(root)
    }

    private fun refreshWebShellForInstalledVersion() {
        val preferences = getSharedPreferences("negin-web-shell", Context.MODE_PRIVATE)
        val cachedVersion = preferences.getInt("app-version-code", -1)
        if (cachedVersion == BuildConfig.VERSION_CODE) return
        webView.clearCache(true)
        preferences.edit().putInt("app-version-code", BuildConfig.VERSION_CODE).apply()
    }

    private fun showUpdateLock(message: String) {
        updateStatus.text = message
        updateOverlay.visibility = View.VISIBLE
        updateOverlay.bringToFront()
    }

    private fun hideUpdateLock() {
        updateOverlay.visibility = View.GONE
    }

    private fun configureWebView() {
        CookieManager.getInstance().apply {
            setAcceptCookie(true)
            setAcceptThirdPartyCookies(webView, true)
        }

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            cacheMode = WebSettings.LOAD_DEFAULT
            useWideViewPort = true
            loadWithOverviewMode = false
            builtInZoomControls = false
            displayZoomControls = false
            allowFileAccess = false
            allowContentAccess = true
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            mediaPlaybackRequiresUserGesture = false
            userAgentString = "$userAgentString NeginSellerAndroid/${BuildConfig.VERSION_NAME}"
        }
        webView.addJavascriptInterface(AndroidUpdateBridge(), "NeginAndroid")

        webView.webViewClient = object : WebViewClient() {
            override fun onPageStarted(view: WebView, url: String, favicon: Bitmap?) {
                errorPanel.visibility = View.GONE
                progress.visibility = View.VISIBLE
            }

            override fun onPageFinished(view: WebView, url: String) {
                progress.visibility = View.GONE
                CookieManager.getInstance().flush()
            }

            override fun onReceivedError(
                view: WebView,
                request: WebResourceRequest,
                error: WebResourceError
            ) {
                if (request.isForMainFrame) {
                    progress.visibility = View.GONE
                    errorPanel.visibility = View.VISIBLE
                }
            }

            override fun shouldOverrideUrlLoading(
                view: WebView,
                request: WebResourceRequest
            ): Boolean {
                val uri = request.url
                if (uri.scheme == "http" || uri.scheme == "https") {
                    val host = uri.host.orEmpty().lowercase()
                    if (
                        host == "ai.neginpakhsh.com" ||
                        host == "10.0.2.2" ||
                        host == "127.0.0.1"
                    ) return false
                }
                return openExternal(uri)
            }
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView, newProgress: Int) {
                progress.progress = newProgress
                progress.visibility = if (newProgress in 1..99) View.VISIBLE else View.GONE
            }

            override fun onShowFileChooser(
                webView: WebView,
                filePathCallback: ValueCallback<Array<Uri>>,
                fileChooserParams: FileChooserParams
            ): Boolean {
                uploadCallback?.onReceiveValue(null)
                uploadCallback = filePathCallback
                return try {
                    fileChooser.launch(fileChooserParams.createIntent())
                    true
                } catch (_: ActivityNotFoundException) {
                    uploadCallback = null
                    Toast.makeText(
                        this@AssistantActivity,
                        "برنامه‌ای برای انتخاب فایل روی گوشی پیدا نشد.",
                        Toast.LENGTH_LONG
                    ).show()
                    false
                }
            }

            override fun onPermissionRequest(request: PermissionRequest) {
                runOnUiThread {
                    val requestsAudio = request.resources.contains(
                        PermissionRequest.RESOURCE_AUDIO_CAPTURE
                    )
                    if (!requestsAudio || !isTrustedWebOrigin(request.origin)) {
                        request.deny()
                        return@runOnUiThread
                    }
                    if (
                        ContextCompat.checkSelfPermission(
                            this@AssistantActivity,
                            Manifest.permission.RECORD_AUDIO
                        ) == PackageManager.PERMISSION_GRANTED
                    ) {
                        request.grant(arrayOf(PermissionRequest.RESOURCE_AUDIO_CAPTURE))
                    } else {
                        microphoneRequest?.deny()
                        microphoneRequest = request
                        microphonePermission.launch(Manifest.permission.RECORD_AUDIO)
                    }
                }
            }

            override fun onPermissionRequestCanceled(request: PermissionRequest) {
                if (microphoneRequest === request) microphoneRequest = null
            }

            override fun onGeolocationPermissionsShowPrompt(
                origin: String,
                callback: GeolocationPermissions.Callback
            ) {
                if (
                    ContextCompat.checkSelfPermission(
                        this@AssistantActivity,
                        Manifest.permission.ACCESS_FINE_LOCATION
                    ) == PackageManager.PERMISSION_GRANTED
                ) {
                    callback.invoke(origin, true, false)
                } else {
                    geolocationOrigin = origin
                    geolocationCallback = callback
                    locationPermission.launch(
                        arrayOf(
                            Manifest.permission.ACCESS_FINE_LOCATION,
                            Manifest.permission.ACCESS_COARSE_LOCATION
                        )
                    )
                }
            }

            override fun onShowCustomView(view: View, callback: CustomViewCallback) {
                if (fullscreenView != null) {
                    callback.onCustomViewHidden()
                    return
                }
                fullscreenView = view
                fullscreenCallback = callback
                webView.visibility = View.GONE
                root.addView(
                    view,
                    FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                    )
                )
            }

            override fun onHideCustomView() = closeFullscreen()
        }

        webView.setDownloadListener { url, userAgent, contentDisposition, mimeType, _ ->
            try {
                val fileName = URLUtil.guessFileName(url, contentDisposition, mimeType)
                val request = DownloadManager.Request(Uri.parse(url)).apply {
                    addRequestHeader(
                        "Cookie",
                        CookieManager.getInstance().getCookie(url).orEmpty()
                    )
                    addRequestHeader("User-Agent", userAgent)
                    setMimeType(mimeType)
                    setTitle(fileName)
                    setNotificationVisibility(
                        DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED
                    )
                    setDestinationInExternalPublicDir(
                        Environment.DIRECTORY_DOWNLOADS,
                        fileName
                    )
                }
                (getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager)
                    .enqueue(request)
                Toast.makeText(this, "دانلود شروع شد.", Toast.LENGTH_SHORT).show()
            } catch (_: Exception) {
                openExternal(Uri.parse(url))
            }
        }
    }

    private inner class AndroidUpdateBridge {
        @JavascriptInterface
        fun checkForUpdate() {
            runOnUiThread { checkForUpdate(manual = true) }
        }

        @JavascriptInterface
        fun printHtml(title: String, html: String): Boolean {
            val safeTitle = title.trim().take(120)
            if (safeTitle.isEmpty() || html.isBlank() || html.length > 2_000_000) return false
            runOnUiThread { printHtmlDocument(safeTitle, html) }
            return true
        }

        @JavascriptInterface
        fun isPersianVoiceReady(): Boolean = navigationTtsReady

        @JavascriptInterface
        fun speakPersian(text: String): Boolean {
            val phrase = text.trim().take(500)
            if (!navigationTtsReady || phrase.isEmpty()) return false
            runOnUiThread {
                navigationTts?.speak(
                    phrase,
                    TextToSpeech.QUEUE_FLUSH,
                    null,
                    "navigation-${System.currentTimeMillis()}"
                )
            }
            return true
        }

        @JavascriptInterface
        fun stopNavigationVoice() {
            runOnUiThread { navigationTts?.stop() }
        }

        @JavascriptInterface
        fun hasMicrophonePermission(): Boolean =
            ContextCompat.checkSelfPermission(
                this@AssistantActivity,
                Manifest.permission.RECORD_AUDIO
            ) == PackageManager.PERMISSION_GRANTED

        @JavascriptInterface
        fun requestMicrophonePermission(): Boolean {
            if (hasMicrophonePermission()) return true
            runOnUiThread {
                microphonePermission.launch(Manifest.permission.RECORD_AUDIO)
            }
            return false
        }

        @JavascriptInterface
        fun startOrderVoiceRecording(): Boolean {
            if (!hasMicrophonePermission()) return false
            runOnUiThread { startNativeOrderVoiceRecording() }
            return true
        }

        @JavascriptInterface
        fun stopOrderVoiceRecording(): Boolean {
            if (orderVoiceRecorder == null) return false
            runOnUiThread { stopNativeOrderVoiceRecording() }
            return true
        }

        @JavascriptInterface
        fun startNavigationLocationTracking(): Boolean {
            if (ContextCompat.checkSelfPermission(this@AssistantActivity, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED &&
                ContextCompat.checkSelfPermission(this@AssistantActivity, Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED
            ) return false
            return try {
                val intent = Intent(this@AssistantActivity, NavigationLocationService::class.java)
                    .setAction(NavigationLocationService.ACTION_START)
                ContextCompat.startForegroundService(this@AssistantActivity, intent)
                true
            } catch (_: Exception) {
                false
            }
        }

        @JavascriptInterface
        fun stopNavigationLocationTracking() {
            stopService(Intent(this@AssistantActivity, NavigationLocationService::class.java))
        }
    }

    private fun printHtmlDocument(title: String, html: String) {
        printWebView?.destroy()
        val printableView = WebView(this)
        printWebView = printableView
        printableView.settings.javaScriptEnabled = false
        printableView.webViewClient = object : WebViewClient() {
            private var printStarted = false

            override fun onPageFinished(view: WebView, url: String) {
                if (printStarted) return
                printStarted = true
                try {
                    val printManager = getSystemService(Context.PRINT_SERVICE) as PrintManager
                    val adapter = view.createPrintDocumentAdapter(title)
                    val attributes = PrintAttributes.Builder()
                        .setMediaSize(PrintAttributes.MediaSize.ISO_A4.asLandscape())
                        .setColorMode(PrintAttributes.COLOR_MODE_COLOR)
                        .build()
                    printManager.print(title, adapter, attributes)
                } catch (_: Exception) {
                    Toast.makeText(
                        this@AssistantActivity,
                        "ساخت فایل PDF انجام نشد.",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }
        printableView.loadDataWithBaseURL(
            BuildConfig.ASSISTANT_URL,
            html,
            "text/html",
            "UTF-8",
            null
        )
    }

    private fun configureNavigationVoice() {
        navigationTts = TextToSpeech(this) { status ->
            if (status != TextToSpeech.SUCCESS) return@TextToSpeech
            val engine = navigationTts ?: return@TextToSpeech
            val languageResult = engine.setLanguage(Locale("fa", "IR"))
            navigationTtsReady = languageResult != TextToSpeech.LANG_MISSING_DATA &&
                languageResult != TextToSpeech.LANG_NOT_SUPPORTED
            engine.setSpeechRate(0.9f)
            engine.setPitch(1.0f)
            engine.setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
        }
    }

    private fun registerUpdateReceiver() {
        if (updateReceiverRegistered) return
        val filter = IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            // DownloadManager is a system component outside this app. Android 13+
            // requires an exported dynamic receiver for its completion broadcast.
            registerReceiver(updateReceiver, filter, Context.RECEIVER_EXPORTED)
        } else {
            @Suppress("DEPRECATION")
            registerReceiver(updateReceiver, filter)
        }
        updateReceiverRegistered = true
    }

    private fun registerNavigationLocationReceiver() {
        if (navigationLocationReceiverRegistered) return
        val filter = IntentFilter(NavigationLocationService.ACTION_LOCATION)
        ContextCompat.registerReceiver(
            this,
            navigationLocationReceiver,
            filter,
            ContextCompat.RECEIVER_NOT_EXPORTED
        )
        navigationLocationReceiverRegistered = true
    }

    private fun checkForUpdate(manual: Boolean) {
        if (updateCheckInProgress) return
        updateCheckInProgress = true
        val request = Request.Builder()
            .url(BuildConfig.UPDATE_URL)
            .header("Cache-Control", "no-cache")
            .build()
        httpClient.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, error: IOException) {
                runOnUiThread {
                    updateCheckInProgress = false
                    if (manual) Toast.makeText(
                        this@AssistantActivity,
                        "بررسی نسخه جدید انجام نشد؛ اتصال اینترنت را بررسی کنید.",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }

            override fun onResponse(call: Call, response: Response) {
                response.use {
                    val payload = if (it.isSuccessful) it.body?.string() else null
                    runOnUiThread {
                        updateCheckInProgress = false
                        if (payload == null) {
                            if (manual) Toast.makeText(
                                this@AssistantActivity,
                                "اطلاعات نسخه جدید از سرور دریافت نشد.",
                                Toast.LENGTH_LONG
                            ).show()
                            return@runOnUiThread
                        }
                        try {
                            val json = JSONObject(payload)
                            val versionCode = json.getInt("version_code")
                            if (versionCode <= BuildConfig.VERSION_CODE) {
                                if (manual) Toast.makeText(
                                    this@AssistantActivity,
                                    "آخرین نسخه نگین AI روی گوشی نصب است.",
                                    Toast.LENGTH_SHORT
                                ).show()
                                return@runOnUiThread
                            }
                            val versionName = json.optString("version_name", versionCode.toString())
                            val notes = json.optString("release_notes", "بهبود عملکرد و امکانات اپ")
                            val mandatory = json.optBoolean("mandatory", false)
                            val rawUrl = json.getString("download_url")
                            val downloadUrl = if (rawUrl.startsWith("http")) {
                                rawUrl
                            } else {
                                BuildConfig.NEGIN_BASE_URL + "/" + rawUrl.trimStart('/')
                            }
                            showUpdateDialog(versionName, notes, downloadUrl, mandatory)
                        } catch (_: Exception) {
                            if (manual) Toast.makeText(
                                this@AssistantActivity,
                                "پاسخ به‌روزرسانی معتبر نبود.",
                                Toast.LENGTH_LONG
                            ).show()
                        }
                    }
                }
            }
        })
    }

    private fun showUpdateDialog(
        versionName: String,
        releaseNotes: String,
        downloadUrl: String,
        mandatory: Boolean
    ) {
        val dialog = AlertDialog.Builder(this)
            .setTitle("نسخه جدید نگین AI")
            .setMessage("نسخه $versionName آماده است.\n\n$releaseNotes")
            .setPositiveButton("دانلود و نصب") { _, _ ->
                downloadUpdate(downloadUrl, versionName)
            }
        if (!mandatory) dialog.setNegativeButton("بعداً", null)
        dialog.setCancelable(!mandatory)
        dialog.show()
    }

    private fun downloadUpdate(downloadUrl: String, versionName: String) {
        showUpdateLock("در حال دریافت نسخه $versionName…\nلطفاً تا پایان به‌روزرسانی صبر کنید.")
        try {
            val fileName = "NeginAI-$versionName.apk"
            getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS)
                ?.resolve(fileName)
                ?.takeIf { it.exists() }
                ?.delete()
            val request = DownloadManager.Request(Uri.parse(downloadUrl)).apply {
                setMimeType("application/vnd.android.package-archive")
                setTitle("به‌روزرسانی نگین AI")
                setDescription("در حال دریافت نسخه $versionName")
                setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                setDestinationInExternalFilesDir(
                    this@AssistantActivity,
                    Environment.DIRECTORY_DOWNLOADS,
                    fileName
                )
            }
            updateDownloadId = (getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager)
                .enqueue(request)
            Toast.makeText(this, "دانلود به‌روزرسانی شروع شد.", Toast.LENGTH_SHORT).show()
        } catch (_: Exception) {
            hideUpdateLock()
            openExternal(Uri.parse(downloadUrl))
        }
    }

    private fun installUpdate(uri: Uri) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && !packageManager.canRequestPackageInstalls()) {
            pendingUpdateUri = uri
            waitingForUpdateSettings = true
            showUpdateLock("برای ادامه نصب، اجازه نصب برنامه را فعال کنید.")
            Toast.makeText(
                this,
                "اجازه نصب نسخه جدید را برای نگین AI فعال کنید.",
                Toast.LENGTH_LONG
            ).show()
            try {
                startActivity(
                    Intent(
                        AndroidSettings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                        Uri.parse("package:$packageName")
                    )
                )
            } catch (_: ActivityNotFoundException) {
                waitingForUpdateSettings = false
                pendingUpdateUri = null
                hideUpdateLock()
                Toast.makeText(this, "صفحه اجازه نصب اندروید پیدا نشد.", Toast.LENGTH_LONG).show()
            }
            return
        }
        try {
            showUpdateLock("نسخه جدید آماده نصب است…")
            waitingForUpdateInstaller = true
            startActivity(
                Intent(Intent.ACTION_VIEW).apply {
                    setDataAndType(uri, "application/vnd.android.package-archive")
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
            )
        } catch (_: ActivityNotFoundException) {
            waitingForUpdateInstaller = false
            hideUpdateLock()
            Toast.makeText(this, "نصب‌کننده اندروید پیدا نشد.", Toast.LENGTH_LONG).show()
        }
    }

    private fun configureBackNavigation() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                when {
                    updateOverlay.visibility == View.VISIBLE -> Unit
                    fullscreenView != null -> closeFullscreen()
                    else -> webView.evaluateJavascript(
                        "(function(){try{return Boolean(window.NeginAppNavigation && window.NeginAppNavigation.back());}catch(_error){return false;}})();"
                    ) { handled ->
                        if (handled != "true") {
                            if (webView.canGoBack()) webView.goBack() else finish()
                        }
                    }
                }
            }
        })
    }

    private fun closeFullscreen() {
        val view = fullscreenView ?: return
        root.removeView(view)
        fullscreenView = null
        webView.visibility = View.VISIBLE
        fullscreenCallback?.onCustomViewHidden()
        fullscreenCallback = null
    }

    private fun openExternal(uri: Uri): Boolean = try {
        startActivity(Intent(Intent.ACTION_VIEW, uri))
        true
    } catch (_: ActivityNotFoundException) {
        false
    }

    private fun isTrustedWebOrigin(origin: Uri): Boolean {
        val expected = Uri.parse(BuildConfig.ASSISTANT_URL)
        val current = Uri.parse(webView.url.orEmpty())
        fun sameOrigin(first: Uri, second: Uri): Boolean =
            first.scheme.equals(second.scheme, ignoreCase = true) &&
                first.host.equals(second.host, ignoreCase = true) &&
                first.port == second.port
        val safeCurrent = current.scheme.equals("https", ignoreCase = true) ||
            (BuildConfig.DEBUG && current.scheme.equals("http", ignoreCase = true))
        return sameOrigin(origin, expected) || (safeCurrent && sameOrigin(origin, current))
    }

    private fun dispatchMicrophonePermission(granted: Boolean) {
        webView.post {
            webView.evaluateJavascript(
                "window.dispatchEvent(new CustomEvent('negin-microphone-permission', " +
                    "{detail:{granted:${if (granted) "true" else "false"}}}));",
                null
            )
        }
    }

    @Suppress("DEPRECATION")
    private fun createOrderVoiceRecorder(): MediaRecorder =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) MediaRecorder(this)
        else MediaRecorder()

    private fun startNativeOrderVoiceRecording() {
        if (orderVoiceRecorder != null) {
            dispatchNativeOrderVoice("started")
            return
        }
        val file = try {
            File.createTempFile("negin-order-voice-", ".m4a", cacheDir)
        } catch (error: IOException) {
            dispatchNativeOrderVoice("failed", message = error.message.orEmpty())
            return
        }
        val recorder = createOrderVoiceRecorder()
        try {
            recorder.setAudioSource(MediaRecorder.AudioSource.MIC)
            recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            recorder.setAudioEncodingBitRate(96_000)
            recorder.setAudioSamplingRate(44_100)
            recorder.setOutputFile(file.absolutePath)
            recorder.prepare()
            recorder.start()
            orderVoiceFile = file
            orderVoiceRecorder = recorder
            dispatchNativeOrderVoice("started")
        } catch (error: Exception) {
            recorder.release()
            file.delete()
            dispatchNativeOrderVoice("failed", message = error.message.orEmpty())
        }
    }

    private fun stopNativeOrderVoiceRecording() {
        val recorder = orderVoiceRecorder ?: return
        val file = orderVoiceFile
        orderVoiceRecorder = null
        orderVoiceFile = null
        try {
            recorder.stop()
            recorder.release()
            val audio = file?.takeIf { it.isFile }?.readBytes() ?: ByteArray(0)
            if (audio.size < 128) {
                dispatchNativeOrderVoice("failed", message = "No audio data was captured")
            } else {
                dispatchNativeOrderVoice(
                    "completed",
                    Base64.encodeToString(audio, Base64.NO_WRAP)
                )
            }
        } catch (error: Exception) {
            recorder.release()
            dispatchNativeOrderVoice("failed", message = error.message.orEmpty())
        } finally {
            file?.delete()
        }
    }

    private fun dispatchNativeOrderVoice(
        state: String,
        audioBase64: String = "",
        message: String = ""
    ) {
        val detail = JSONObject().apply {
            put("state", state)
            put("mimeType", "audio/mp4")
            if (audioBase64.isNotEmpty()) put("audioBase64", audioBase64)
            if (message.isNotEmpty()) put("message", message.take(300))
        }
        webView.post {
            webView.evaluateJavascript(
                "window.dispatchEvent(new CustomEvent('negin-native-order-voice', " +
                    "{detail:$detail}));",
                null
            )
        }
    }

    override fun onDestroy() {
        orderVoiceRecorder?.release()
        orderVoiceRecorder = null
        orderVoiceFile?.delete()
        orderVoiceFile = null
        uploadCallback?.onReceiveValue(null)
        microphoneRequest?.deny()
        microphoneRequest = null
        webView.stopLoading()
        webView.webChromeClient = WebChromeClient()
        webView.webViewClient = WebViewClient()
        webView.destroy()
        printWebView?.stopLoading()
        printWebView?.destroy()
        printWebView = null
        httpClient.dispatcher.cancelAll()
        navigationTtsReady = false
        navigationTts?.stop()
        navigationTts?.shutdown()
        navigationTts = null
        stopService(Intent(this, NavigationLocationService::class.java))
        if (navigationLocationReceiverRegistered) {
            unregisterReceiver(navigationLocationReceiver)
            navigationLocationReceiverRegistered = false
        }
        if (updateReceiverRegistered) {
            unregisterReceiver(updateReceiver)
            updateReceiverRegistered = false
        }
        super.onDestroy()
    }

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density).toInt()
}
