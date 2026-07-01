import AppKit
import AVFoundation
import Foundation
import Network

let port: UInt16 = 8788
var statusItem: NSStatusItem!

func jsonData(_ body: [String: Any]) -> Data {
    (try? JSONSerialization.data(withJSONObject: body)) ?? Data("{}".utf8)
}

func httpResponse(status: String, body: Data) -> Data {
    let header = "HTTP/1.1 \(status)\r\nContent-Type: application/json\r\nContent-Length: \(body.count)\r\nConnection: close\r\n\r\n"
    var data = Data(header.utf8)
    data.append(body)
    return data
}

func parseRequest(_ data: Data) -> (method: String, path: String, body: Data)? {
    guard let raw = String(data: data, encoding: .utf8) else { return nil }
    let parts = raw.components(separatedBy: "\r\n\r\n")
    let head = parts.first ?? ""
    let body = parts.count > 1 ? Data(parts[1].utf8) : Data()
    let lines = head.components(separatedBy: "\r\n")
    guard let requestLine = lines.first else { return nil }
    let tokens = requestLine.split(separator: " ")
    guard tokens.count >= 2 else { return nil }
    return (String(tokens[0]), String(tokens[1]), body)
}

func runCommand(_ launchPath: String, _ arguments: [String]) -> Bool {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: launchPath)
    process.arguments = arguments
    do {
        try process.run()
        process.waitUntilExit()
        return process.terminationStatus == 0
    } catch {
        return false
    }
}

func openMissingPermissionSettings() {
    let perms = WakeWordListener.shared.authStatus()
    if !Input.accessibilityGranted,
       let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") {
        NSWorkspace.shared.open(url)
    }
    if perms["microphone"] as? String != "granted",
       let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone") {
        NSWorkspace.shared.open(url)
    }
    if perms["speech"] as? String != "granted",
       let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_SpeechRecognition") {
        NSWorkspace.shared.open(url)
    }
}

func takeScreenshot() -> [String: Any] {
    // Screen Recording not used — desktop awareness goes through Accessibility (DesktopContext).
    return [
        "ok": false,
        "error": "screenshots disabled — use GET /desktop/context (Accessibility API, no Screen Recording)",
        "method": "accessibility",
        "use_context": true,
    ]
}

func escapeAppleScript(_ text: String) -> String {
    text.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "\"", with: "\\\"")
}

func postNotification(title: String, message: String, speak: Bool) -> [String: Any] {
    let script = "display notification \"\(escapeAppleScript(message))\" with title \"\(escapeAppleScript(title))\""
    let ok = runCommand("/usr/bin/osascript", ["-e", script])
    if speak && !Voice.isMuted {
        Voice.speak(message)
    }
    return ["ok": ok]
}

func respond(_ connection: NWConnection, status: String, body: [String: Any]) {
    let payload = httpResponse(status: status, body: jsonData(body))
    connection.send(content: payload, completion: .contentProcessed { _ in
        connection.cancel()
    })
}

