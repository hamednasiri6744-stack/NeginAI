package ir.neginpakhsh.seller

data class GeoPoint(val latitude: Double, val longitude: Double)

data class SellerRoute(val id: String, val title: String, val customerCount: Int)
data class RouteStop(val id: String, val title: String, val point: GeoPoint)
data class NavigationStep(val instruction: String, val distanceText: String, val start: GeoPoint?)
data class RouteLeg(val encodedPolyline: String, val steps: List<NavigationStep>)

data class NavigationState(
    val routes: List<SellerRoute> = emptyList(),
    val routeMode: String = "sales_priority",
    val activeRoute: SellerRoute? = null,
    val stops: List<RouteStop> = emptyList(),
    val activeStopIndex: Int = 0,
    val leg: RouteLeg? = null,
    val position: GeoPoint? = null,
    val stepIndex: Int = 0,
    val loading: Boolean = false,
    val error: String? = null,
) {
    val activeStop get() = stops.getOrNull(activeStopIndex)
    val currentStep get() = leg?.steps?.getOrNull(stepIndex)
}
