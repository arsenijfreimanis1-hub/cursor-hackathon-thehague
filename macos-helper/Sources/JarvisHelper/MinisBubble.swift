import AppKit
import SwiftUI
import UniformTypeIdentifiers

private let coreBase = ProcessInfo.processInfo.environment["JARVIS_CORE_URL"] ?? "http://127.0.0.1:8787"
private let helperBase = ProcessInfo.processInfo.environment["JARVIS_HELPER_URL"] ?? "http://127.0.0.1:8788"

@MainActor
final class MinisViewModel: ObservableObject {
    @Published var coreConnected = false
    @Published var screenShareEnabled = false
    @Published var remoteControlEnabled = false
    @Published var statusText = "Checking…"
    @Published var actionText = ""

    private var pollTimer: Timer?

    func startPolling() {
        pollTimer?.invalidate()
        pollTimer = Timer.scheduledTimer(withTimeInterval: 3.0, repeats: true) { [weak self] _ in
            Task { await self?.refresh() }
        }
        Task { await refresh() }
    }

    func stopPolling() {
        pollTimer?.invalidate()
        pollTimer = nil
    }

    func refresh() async {
        do {
            let status = try await MinisAPI.fetchStatus()
            coreConnected = status.coreOk
            screenShareEnabled = status.screenShareEnabled
            remoteControlEnabled = status.remoteControlEnabled
            let helperOk = status.helperOk
            statusText = coreConnected
                ? (helperOk ? "Connected" : "Core up, helper down")
                : "JarvisCore offline"
        } catch {
            coreConnected = false
            statusText = "Offline"
        }
    }

    func setScreenShare(_ enabled: Bool) async {
        do {
            let result = try await MinisAPI.setScreenShare(enabled: enabled)
            screenShareEnabled = result.screenShareEnabled ?? enabled
        } catch {
            await refresh()
        }
    }

    func setRemoteControl(_ enabled: Bool) async {
        do {
            let result = try await MinisAPI.setRemoteControl(enabled: enabled)
            remoteControlEnabled = result.remoteControlEnabled ?? enabled
        } catch {
            await refresh()
        }
    }

    func restartServices() async {
        actionText = "Restarting…"
        do {
            if coreConnected {
                _ = try await MinisAPI.restart(target: "both")
                actionText = "Restart scheduled"
            } else {
                _ = try await MinisAPI.restartHelperLocal()
                actionText = "Helper restart sent"
            }
        } catch {
            actionText = "Restart failed"
        }
        try? await Task.sleep(nanoseconds: 2_000_000_000)
        actionText = ""
        await refresh()
    }

    func hardReset() async {
        actionText = "Hard reset…"
        do {
            if coreConnected {
                _ = try await MinisAPI.hardReset()
                actionText = "Hard reset scheduled"
            } else {
                _ = try await MinisAPI.hardResetHelperLocal()
                actionText = "Helper hard reset sent"
            }
        } catch {
            actionText = "Reset failed"
        }
        try? await Task.sleep(nanoseconds: 2_000_000_000)
        actionText = ""
        await refresh()
    }

    func buildFromSource() async {
        guard coreConnected else {
            actionText = "Core offline"
            return
        }
        actionText = "Building…"
        do {
            _ = try await MinisAPI.buildFromSource()
            actionText = "Build started"
        } catch {
            actionText = "Build failed"
        }
        try? await Task.sleep(nanoseconds: 3_000_000_000)
        actionText = ""
    }

    func uploadHelperBinary(from url: URL) async {
        guard coreConnected else {
            actionText = "Core offline"
            return
        }
        actionText = "Uploading…"
        do {
            let data = try Data(contentsOf: url)
            let result = try await MinisAPI.uploadHelperBinary(data)
            actionText = (result.ok ?? false) ? "Update applied" : "Upload failed"
        } catch {
            actionText = "Upload failed"
        }
        try? await Task.sleep(nanoseconds: 2_000_000_000)
        actionText = ""
        await refresh()
    }
}

private struct MinisStatusResponse: Decodable {
    let coreOk: Bool
    let screenShareEnabled: Bool
    let remoteControlEnabled: Bool
    let helperOk: Bool

    enum CodingKeys: String, CodingKey {
        case coreOk = "core_ok"
        case screenShareEnabled = "screen_share_enabled"
        case remoteControl
        case macosHelper = "macos_helper"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        coreOk = try container.decodeIfPresent(Bool.self, forKey: .coreOk) ?? false
        screenShareEnabled = try container.decodeIfPresent(Bool.self, forKey: .screenShareEnabled) ?? false
        if let remote = try container.decodeIfPresent([String: Bool].self, forKey: .remoteControl) {
            remoteControlEnabled = remote["remote_control_enabled"] ?? false
        } else {
            remoteControlEnabled = false
        }
        if let helper = try container.decodeIfPresent([String: Bool].self, forKey: .macosHelper) {
            helperOk = helper["ok"] ?? false
        } else {
            helperOk = false
        }
    }
}

private struct ToggleResponse: Decodable {
    let screenShareEnabled: Bool?
    let remoteControlEnabled: Bool?

    enum CodingKeys: String, CodingKey {
        case screenShareEnabled = "screen_share_enabled"
        case remoteControlEnabled = "remote_control_enabled"
    }
}

