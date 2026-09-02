import MapKit
import SwiftUI

struct NavigationScreen: View {
    @EnvironmentObject private var locationService: LocationService
    @EnvironmentObject private var navigation: NavigationEngine
    @State private var position: MapCameraPosition = .automatic

    var body: some View {
        Map(position: $position) {
            UserAnnotation()
            if let leg = navigation.activeLeg {
                MapPolyline(MKPolyline(coordinates: leg.polyline.map { $0.clLocation.coordinate }, count: leg.polyline.count))
                    .stroke(.green, lineWidth: 6)
                Marker(leg.destination.title, coordinate: leg.destination.coordinate)
            }
        }
        .mapControls { MapUserLocationButton(); MapCompass() }
        .safeAreaInset(edge: .bottom) { controls }
        .onAppear { locationService.start() }
        .onChange(of: locationService.location) { _, location in
            guard let location else { return }
            navigation.update(location: location)
            position = .camera(.init(centerCoordinate: location.coordinate, distance: 800))
        }
    }

    private var controls: some View {
        VStack(alignment: .trailing, spacing: 10) {
            Text(statusText).font(.headline).frame(maxWidth: .infinity, alignment: .trailing)
            if navigation.activeLeg != nil {
                Button("رد کردن پایگاه و مسیر به بعدی") { navigation.skipStop() }
                    .buttonStyle(.borderedProminent)
            }
        }
        .padding().background(.ultraThinMaterial).clipShape(.rect(cornerRadius: 16)).padding()
    }

    private var statusText: String {
        switch navigation.state {
        case .idle: "مسیر روز را انتخاب کنید"
        case .navigating: "در مسیر پایگاه فعال"
        case .arrived: "به پایگاه رسیدید"
        case .offRoute: "از مسیر خارج شده‌اید؛ مسیر جدید در حال دریافت است"
        }
    }
}
