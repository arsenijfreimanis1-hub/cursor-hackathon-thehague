import AppKit
import Foundation

enum MinisServiceControl {
    private static var uid: String { String(getuid()) }
    private static var domain: String { "gui/\(uid)" }

    @discardableResult
    private static func launchctl(_ args: [String]) -> (ok: Bool, output: String) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/launchctl")
        process.arguments = args
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        do {
            try process.run()
            process.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let text = String(data: data, encoding: .utf8) ?? ""
            return (process.terminationStatus == 0, text.trimmingCharacters(in: .whitespacesAndNewlines))
        } catch {
            return (false, error.localizedDescription)
        }
    }

    static func restartHelper() -> [String: Any] {
        let label = "\(domain)/com.willy.jarvis-helper"
        let result = launchctl(["kickstart", "-k", label])
        if result.ok {
            return ["ok": true, "action": "helper_restarted"]
        }
        return bootstrapHelper()
    }

    static func hardResetHelper() -> [String: Any] {
        let label = "com.willy.jarvis-helper"
        let plist = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/LaunchAgents/\(label).plist")
        guard FileManager.default.fileExists(atPath: plist.path) else {
            return ["ok": false, "error": "missing plist: \(plist.path)"]
        }
        _ = launchctl(["bootout", "\(domain)/\(label)"])
        let boot = launchctl(["bootstrap", domain, plist.path])
        guard boot.ok else {
            return ["ok": false, "error": boot.output]
        }
        _ = launchctl(["enable", "\(domain)/\(label)"])
        let start = launchctl(["kickstart", "\(domain)/\(label)"])
        return ["ok": start.ok, "action": "helper_hard_reset", "detail": start.output]
    }

    private static func bootstrapHelper() -> [String: Any] {
        var result = hardResetHelper()
        if (result["ok"] as? Bool) == true {
            result["action"] = "helper_bootstrapped"
        }
        return result
    }
}
