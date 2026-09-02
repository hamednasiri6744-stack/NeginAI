import CoreLocation

struct RouteStop: Identifiable, Codable, Equatable {
    let id: String
    let title: String
    let latitude: Double
    let longitude: Double

    var coordinate: CLLocationCoordinate2D { .init(latitude: latitude, longitude: longitude) }
}

struct NavigationStep: Codable, Equatable {
    let instruction: String
    let latitude: Double
    let longitude: Double

    var coordinate: CLLocationCoordinate2D { .init(latitude: latitude, longitude: longitude) }
}

struct RouteLeg: Codable, Equatable {
    let destination: RouteStop
    let polyline: [Coordinate]
    let steps: [NavigationStep]

    struct Coordinate: Codable, Equatable {
        let latitude: Double
        let longitude: Double

        var clLocation: CLLocation { .init(latitude: latitude, longitude: longitude) }
    }
}

enum NavigationState: Equatable {
    case idle
    case navigating
    case arrived
    case offRoute
}
