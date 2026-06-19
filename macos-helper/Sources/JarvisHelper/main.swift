import AppKit
import AVFoundation
import Foundation
import Network

let port: UInt16 = 8788
var statusItem: NSStatusItem!
let synthesizer = AVSpeechSynthesizer()

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

func takeScreenshot() -> [String: Any] {
    let url = FileManager.default.temporaryDirectory.appendingPathComponent("jarvis-screenshot.png")
    if runCommand("/usr/sbin/screencapture", ["-x", url.path]) {
        return ["ok": true, "path": url.path]
    }
    return ["ok": false, "error": "screencapture failed"]
}

func escapeAppleScript(_ text: String) -> String {
    text.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "\"", with: "\\\"")
}

func postNotification(title: String, message: String, speak: Bool) -> [String: Any] {
    let script = "display notification \"\(escapeAppleScript(message))\" with title \"\(escapeAppleScript(title))\""
    let ok = runCommand("/usr/bin/osascript", ["-e", script])
    if speak {
        let utterance = AVSpeechUtterance(string: message)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        synthesizer.speak(utterance)
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
        respond(connection, status: "200 OK", body: ["ok": true, "service": "jarvis-helper", "port": port])
    case ("POST", "/notify"):
        if let json = try? JSONSerialization.jsonObject(with: req.body) as? [String: Any] {
            let title = json["title"] as? String ?? "William Agent"
            let message = json["message"] as? String ?? ""
            let speak = json["speak"] as? Bool ?? false
            respond(connection, status: "200 OK", body: postNotification(title: title, message: message, speak: speak))
        } else {
            respond(connection, status: "200 OK", body: ["ok": false, "error": "invalid json"])
        }
    case ("POST", "/screenshot"):
        respond(connection, status: "200 OK", body: takeScreenshot())
    case ("POST", "/click"):
        respond(connection, status: "200 OK", body: ["ok": false, "error": "mouse control requires Accessibility permission"])
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

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.button?.title = "🤖"

        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "William Agent Helper", action: nil, keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        statusItem.menu = menu

        startServer()
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
