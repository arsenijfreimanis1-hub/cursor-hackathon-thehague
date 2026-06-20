import AppKit
import SwiftUI

@main
struct WilliamKioskApp: App {
    @State private var model = VoiceStateViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView(model: model)
                .preferredColorScheme(.dark)
                .onAppear {
                    configureWindow()
                    model.startPolling()
                }
                .onDisappear { model.stopPolling() }
        }
        .windowStyle(.hiddenTitleBar)
    }

    private func configureWindow() {
        DispatchQueue.main.async {
            guard let window = NSApplication.shared.windows.first else { return }
            window.toggleFullScreen(nil)
            window.level = .floating
            window.collectionBehavior = [.canJoinAllSpaces, .fullScreenPrimary]
        }
    }
}
