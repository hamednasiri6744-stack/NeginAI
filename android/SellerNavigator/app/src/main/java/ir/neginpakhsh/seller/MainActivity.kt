package ir.neginpakhsh.seller

import android.Manifest
import android.app.Application
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val model: RouteViewModel by viewModels()
    private val locationPermission = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { granted ->
        if (granted.values.any { it }) model.startLocation()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme(colorScheme = lightColorScheme(primary = Color(0xFF087D62))) { SellerNavigator(model) } }
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) model.startLocation()
        else locationPermission.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION))
    }

    override fun onStop() { super.onStop(); model.stopLocation() }
}

class RouteViewModel(application: Application) : AndroidViewModel(application), LocationListener {
    private val api = NeginApi(application)
    private val location = application.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    var state by mutableStateOf(NavigationState())
        private set
    var signedIn by mutableStateOf(false)
        private set
    private var lastReroute = 0L

    init {
        if (api.hasSession()) { signedIn = true; loadRoutes() }
    }

    fun login(username: String, password: String) = launch { api.login(username, password); signedIn = true; loadRoutes() }
    fun loadRoutes() = launch { state = state.copy(loading = true, error = null); state = state.copy(routes = api.routes(), loading = false) }
    fun activate(route: SellerRoute) = launch {
        state = state.copy(loading = true, error = null, activeRoute = route, activeStopIndex = 0, stepIndex = 0)
        val (stops, initialLeg) = api.routePlan(route.id, state.position, state.routeMode)
        state = state.copy(stops = stops, leg = initialLeg, loading = false)
        refreshLeg()
    }
    fun skipStop() = launch {
        val next = state.activeStopIndex + 1
        state = state.copy(activeStopIndex = next, stepIndex = 0, leg = null)
        refreshLeg()
    }
    fun setRouteMode(mode: String) { state = state.copy(routeMode = mode) }
    private fun refreshLeg() = launch {
        val route = state.activeRoute ?: return@launch
        val stop = state.activeStop ?: return@launch
        val point = state.position ?: return@launch
        state = state.copy(loading = true, error = null)
        state = state.copy(leg = api.routeLeg(route.id, stop, point), stepIndex = 0, loading = false)
    }
    fun startLocation() {
        if (getApplication<Application>().checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) return
        location.requestLocationUpdates(LocationManager.GPS_PROVIDER, 2_000, 4f, this)
        (location.getLastKnownLocation(LocationManager.GPS_PROVIDER)
            ?: location.getLastKnownLocation(LocationManager.NETWORK_PROVIDER))
            ?.let(::onLocationChanged)
    }
    fun stopLocation() = location.removeUpdates(this)
    override fun onLocationChanged(value: Location) {
        val point = GeoPoint(value.latitude, value.longitude); val current = state
        state = current.copy(position = point)
        val step = state.currentStep
        if (step?.start != null && NavigationEngine.meters(point, step.start) <= NavigationEngine.STEP_METERS) state = state.copy(stepIndex = state.stepIndex + 1)
        val stop = state.activeStop
        if (stop != null && NavigationEngine.meters(point, stop.point) <= NavigationEngine.ARRIVAL_METERS) { skipStop(); return }
        val points = NavigationEngine.decodePolyline(state.leg?.encodedPolyline.orEmpty())
        if (state.activeStop != null && points.isNotEmpty() && NavigationEngine.closestDistance(point, points) > NavigationEngine.OFF_ROUTE_METERS && System.currentTimeMillis() - lastReroute > 15_000) {
            lastReroute = System.currentTimeMillis(); refreshLeg()
        }
    }
    override fun onProviderEnabled(provider: String) = Unit
    override fun onProviderDisabled(provider: String) { state = state.copy(error = "موقعیت‌یاب گوشی خاموش است.") }
    private fun launch(block: suspend () -> Unit) = viewModelScope.launch { try { block() } catch (e: Exception) { state = state.copy(loading = false, error = e.message ?: "خطای نامشخص") } }
}

@Composable private fun SellerNavigator(model: RouteViewModel) {
    val state = model.state
    if (!model.signedIn) LoginScreen(onLogin = model::login, error = state.error, loading = state.loading)
    else if (state.activeRoute == null) RoutesScreen(state.routes, state.routeMode, state.loading, state.error, model::activate, model::loadRoutes, model::setRouteMode)
    else NavigationScreen(state, model::skipStop)
}

@Composable private fun LoginScreen(onLogin: (String, String) -> Unit, error: String?, loading: Boolean) {
    var username by remember { mutableStateOf("") }; var password by remember { mutableStateOf("") }
    Column(Modifier.fillMaxSize().padding(28.dp), verticalArrangement = Arrangement.Center) {
        Text("نگین فروش", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("مسیریاب حرفه‌ای فروشنده", color = Color.Gray, modifier = Modifier.padding(bottom = 28.dp))
        OutlinedTextField(username, { username = it }, label = { Text("نام کاربری") }, modifier = Modifier.fillMaxWidth())
        OutlinedTextField(password, { password = it }, label = { Text("رمز عبور") }, modifier = Modifier.fillMaxWidth().padding(top = 10.dp))
        error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 10.dp)) }
        Button({ onLogin(username, password) }, enabled = username.isNotBlank() && password.isNotBlank() && !loading, modifier = Modifier.fillMaxWidth().padding(top = 18.dp)) { Text(if (loading) "در حال ورود…" else "ورود") }
    }
}

