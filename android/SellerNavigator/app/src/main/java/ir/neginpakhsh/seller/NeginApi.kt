package ir.neginpakhsh.seller

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject

/** The only routes exposed to the phone are authenticated NeginAI endpoints. */
class NeginApi(context: Context) {
    private val prefs = EncryptedSharedPreferences.create(
        context,
        "seller_session",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )
    private val client = OkHttpClient.Builder().retryOnConnectionFailure(true).build()
    private val baseUrl = BuildConfig.NEGIN_BASE_URL.trimEnd('/')
    fun hasSession(): Boolean = !prefs.getString("cookie", null).isNullOrBlank()

    private fun request(path: String, builder: Request.Builder = Request.Builder()): Request {
        prefs.getString("cookie", null)?.let { builder.header("Cookie", it) }
        return builder.url("$baseUrl$path").header("Accept", "application/json").build()
    }

    suspend fun login(username: String, password: String) = withContext(Dispatchers.IO) {
        val body = JSONObject().put("username", username).put("password", password).toString()
            .toRequestBody("application/json; charset=utf-8".toMediaType())
        val response = client.newCall(Request.Builder().url("$baseUrl/auth/login")
            .post(body).header("Accept", "application/json").build()).execute()
        response.use {
            if (!it.isSuccessful) error("نام کاربری یا رمز عبور صحیح نیست.")
            val cookie = it.headers("Set-Cookie").firstOrNull { value -> value.startsWith("negin_session=") }
                ?.substringBefore(';') ?: error("نشست ورود دریافت نشد.")
            prefs.edit().putString("cookie", cookie).apply()
        }
    }

    suspend fun routes(): List<SellerRoute> = withContext(Dispatchers.IO) {
        json("/seller-workspace/routes").getJSONArray("routes").toRoutes()
    }

    suspend fun routePlan(routeId: String, origin: GeoPoint?, routeMode: String): Pair<List<RouteStop>, RouteLeg?> = withContext(Dispatchers.IO) {
        val queryParts = mutableListOf("route_mode=$routeMode")
        origin?.let { queryParts += "origin_latitude=${it.latitude}"; queryParts += "origin_longitude=${it.longitude}" }
        val query = "?${queryParts.joinToString("&")}"
        val value = json("/seller-workspace/routes/$routeId/map-plan$query")
        val stops = value.getJSONArray("ordered_customers").toStops()
        stops to value.optJSONObject("initial_leg")?.toLeg(value.optString("polyline"))
    }

    suspend fun routeLeg(routeId: String, stop: RouteStop, origin: GeoPoint): RouteLeg = withContext(Dispatchers.IO) {
        val url = "/seller-workspace/routes/$routeId/map-leg?destination_id=${stop.id}&origin_latitude=${origin.latitude}&origin_longitude=${origin.longitude}"
        val value = json(url)
        value.optJSONObject("leg")?.toLeg(value.optString("polyline")) ?: error("مسیر قابل دریافت نیست.")
    }

    private fun json(path: String): JSONObject {
        client.newCall(request(path)).execute().use { response ->
            if (response.code == 401) error("نشست شما پایان یافته است؛ دوباره وارد شوید.")
            if (!response.isSuccessful) error("دریافت مسیر ناموفق بود. (${response.code})")
            val body = response.body?.string() ?: error("پاسخ خالی از سرور دریافت شد.")
            return JSONObject(body)
        }
    }

    private fun JSONArray.toRoutes() = List(length()) { index ->
        getJSONObject(index).let { SellerRoute(it.getString("id"), it.optString("title"), it.optInt("customer_count")) }
    }
    private fun JSONArray.toStops() = List(length()) { index ->
        getJSONObject(index).let {
            RouteStop(it.getString("id"), it.optString("store_name").ifBlank { it.optString("name") }, GeoPoint(it.getDouble("latitude"), it.getDouble("longitude")))
        }
    }
    private fun JSONObject.toLeg(polyline: String): RouteLeg = RouteLeg(polyline, optJSONArray("steps")?.toSteps() ?: emptyList())
    private fun JSONArray.toSteps() = List(length()) { index ->
        getJSONObject(index).let { step ->
            val start = step.optJSONArray("start_location")?.let { GeoPoint(it.optDouble(1), it.optDouble(0)) }
            NavigationStep(step.optString("instruction").stripHtml().ifBlank { "مستقیم حرکت کنید" }, step.optJSONObject("distance")?.optString("text").orEmpty(), start)
        }
    }
    private fun String.stripHtml() = replace(Regex("<[^>]*>"), "").trim()
}
