import CoreLocation

/// The native app receives only authenticated route data from NeginAI.
/// Neshan service keys remain on the backend and are never embedded in iOS.
protocol RouteProvider {
    func routeLeg(from origin: CLLocation, to destination: RouteStop) async throws -> RouteLeg
}

enum RouteProviderError: LocalizedError {
    case unavailable

    var errorDescription: String? { "مسیر فعلی در دسترس نیست." }
}
