package ir.neginpakhsh.seller

import kotlin.math.*

object NavigationEngine {
    const val ARRIVAL_METERS = 70.0
    const val STEP_METERS = 45.0
    const val OFF_ROUTE_METERS = 80.0

    fun meters(a: GeoPoint, b: GeoPoint): Double {
        val lat = Math.toRadians(b.latitude - a.latitude)
        val lng = Math.toRadians(b.longitude - a.longitude)
        val x = sin(lat / 2).pow(2) + cos(Math.toRadians(a.latitude)) * cos(Math.toRadians(b.latitude)) * sin(lng / 2).pow(2)
        return 6_371_000.0 * 2 * atan2(sqrt(x), sqrt(1 - x))
    }

    fun decodePolyline(encoded: String): List<GeoPoint> {
        val points = mutableListOf<GeoPoint>(); var index = 0; var lat = 0; var lng = 0
        while (index < encoded.length) {
            fun next(): Int { var result = 0; var shift = 0; var value: Int; do { value = encoded[index++].code - 63; result = result or ((value and 31) shl shift); shift += 5 } while (value >= 32 && index < encoded.length); return if ((result and 1) != 0) result.inv() shr 1 else result shr 1 }
            lat += next(); lng += next(); points += GeoPoint(lat / 1E5, lng / 1E5)
        }
        return points
    }

    fun closestDistance(position: GeoPoint, points: List<GeoPoint>): Double = points.minOfOrNull { meters(position, it) } ?: Double.MAX_VALUE
}
