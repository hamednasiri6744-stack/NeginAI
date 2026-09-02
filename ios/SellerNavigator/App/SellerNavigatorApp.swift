import SwiftUI

@main
struct SellerNavigatorApp: App {
    @StateObject private var locationService = LocationService()
    @StateObject private var navigation = NavigationEngine()

    var body: some Scene {
        WindowGroup {
            NavigationScreen()
                .environmentObject(locationService)
                .environmentObject(navigation)
        }
    }
}