func handleRequest(_ connection: NWConnection, buffer: Data) {
    guard let req = parseRequest(buffer) else {
        respond(connection, status: "400 Bad Request", body: ["ok": false, "error": "bad request"])
        return
    }

    switch (req.method, req.path) {
    case ("GET", "/status"):
        DispatchQueue.main.async {
            let listener = WakeWordListener.shared
            respond(connection, status: "200 OK", body: [
                "ok": true,
                "service": "jarvis-helper",
                "port": port,
                "wake_word": listener.wakePhraseDisplay,
                "wake_phrase_hint": listener.wakePhraseHint,
                "voice_backend": listener.voiceBackendName,
                "voice_state": listener.voiceState,
                "wake_listening": listener.isActive,
                "sleeping": listener.isSleeping,
                "healthy": listener.isHealthy,
                "conversation_mode": listener.isConversationMode,
                "awaiting_command": listener.isAwaitingCommand,
                "listening_for_response": listener.listeningForResponse,
                "busy": listener.isBusy,
                "voice_muted": Voice.isMuted,
                "voice_speaking": Voice.isSpeaking,
                "microphone": listener.deviceStatus(),
                "wake_status": listener.statusMessage,
                "last_heard": listener.lastHeard,
                "live_transcript": listener.liveTranscript,
                "live_transcript_partial": listener.liveTranscriptIsPartial,
                "last_final_transcript": listener.lastFinalTranscript,
                "last_action": listener.lastAction,
                "voice": Voice.displayName,
                "sounds": Sound.displayName,
                "permissions": listener.authStatus(),
                "voice_profile": SpeakerVerifier.shared.status(),
                "accessibility": Input.accessibilityGranted,
                "screen_watcher": ScreenWatcher.shared.status(),
            ])
        }
    case ("GET", "/debug"):
        DispatchQueue.main.async {
            respond(connection, status: "200 OK", body: [
                "ok": true,
                "last_heard": WakeWordListener.shared.lastHeard,
                "last_action": WakeWordListener.shared.lastAction,
                "wake_listening": WakeWordListener.shared.isActive,
                "healthy": WakeWordListener.shared.isHealthy,
                "wake_status": WakeWordListener.shared.statusMessage,
                "voice_backend": WakeWordListener.shared.voiceBackendName,
            ])
        }
    case ("POST", "/notify"):
        if let json = try? JSONSerialization.jsonObject(with: req.body) as? [String: Any] {
            let title = json["title"] as? String ?? "William Agent"
            let message = json["message"] as? String ?? ""
            let speak = json["speak"] as? Bool ?? false
            respond(connection, status: "200 OK", body: postNotification(title: title, message: message, speak: speak))
        } else {
            respond(connection, status: "200 OK", body: ["ok": false, "error": "invalid json"])
        }
    case ("POST", "/speak"):
        if let json = try? JSONSerialization.jsonObject(with: req.body) as? [String: Any],
           let text = json["text"] as? String {
            Voice.speak(text)
            respond(connection, status: "200 OK", body: ["ok": true])
        } else {
            respond(connection, status: "200 OK", body: ["ok": false, "error": "missing text"])
        }
    case ("POST", "/mute"):
        if let json = try? JSONSerialization.jsonObject(with: req.body) as? [String: Any],
           let muted = json["muted"] as? Bool {
            Voice.setMuted(muted)
            respond(connection, status: "200 OK", body: ["ok": true, "muted": Voice.isMuted])
        } else {
            respond(connection, status: "200 OK", body: ["ok": false, "error": "missing muted flag"])
        }
    case ("POST", "/permissions/prompt"):
        // User-initiated only — Accessibility + mic/speech; no Screen Recording prompts.
        DispatchQueue.main.async {
            WakeWordListener.shared.requestPermissionsUserInitiated()
        }
        let accessibility = Input.promptAccessibility()
        respond(connection, status: "200 OK", body: [
            "ok": true,
            "user_initiated": true,
            "accessibility": Input.accessibilityGranted,
            "accessibility_prompt": accessibility,
            "permissions": WakeWordListener.shared.authStatus(),
            "wake_listening": WakeWordListener.shared.isActive,
            "healthy": WakeWordListener.shared.isHealthy,
            "screen_capture_granted": false,
            "screen_capture_mode": "accessibility",
        ])
    case ("POST", "/permissions/bootstrap"):
        // Automated bootstrap — opens settings panes, no CGRequestScreenCaptureAccess.
        DispatchQueue.main.async {
            openMissingPermissionSettings()
        }
        var dialogResult: [String: Any] = ["ok": false, "acted": false]
        DispatchQueue.main.sync {
            dialogResult = DialogHandler.handleDialogs()
        }
        respond(connection, status: "200 OK", body: [
            "ok": true,
            "user_initiated": false,
            "accessibility": Input.accessibilityGranted,
            "permissions": WakeWordListener.shared.authStatus(),
            "screen_capture_granted": ScreenWatcher.shared.status()["screen_capture_granted"] as? Bool ?? false,
            "native": dialogResult,
        ])
    case ("POST", "/dialogs/handle"):
        var dialogResult: [String: Any] = ["ok": false, "error": "dialog handler unavailable"]
        DispatchQueue.main.sync {
            dialogResult = DialogHandler.handleDialogs()
        }
        respond(connection, status: "200 OK", body: dialogResult)
    case ("POST", "/screen/prompt-recording"):
        respond(connection, status: "200 OK", body: [
            "ok": false,
            "error": "Screen Recording disabled — William uses Accessibility API instead",
            "screen_capture_granted": false,
            "screen_capture_mode": "accessibility",
        ])
    case ("POST", "/voice/enroll/start"):
        DispatchQueue.main.async {
            WakeWordListener.shared.startGuidedVoiceEnrollment()
        }
        respond(connection, status: "200 OK", body: [
            "ok": true,
            "guided": true,
            "voice_profile": SpeakerVerifier.shared.status(),
        ])
    case ("POST", "/voice/enroll/start-guided"):
        DispatchQueue.main.async {
            WakeWordListener.shared.startGuidedVoiceEnrollment()
        }
        respond(connection, status: "200 OK", body: [
            "ok": true,
            "guided": true,
            "voice_profile": SpeakerVerifier.shared.status(),
        ])
    case ("POST", "/voice/enroll/cancel"):
        DispatchQueue.main.async {
            WakeWordListener.shared.cancelGuidedVoiceEnrollment()
        }
        respond(connection, status: "200 OK", body: ["ok": true, "voice_profile": SpeakerVerifier.shared.status()])
    case ("GET", "/voice/enroll/status"):
        respond(connection, status: "200 OK", body: [
            "ok": true,
            "voice_profile": SpeakerVerifier.shared.status(),
        ])
    case ("POST", "/voice/enroll/finish"):
        let ok = SpeakerVerifier.shared.finishEnrollment()
        respond(connection, status: "200 OK", body: ["ok": ok, "voice_profile": SpeakerVerifier.shared.status()])
    case ("POST", "/voice/enroll/clear"):
        SpeakerVerifier.shared.clearProfile()
        respond(connection, status: "200 OK", body: ["ok": true, "voice_profile": SpeakerVerifier.shared.status()])
    case ("GET", "/voice/profile"):
        respond(connection, status: "200 OK", body: ["ok": true, "voice_profile": SpeakerVerifier.shared.status()])
    case ("POST", "/screenshot"):
        respond(connection, status: "200 OK", body: takeScreenshot())
    case ("GET", "/desktop/context"):
        respond(connection, status: "200 OK", body: DesktopContext.snapshot())
    case ("POST", "/desktop/press"):
        if let json = try? JSONSerialization.jsonObject(with: req.body) as? [String: Any],
           let target = json["target"] as? String {
            respond(connection, status: "200 OK", body: DesktopContext.press(target: target))
        } else {
            respond(connection, status: "200 OK", body: ["ok": false, "error": "missing target"])
        }
    case ("GET", "/screen/status"):
        respond(connection, status: "200 OK", body: ["ok": true, "watcher": ScreenWatcher.shared.status()])
    case ("POST", "/screen/pause"):
        DispatchQueue.main.async {
            ScreenWatcher.shared.pause()
            respond(connection, status: "200 OK", body: ["ok": true, "watcher": ScreenWatcher.shared.status()])
        }
    case ("POST", "/screen/resume"):
        DispatchQueue.main.async {
            ScreenWatcher.shared.resume()
            respond(connection, status: "200 OK", body: ["ok": true, "watcher": ScreenWatcher.shared.status()])
        }
    case ("POST", "/wake/start"):
        DispatchQueue.main.async {
            NSApp.activate(ignoringOtherApps: true)
            WakeWordListener.shared.startOnMain()
        }
        respond(connection, status: "200 OK", body: [
            "ok": true,
            "wake_listening": WakeWordListener.shared.isActive,
            "healthy": WakeWordListener.shared.isHealthy,
            "voice_state": WakeWordListener.shared.voiceState,
        ])
    case ("POST", "/wake/listen"):
        DispatchQueue.main.async {
            NSApp.activate(ignoringOtherApps: true)
            WakeWordListener.shared.startListeningForCommand()
        }
        respond(connection, status: "200 OK", body: [
            "ok": true,
            "conversation_mode": WakeWordListener.shared.isConversationMode,
            "listening_for_response": WakeWordListener.shared.listeningForResponse,
            "voice_state": WakeWordListener.shared.voiceState,
        ])
    case ("POST", "/sleep"):
        DispatchQueue.main.async {
            WakeWordListener.shared.enterSleep()
        }
        respond(connection, status: "200 OK", body: [
            "ok": true,
            "sleeping": WakeWordListener.shared.isSleeping,
            "voice_state": WakeWordListener.shared.voiceState,
        ])
    case ("POST", "/transcript/clear"):
        DispatchQueue.main.async {
            WakeWordListener.shared.clearTranscriptOnMain()
        }
        respond(connection, status: "200 OK", body: ["ok": true])
    case ("POST", "/mousemove"):
        if let json = try? JSONSerialization.jsonObject(with: req.body) as? [String: Any],
           let x = json["x"] as? Double,
           let y = json["y"] as? Double {
            respond(connection, status: "200 OK", body: Input.moveMouse(x: x, y: y))
        } else {
            respond(connection, status: "200 OK", body: ["ok": false, "error": "missing x,y"])
        }
    case ("POST", "/mousedown"):
        if let json = try? JSONSerialization.jsonObject(with: req.body) as? [String: Any],
           let x = json["x"] as? Double,
           let y = json["y"] as? Double {
            let button = json["button"] as? String ?? "left"
            respond(connection, status: "200 OK", body: Input.mouseDown(x: x, y: y, button: button))
        } else {
            respond(connection, status: "200 OK", body: ["ok": false, "error": "missing x,y"])
        }
    case ("POST", "/mouseup"):
        if let json = try? JSONSerialization.jsonObject(with: req.body) as? [String: Any],
           let x = json["x"] as? Double,
           let y = json["y"] as? Double {
            let button = json["button"] as? String ?? "left"
            respond(connection, status: "200 OK", body: Input.mouseUp(x: x, y: y, button: button))
        } else {
            respond(connection, status: "200 OK", body: ["ok": false, "error": "missing x,y"])
        }
    case ("POST", "/click"):
        if let json = try? JSONSerialization.jsonObject(with: req.body) as? [String: Any],
           let x = json["x"] as? Double,
           let y = json["y"] as? Double {
            let button = json["button"] as? String ?? "left"
            respond(connection, status: "200 OK", body: Input.click(x: x, y: y, button: button))
        } else {
            respond(connection, status: "200 OK", body: ["ok": false, "error": "missing x,y"])
        }
    case ("POST", "/type"):
        if let json = try? JSONSerialization.jsonObject(with: req.body) as? [String: Any],
           let text = json["text"] as? String {
            respond(connection, status: "200 OK", body: Input.typeText(text))
        } else {
            respond(connection, status: "200 OK", body: ["ok": false, "error": "missing text"])
        }
    case ("POST", "/key"):
        if let json = try? JSONSerialization.jsonObject(with: req.body) as? [String: Any],
           let key = json["key"] as? String {
            let mods = json["modifiers"] as? [String] ?? []
            respond(connection, status: "200 OK", body: Input.pressKey(key, modifiers: mods))
        } else {
            respond(connection, status: "200 OK", body: ["ok": false, "error": "missing key"])
        }
    case ("POST", "/minis/restart"):
        respond(connection, status: "200 OK", body: MinisServiceControl.restartHelper())
    case ("POST", "/minis/hard-reset"):
        respond(connection, status: "200 OK", body: MinisServiceControl.hardResetHelper())
    default:
        respond(connection, status: "404 Not Found", body: ["ok": false, "error": "not found"])
    }
}