@Composable private fun RoutesScreen(routes: List<SellerRoute>, routeMode: String, loading: Boolean, error: String?, onOpen: (SellerRoute) -> Unit, onRefresh: () -> Unit, onMode: (String) -> Unit) {
    Column(Modifier.fillMaxSize().padding(16.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) { Text("مسیرهای امروز", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold); TextButton(onRefresh) { Text("بروزرسانی") } }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(selected = routeMode == "sales_priority", onClick = { onMode("sales_priority") }, label = { Text("اولویت فروش") })
            FilterChip(selected = routeMode == "shortest", onClick = { onMode("shortest") }, label = { Text("کوتاه‌ترین مسیر") })
        }
        Text(if (routeMode == "sales_priority") "مشتریان با احتمال خرید بالا و متوسط، پیش از سایر مشتریان چیده می‌شوند." else "همهٔ مشتریان صرفاً با کمترین مسیر جغرافیایی چیده می‌شوند.", color = Color.Gray, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(top = 6.dp))
        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        if (loading) LinearProgressIndicator(Modifier.fillMaxWidth())
        LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(top = 14.dp)) { items(routes) { route -> ElevatedCard(Modifier.fillMaxWidth().clickable { onOpen(route) }) { Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically) { Text("⌖", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.headlineSmall); Column(Modifier.padding(start = 14.dp).weight(1f)) { Text(route.title, fontWeight = FontWeight.Bold); Text("${route.customerCount} مشتری", color = Color.Gray) }; Text("شروع") } } } }
    }
}

@Composable private fun NavigationScreen(state: NavigationState, onSkip: () -> Unit) {
    val step = state.currentStep; val title = step?.instruction ?: "مستقیم تا پایگاه فعال حرکت کنید"
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), horizontalArrangement = Arrangement.SpaceBetween) { Column { Text(state.activeRoute?.title.orEmpty(), fontWeight = FontWeight.Bold); Text("پایگاه ${state.activeStopIndex + 1} از ${state.stops.size}", color = Color.Gray) }; if (state.loading) CircularProgressIndicator(Modifier.size(24.dp), strokeWidth = 2.dp) }
        RouteCanvas(state, Modifier.weight(1f).fillMaxWidth())
        Surface(Modifier.fillMaxWidth(), shadowElevation = 12.dp, shape = RoundedCornerShape(topStart = 22.dp, topEnd = 22.dp)) { Column(Modifier.padding(20.dp)) { Text(step?.distanceText?.let { "تا $it دیگر" } ?: "راهنمای مسیر", color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold); Text(title, style = MaterialTheme.typography.headlineSmall, modifier = Modifier.padding(vertical = 6.dp)); Text("با خروج بیش از ۸۰ متر از مسیر، مسیر به‌صورت خودکار اصلاح می‌شود.", color = Color.Gray, style = MaterialTheme.typography.bodySmall); Button(onSkip, Modifier.fillMaxWidth().padding(top = 12.dp)) { Text("رد کردن پایگاه و رفتن به بعدی") } } }
    }
}

@Composable private fun RouteCanvas(state: NavigationState, modifier: Modifier) {
    val points = remember(state.leg?.encodedPolyline) { NavigationEngine.decodePolyline(state.leg?.encodedPolyline.orEmpty()) }
    Canvas(modifier.background(Color(0xFFE8F1EE))) {
        val all = points + listOfNotNull(state.position, state.activeStop?.point)
        if (all.isEmpty()) { drawContext.canvas.nativeCanvas.drawText("در انتظار دریافت موقعیت و مسیر…", size.width / 2, size.height / 2, android.graphics.Paint().apply { color = android.graphics.Color.DKGRAY; textAlign = android.graphics.Paint.Align.CENTER; textSize = 36f }); return@Canvas }
        val minLat = all.minOf { it.latitude }; val maxLat = all.maxOf { it.latitude }; val minLng = all.minOf { it.longitude }; val maxLng = all.maxOf { it.longitude }
        fun project(p: GeoPoint): androidx.compose.ui.geometry.Offset { val x = if (maxLng == minLng) .5f else ((p.longitude - minLng) / (maxLng - minLng)).toFloat(); val y = if (maxLat == minLat) .5f else (1 - (p.latitude - minLat) / (maxLat - minLat)).toFloat(); return androidx.compose.ui.geometry.Offset(24.dp.toPx() + x * (size.width - 48.dp.toPx()), 24.dp.toPx() + y * (size.height - 48.dp.toPx())) }
        if (points.size > 1) { val path = Path().apply { moveTo(project(points.first()).x, project(points.first()).y); points.drop(1).forEach { lineTo(project(it).x, project(it).y) } }; drawPath(path, Color(0xFF087DDA), style = Stroke(10.dp.toPx())) }
        state.activeStop?.let { drawCircle(Color(0xFF087D62), 13.dp.toPx(), project(it.point)) }
        state.position?.let { drawCircle(Color(0xFF1565D8), 12.dp.toPx(), project(it)) }
    }
}