private struct ActionResponse: Decodable {
    let ok: Bool?
    let action: String?
    let error: String?
}

private enum MinisAPI {
    static func fetchStatus() async throws -> MinisStatusResponse {
        let url = URL(string: "\(coreBase)/api/minis/status")!
        let (data, response) = try await URLSession.shared.data(from: url)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(MinisStatusResponse.self, from: data)
    }

    static func setScreenShare(enabled: Bool) async throws -> ToggleResponse {
        try await post("\(coreBase)/api/minis/screen-share", body: ["enabled": enabled])
    }

    static func setRemoteControl(enabled: Bool) async throws -> ToggleResponse {
        try await post("\(coreBase)/api/remote/control", body: ["enabled": enabled])
    }

    static func restart(target: String) async throws -> ActionResponse {
        try await postAction("\(coreBase)/api/minis/restart", body: ["target": target])
    }

    static func hardReset() async throws -> ActionResponse {
        try await postAction("\(coreBase)/api/minis/hard-reset", body: [:])
    }

    static func buildFromSource() async throws -> ActionResponse {
        try await postAction("\(coreBase)/api/minis/update/build", body: [:])
    }

    static func uploadHelperBinary(_ data: Data) async throws -> ActionResponse {
        var request = URLRequest(url: URL(string: "\(coreBase)/api/minis/update/helper-binary")!)
        request.httpMethod = "POST"
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
        request.httpBody = data
        let (respData, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(ActionResponse.self, from: respData)
    }

    static func restartHelperLocal() async throws -> ActionResponse {
        try await postAction("\(helperBase)/minis/restart", body: [:])
    }

    static func hardResetHelperLocal() async throws -> ActionResponse {
        try await postAction("\(helperBase)/minis/hard-reset", body: [:])
    }

    private static func post(_ urlString: String, body: [String: Any]) async throws -> ToggleResponse {
        var request = URLRequest(url: URL(string: urlString)!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(ToggleResponse.self, from: data)
    }

    private static func postAction(_ urlString: String, body: [String: Any]) async throws -> ActionResponse {
        var request = URLRequest(url: URL(string: urlString)!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(ActionResponse.self, from: data)
    }
}

struct MinisBubbleView: View {
    @ObservedObject var model: MinisViewModel
    @State private var showHardResetConfirm = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Circle()
                    .fill(model.coreConnected ? Color.green : Color.red)
                    .frame(width: 10, height: 10)
                Text("Minis")
                    .font(.headline)
                Spacer()
                Text(model.statusText)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Toggle("Screen Share", isOn: Binding(
                get: { model.screenShareEnabled },
                set: { enabled in Task { await model.setScreenShare(enabled) } }
            ))
            .toggleStyle(.switch)
            .controlSize(.small)

            Toggle("Remote Control", isOn: Binding(
                get: { model.remoteControlEnabled },
                set: { enabled in Task { await model.setRemoteControl(enabled) } }
            ))
            .toggleStyle(.switch)
            .controlSize(.small)

            HStack(spacing: 6) {
                Button("Restart") {
                    Task { await model.restartServices() }
                }
                .controlSize(.small)

                Button("Hard Reset") {
                    showHardResetConfirm = true
                }
                .controlSize(.small)
            }

            HStack(spacing: 6) {
                Button("Build") {
                    Task { await model.buildFromSource() }
                }
                .controlSize(.small)

                Button("Upload…") {
                    pickAndUpload()
                }
                .controlSize(.small)
            }

            if !model.actionText.isEmpty {
                Text(model.actionText)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(14)
        .frame(width: 240)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
        .alert("Hard reset?", isPresented: $showHardResetConfirm) {
            Button("Cancel", role: .cancel) {}
            Button("Reset", role: .destructive) {
                Task { await model.hardReset() }
            }
        } message: {
            Text("Turns off screen share and remote control, then fully restarts JarvisCore and JarvisHelper.")
        }
    }

    private func pickAndUpload() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.allowedContentTypes = [.unixExecutable, .data]
        panel.message = "Select a JarvisHelper binary build"
        if panel.runModal() == .OK, let url = panel.url {
            Task { await model.uploadHelperBinary(from: url) }
        }
    }
}

final class MinisBubblePanel: NSPanel {
    private let viewModel = MinisViewModel()

    init() {
        super.init(
            contentRect: NSRect(x: 80, y: 120, width: 240, height: 220),
            styleMask: [.nonactivatingPanel, .hudWindow, .fullSizeContentView],
            backing: .buffered,
            defer: false
        )
        isFloatingPanel = true
        level = .floating
        collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        isMovableByWindowBackground = true
        titlebarAppearsTransparent = true
        titleVisibility = .hidden
        backgroundColor = .clear
        isOpaque = false
        hasShadow = true
        hidesOnDeactivate = false

        let hosting = NSHostingView(rootView: MinisBubbleView(model: viewModel))
        hosting.frame = contentRect(forFrameRect: frame)
        hosting.autoresizingMask = [.width, .height]
        contentView = hosting
    }

    func showBubble() {
        orderFrontRegardless()
        viewModel.startPolling()
    }

    func hideBubble() {
        viewModel.stopPolling()
        orderOut(nil)
    }
}
