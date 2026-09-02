# Seller Navigator for iOS

This is the native iOS navigation module for the seller application. It deliberately keeps turn-by-turn navigation outside the browser:

- `CoreLocation` supplies live and background-capable location updates.
- `NavigationEngine` detects arrival and off-route state.
- `PromptPlayer` plays bundled Persian audio prompts with `AVAudioPlayer`; it does not use browser or AI text-to-speech.
- `RouteProvider` is the boundary for the authenticated NeginAI backend, which in turn calls Neshan Direction/Trip services without exposing a service key to the phone.

The first shell uses MapKit only as a native renderer while the navigation engine is verified. Replace that renderer with Neshan's current iOS SDK only after Neshan confirms the supported SDK and license flow; the routing data remains sourced from the protected NeginAI backend.

## Open on a Mac

1. Install [XcodeGen](https://github.com/yonaskolb/XcodeGen).
2. Run `xcodegen generate` in this directory.
3. Open `SellerNavigator.xcodeproj` in Xcode.
4. Configure the Apple development team and the final bundle identifier.
5. Add the Persian MP3 prompt files listed in `Resources/Audio/README.md`.

The app asks for **Always Allow** location access because navigation must remain active while the phone is locked. Background Location Updates is enabled in `project.yml`.

## Backend contract still to add

The current web endpoints authenticate via browser session. Before connecting this app to production, add a mobile bearer-token flow and expose a mobile route-leg endpoint. Do not put `NESHAN_SERVICE_API_KEY` in the iOS app.
