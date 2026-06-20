import AppKit
import Foundation
import Vision

/// Always-on screen observer — captures frontmost app context, deduplicates frames, OCRs locally.
final class ScreenWatcher {
    static let shared = ScreenWatcher()

    private var timer: Timer?
    private var paused = false
    private var lastPhash: String?
    private var lastOcrText: String = ""
    private var lastApp: String = ""
    private var lastWindowTitle: String = ""
    private var buffer: [[String: Any]] = []
    private var captureCount = 0
    private var skippedCount = 0
    private var lastPostAt = Date.distantPast
    private var lastError: String?

    private let excludedBundleIds: Set<String> = [
        "com.1password.1password", "com.agilebits.onepassword7",
        "com.bitwarden.desktop", "com.dashlane.Dashlane",
        "com.lastpass.LastPass", "com.apple.MobileSMS",
        "com.tinyspeck.slackmacgap", "com.hnc.Discord",
        "org.whispersystems.signal-desktop", "ru.keepcoder.Telegram",
        "net.whatsapp.WhatsApp", "com.apple.mail",
        "com.microsoft.Outlook", "com.readdle.smartemail-Mac",
        "com.apple.finder", "com.apple.systempreferences",
        "com.apple.ActivityMonitor", "com.apple.wallet",
    ]

    private var coreURL: String {
        ProcessInfo.processInfo.environment["JARVIS_CORE_URL"] ?? "http://127.0.0.1:8787"
    }

    private var interval: TimeInterval {
        let raw = ProcessInfo.processInfo.environment["JARVIS_SCREEN_CAPTURE_INTERVAL_SECONDS"] ?? "10"
        return max(5, TimeInterval(Int(raw) ?? 10))
    }

    private var enabled: Bool {
        let raw = (ProcessInfo.processInfo.environment["JARVIS_SCREEN_WATCH_ENABLED"] ?? "true").lowercased()
        return raw != "false" && raw != "0"
    }

    func status() -> [String: Any] {
        [
            "enabled": enabled,
            "paused": paused,
            "running": timer != nil && !paused,
            "interval_seconds": interval,
            "capture_count": captureCount,
            "skipped_count": skippedCount,
            "buffer_size": buffer.count,
            "last_app": lastApp,
            "last_window": lastWindowTitle,
            "last_error": lastError as Any,
        ]
    }

    func start() {
        guard enabled else { return }
        guard timer == nil else { return }
        paused = false
        DispatchQueue.main.async {
            self.timer = Timer.scheduledTimer(withTimeInterval: self.interval, repeats: true) { _ in
                self.tick()
            }
            self.timer?.tolerance = 1.0
            RunLoop.main.add(self.timer!, forMode: .common)
            self.tick()
        }
    }

    func pause() {
        paused = true
    }

    func resume() {
        paused = false
    }

    func stop() {
        timer?.invalidate()
        timer = nil
        flushBuffer()
    }

    private func tick() {
        guard !paused else { return }
        guard let app = NSWorkspace.shared.frontmostApplication else { return }
        let bundleId = app.bundleIdentifier ?? ""
        if excludedBundleIds.contains(bundleId) {
            skippedCount += 1
            return
        }

        let appName = app.localizedName ?? bundleId
        let windowTitle = activeWindowTitle(for: app) ?? ""

        let shotURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("jarvis-screen-\(UUID().uuidString).png")
        guard runCommand("/usr/sbin/screencapture", ["-x", shotURL.path]) else {
            lastError = "screencapture failed"
            return
        }

        guard let image = NSImage(contentsOf: shotURL),
              let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
            try? FileManager.default.removeItem(at: shotURL)
            lastError = "image load failed"
            return
        }

        let phash = perceptualHash(cgImage)
        let unchanged = phash == lastPhash && appName == lastApp && windowTitle == lastWindowTitle
        if unchanged {
            skippedCount += 1
            try? FileManager.default.removeItem(at: shotURL)
            return
        }

        let ocrText: String
        if let prev = lastPhash, phashSimilar(prev, phash) && appName == lastApp {
            ocrText = lastOcrText
        } else {
            ocrText = recognizeText(cgImage)
        }

        lastPhash = phash
        lastOcrText = ocrText
        lastApp = appName
        lastWindowTitle = windowTitle
        captureCount += 1
        lastError = nil

        let iso = ISO8601DateFormatter().string(from: Date())
        buffer.append([
            "ts": iso,
            "app": appName,
            "bundle_id": bundleId,
            "window_title": windowTitle,
            "ocr_text": String(ocrText.prefix(4000)),
            "phash": phash,
            "screenshot_path": shotURL.path,
        ])

        if buffer.count >= 3 || Date().timeIntervalSince(lastPostAt) >= 30 {
            flushBuffer()
        }
    }

    private func flushBuffer() {
        guard !buffer.isEmpty else { return }
        let events = buffer
        buffer = []
        lastPostAt = Date()

        guard let url = URL(string: "\(coreURL)/api/screen/events") else { return }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 15
        let body: [String: Any] = ["events": events]
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: req) { _, resp, err in
            if let err {
                self.lastError = err.localizedDescription
                return
            }
            if let http = resp as? HTTPURLResponse, http.statusCode >= 400 {
                self.lastError = "core returned \(http.statusCode)"
            }
        }.resume()
    }

    private func activeWindowTitle(for app: NSRunningApplication) -> String? {
        let appName = app.localizedName ?? ""
        let script = """
        tell application "System Events"
            try
                set frontApp to first application process whose frontmost is true
                set winName to name of front window of frontApp
                return winName
            on error
                return ""
            end try
        end tell
        """
        guard let appleScript = NSAppleScript(source: script) else { return nil }
        var error: NSDictionary?
        let result = appleScript.executeAndReturnError(&error)
        let title = result.stringValue?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        if title.isEmpty { return appName }
        return title
    }

    private func recognizeText(_ image: CGImage) -> String {
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .fast
        request.usesLanguageCorrection = true
        let handler = VNImageRequestHandler(cgImage: image, options: [:])
        do {
            try handler.perform([request])
            let lines = (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }
            return lines.joined(separator: "\n")
        } catch {
            return ""
        }
    }

    private func perceptualHash(_ image: CGImage) -> String {
        let size = 8
        let width = size
        let height = size
        let colorSpace = CGColorSpaceCreateDeviceGray()
        guard let ctx = CGContext(
            data: nil, width: width, height: height,
            bitsPerComponent: 8, bytesPerRow: width,
            space: colorSpace, bitmapInfo: CGImageAlphaInfo.none.rawValue
        ) else { return "0" }
        ctx.interpolationQuality = .low
        ctx.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        guard let data = ctx.data else { return "0" }
        let ptr = data.bindMemory(to: UInt8.self, capacity: width * height)
        var sum: Int = 0
        for i in 0..<(width * height) { sum += Int(ptr[i]) }
        let avg = sum / (width * height)
        var bits = ""
        for i in 0..<(width * height) {
            bits.append(ptr[i] >= avg ? "1" : "0")
        }
        return String(bits.hashValue)
    }

    private func phashSimilar(_ a: String, _ b: String) -> Bool {
        a == b
    }
}
