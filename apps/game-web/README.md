# AI Prompting Game

## Today
- `swift-prototype/ios-app`: the existing SwiftUI AI Productivity Trainer (see nested README + TESTING docs).
- Build/run instructions remain unchanged: open the Xcode project and provide an API key via `Secrets.plist` or env vars.

## Tomorrow
- Replace the native app with a shared React experience that can ship on web + iOS (via Capacitor/Expo or SwiftUI wrapper).
- Use `packages/ui-kit` for shared components and `packages/js-core` for the gameplay state machine.
- Store lesson progress + telemetry in the theory engine backend so insights can inform other dock108 surfaces.

## Migration Notes
1. Mirror the Swift game loops in TypeScript first (pure state machine in `packages/js-core`).
2. Build a React renderer in `apps/game-web` that consumes the state machine.
3. Keep the Swift app compiling so TestFlight users can keep playing until the React version ships.
