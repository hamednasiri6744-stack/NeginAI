import CoreLocation
import MapKit

final class NavigationEngine: ObservableObject {
    @Published private(set) var state: NavigationState = .idle
    @Published private(set) var activeLeg: RouteLeg?
    @Published private(set) var activeStepIndex = 0

    private let prompts = PromptPlayer()
    private var lastReroute = Date.distantPast

    func start(leg: RouteLeg) {
        activeLeg = leg
        activeStepIndex = 0
        state = .navigating
        prompts.play(.routeStarted)
    }

    func update(location: CLLocation) {
        guard state == .navigating || state == .offRoute, let leg = activeLeg else { return }
        if location.distance(from: leg.destination.coordinate.location) <= 55 {
            state = .arrived
            prompts.play(.arrived)
            return
        }
        if distanceToRoute(location, polyline: leg.polyline) > 75, Date().timeIntervalSince(lastReroute) > 15 {
            state = .offRoute
            lastReroute = Date()
            prompts.play(.offRoute)
        }
    }

    func replaceLegAfterReroute(_ leg: RouteLeg) {
        activeLeg = leg
        activeStepIndex = 0
        state = .navigating
    }

    func skipStop() {
        state = .idle
        activeLeg = nil
        prompts.play(.stopSkipped)
    }

    private func distanceToRoute(_ location: CLLocation, polyline: [RouteLeg.Coordinate]) -> CLLocationDistance {
        guard polyline.count > 1 else { return .greatestFiniteMagnitude }
        let point = MKMapPoint(location.coordinate)
        return zip(polyline, polyline.dropFirst()).map { start, end in
            let segment = MKPolyline(points: [MKMapPoint(start.clLocation.coordinate), MKMapPoint(end.clLocation.coordinate)], count: 2)
            return segment.closestPoint(to: point).distance(to: point)
        }.min() ?? .greatestFiniteMagnitude
    }
}

private extension CLLocationCoordinate2D {
    var location: CLLocation { .init(latitude: latitude, longitude: longitude) }
}

private extension MKPolyline {
    func closestPoint(to point: MKMapPoint) -> MKMapPoint {
        guard pointCount >= 2 else { return point }
        var points = [MKMapPoint](repeating: .init(), count: pointCount)
        getPoints(&points, range: NSRange(location: 0, length: pointCount))
        let start = points[0], end = points[1]
        let dx = end.x - start.x, dy = end.y - start.y
        let length = dx * dx + dy * dy
        guard length > 0 else { return start }
        let projection = max(0, min(1, ((point.x - start.x) * dx + (point.y - start.y) * dy) / length))
        return MKMapPoint(x: start.x + projection * dx, y: start.y + projection * dy)
    }
}
