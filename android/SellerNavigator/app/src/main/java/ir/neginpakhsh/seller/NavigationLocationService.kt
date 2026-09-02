package ir.neginpakhsh.seller

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat

/** Keeps GPS alive during an explicitly active route and publishes fixes to the app only. */
class NavigationLocationService : Service(), LocationListener {
    companion object {
        const val ACTION_START = "ir.neginpakhsh.seller.action.START_NAVIGATION_LOCATION"
        const val ACTION_STOP = "ir.neginpakhsh.seller.action.STOP_NAVIGATION_LOCATION"
        const val ACTION_LOCATION = "ir.neginpakhsh.seller.action.NAVIGATION_LOCATION"
        const val EXTRA_LATITUDE = "latitude"
        const val EXTRA_LONGITUDE = "longitude"
        const val EXTRA_ACCURACY = "accuracy"
        const val EXTRA_HEADING = "heading"
        const val EXTRA_SPEED = "speed"
        const val EXTRA_TIMESTAMP = "timestamp"
        private const val CHANNEL_ID = "active_navigation"
        private const val NOTIFICATION_ID = 4102
    }

    private lateinit var locationManager: LocationManager
    private var listening = false

    override fun onCreate() {
        super.onCreate()
        locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }
        startForeground(NOTIFICATION_ID, navigationNotification())
        startLocationUpdates()
        return START_NOT_STICKY
    }

    @Suppress("MissingPermission")
    private fun startLocationUpdates() {
        if (listening || !hasLocationPermission()) return
        listening = true
        try {
            locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 2_000L, 3f, this)
            locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER)?.let(::publishLocation)
        } catch (_: IllegalArgumentException) { }
        try {
            locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 4_000L, 8f, this)
            locationManager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)?.let(::publishLocation)
        } catch (_: IllegalArgumentException) { }
    }

    private fun hasLocationPermission(): Boolean =
        ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    override fun onLocationChanged(location: Location) = publishLocation(location)

    private fun publishLocation(location: Location) {
        if (!location.latitude.isFinite() || !location.longitude.isFinite()) return
        sendBroadcast(Intent(ACTION_LOCATION).apply {
            setPackage(packageName)
            putExtra(EXTRA_LATITUDE, location.latitude)
            putExtra(EXTRA_LONGITUDE, location.longitude)
            putExtra(EXTRA_ACCURACY, location.accuracy)
            putExtra(EXTRA_HEADING, if (location.hasBearing()) location.bearing else Float.NaN)
            putExtra(EXTRA_SPEED, if (location.hasSpeed()) location.speed else Float.NaN)
            putExtra(EXTRA_TIMESTAMP, location.time.takeIf { it > 0L } ?: System.currentTimeMillis())
        })
    }

    override fun onDestroy() {
        if (listening) locationManager.removeUpdates(this)
        listening = false
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        val channel = NotificationChannel(CHANNEL_ID, "مسیریابی فعال", NotificationManager.IMPORTANCE_LOW).apply {
            description = "دریافت موقعیت برای راهنمایی مسیر روز"
            setShowBadge(false)
        }
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun navigationNotification(): Notification = NotificationCompat.Builder(this, CHANNEL_ID)
        .setSmallIcon(android.R.drawable.ic_menu_mylocation)
        .setContentTitle("مسیریابی نگین فعال است")
        .setContentText("موقعیت شما برای راهنمایی مسیر روز دریافت می‌شود.")
        .setOngoing(true)
        .setCategory(NotificationCompat.CATEGORY_NAVIGATION)
        .build()
}
