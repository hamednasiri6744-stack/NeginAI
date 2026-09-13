# Visitor Essentials Audit — v0.13.0

## Closed in this stage
- Header profile control on all Visitor screens now opens `/visitor/profile`.
- Added Profile / Settings screen.
- Added explicit mock session key and Visitor route guard.
- Added logout confirmation, session clear, and replace-navigation back to Login.
- Unknown URLs now resolve to Login or Visitor Home based on session state.
- Added local persisted toggles for in-app notifications, offline storage and automatic sync.
- Added manual local sync action/status.
- Added account/role/territory/app-version surfaces.
- Removed dead Login language button; current language is shown as a status indicator.
- Home Start Route now opens Route / Visit.
- Home full schedule action now opens Route / Visit.
- Added visible focus states for keyboard/accessibility safety.
- Added `aria-current=page` to active bottom navigation destinations.
- Refined Bottom Dock active elevation with a raised, pressed dark-neumorphic state.

## Intentionally not faked; requires deeper workflow or real integration
- Password change / password recovery → authentication service.
- Android installer download → release/distribution artifact.
- Voice order → voice service.
- PDF invoice download / report export → document/export service.
- Real phone call / map navigation / GPS writeback → device + map integration.
- Negin AI deep analysis → agent/service integration.
- New customer full lifecycle and advanced filters → Customer workflow hardening.
- Customer overflow menu and operational notes → Customer 360 deep workflow.
- Offline queue conflict handling / server reconciliation → Core Flow Hardening.

These items are preserved in the UI where applicable and remain explicit integration/workflow gaps rather than being silently removed.