func handleConnection(_ connection: NWConnection) {
    connection.start(queue: .global())
    var buffer = Data()

    func receiveMore() {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65536) { data, _, isComplete, _ in
            if let data, !data.isEmpty {
                buffer.append(data)
            }
            if buffer.contains(Data("\r\n\r\n".utf8)) || isComplete {
                handleRequest(connection, buffer: buffer)
            } else {
                receiveMore()
            }
        }
    }
    receiveMore()
}

func startServer() {
    let params = NWParameters.tcp
    params.allowLocalEndpointReuse = true
    guard let listener = try? NWListener(using: params, on: NWEndpoint.Port(rawValue: port)!) else { return }
    listener.newConnectionHandler = handleConnection
    listener.start(queue: .global())
}

func menuBarSymbol(for listener: WakeWordListener) -> String {
    if listener.isSleeping {
        return "moon.zzz.fill"
    }
    if Voice.isSpeaking {
        return "waveform.circle.fill"
    }
    if listener.isBusy {
        return "brain.head.profile"
    }
    if listener.isAwaitingCommand || listener.isConversationMode {
        return "mic.fill"
    }
    if listener.isHealthy {
        return "ear.fill"
    }
    return "exclamationmark.triangle.fill"
}

func menuBarTooltip(for listener: WakeWordListener) -> String {
    switch listener.voiceState {
    case "sleeping":
        return "Sleeping — say hey jarvis"
    case "speaking":
        return "Speaking"
    case "busy":
        return "Thinking…"
    case "awaiting":
        return "I'm listening"
    case "conversation":
        return "Go ahead"
    case "standby":
        return "On guard — wake word active"
    case "unhealthy":
        return "Unhealthy — check permissions"
    default:
        return "William Agent"
    }
}

