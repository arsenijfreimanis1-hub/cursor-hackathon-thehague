import AppKit
import SwiftUI
import WebKit

private let defaultURL = URL(string: "http://127.0.0.1:8787/")!

struct WebContainer: NSViewRepresentable {
    let url: URL

    func makeNSView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.setValue(false, forKey: "drawsBackground")
        webView.load(URLRequest(url: url))
        return webView
    }

    func updateNSView(_ webView: WKWebView, context: Context) {
        if webView.url?.absoluteString != url.absoluteString {
            webView.load(URLRequest(url: url))
        }
    }
}

@main
struct WilliamDesktopApp: App {
    var body: some Scene {
        WindowGroup {
            WebContainer(url: defaultURL)
                .preferredColorScheme(.dark)
                .frame(minWidth: 960, minHeight: 680)
        }
        .defaultSize(width: 1100, height: 760)
        .commands {
            CommandGroup(replacing: .newItem) {}
        }
    }
}