func applyMenuBarState(_ listener: WakeWordListener) {
    let symbol = menuBarSymbol(for: listener)
    if let image = NSImage(systemSymbolName: symbol, accessibilityDescription: menuBarTooltip(for: listener)) {
        image.isTemplate = true
        statusItem.button?.image = image
        statusItem.button?.title = ""
    } else {
        statusItem.button?.image = nil
        statusItem.button?.title = listener.isSleeping ? "💤" : "🤖"
    }
    statusItem.button?.toolTip = menuBarTooltip(for: listener)
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var stayAwakeActivity: NSObjectProtocol?
    private var minisBubble: MinisBubblePanel?

    func applicationDidFinishLaunching(_ notification: Notification) {
        stayAwakeActivity = ProcessInfo.processInfo.beginActivity(
            options: [.userInitiated, .idleSystemSleepDisabled],
            reason: "William Agent always-on voice"
        )

        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        applyMenuBarState(WakeWordListener.shared)

        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "William Agent — always listening", action: nil, keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Listen now", action: #selector(listenNow), keyEquivalent: "l"))
        menu.addItem(NSMenuItem(title: "Wake now", action: #selector(wakeNow), keyEquivalent: "w"))
        menu.addItem(NSMenuItem(title: "Sleep now", action: #selector(sleepNow), keyEquivalent: "s"))
        menu.addItem(NSMenuItem(title: "Mute voice", action: #selector(toggleMute), keyEquivalent: "m"))
        menu.addItem(NSMenuItem(title: "Open panel…", action: #selector(openPanel), keyEquivalent: "o"))
        menu.addItem(NSMenuItem(title: "Toggle Minis bubble", action: #selector(toggleMinisBubble), keyEquivalent: "b"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Enroll my voice", action: #selector(enrollVoice), keyEquivalent: "e"))
        menu.addItem(NSMenuItem(title: "Handle pop-ups now", action: #selector(handlePopupsNow), keyEquivalent: "h"))
        menu.addItem(NSMenuItem(title: "Grant permissions…", action: #selector(grantPermissions), keyEquivalent: "p"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        statusItem.menu = menu

        startServer()
        WakeWordListener.shared.startOnMain()

        minisBubble = MinisBubblePanel()
        minisBubble?.showBubble()

        Timer.scheduledTimer(withTimeInterval: 12, repeats: true) { _ in
            WakeWordListener.shared.ensureAwakeOnMain()
            applyMenuBarState(WakeWordListener.shared)
        }
    }

    @objc func wakeNow() {
        WakeWordListener.shared.startOnMain()
    }

    @objc func listenNow() {
        WakeWordListener.shared.startListeningForCommand()
    }

    @objc func sleepNow() {
        WakeWordListener.shared.enterSleep()
    }

    @objc func toggleMute() {
        Voice.setMuted(!Voice.isMuted)
    }

    @objc func openPanel() {
        let url = ProcessInfo.processInfo.environment["JARVIS_CORE_URL"] ?? "http://127.0.0.1:8787"
        if let panel = URL(string: url) {
            NSWorkspace.shared.open(panel)
        }
    }

    @objc func toggleMinisBubble() {
        guard let bubble = minisBubble else { return }
        if bubble.isVisible {
            bubble.hideBubble()
        } else {
            bubble.showBubble()
        }
    }

    @objc func enrollVoice() {
        WakeWordListener.shared.startVoiceEnrollment()
    }

    @objc func grantPermissions() {
        WakeWordListener.shared.requestPermissionsUserInitiated()
        _ = Input.promptAccessibility()
    }

    @objc func handlePopupsNow() {
        _ = DialogHandler.handleDialogs()
    }

    func applicationWillTerminate(_ notification: Notification) {
        ScreenWatcher.shared.stop()
        if let activity = stayAwakeActivity {
            ProcessInfo.processInfo.endActivity(activity)
        }
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
