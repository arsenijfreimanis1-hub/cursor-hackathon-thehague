import Foundation

final class OpenWakeWordBridge {
    private let command: String
    private var process: Process?
    private var pipe: Pipe?
    private(set) var isRunning = false
    private var restartWork: DispatchWorkItem?
    var onWakeDetected: (() -> Void)?
    var onProcessEnded: (() -> Void)?

    init(command: String) {
        self.command = command.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var isConfigured: Bool {
        !command.isEmpty
    }

    func start() {
        guard isConfigured else { return }
        restartWork?.cancel()
        restartWork = nil
        if isRunning, let process, process.isRunning {
            return
        }
        stop()
        killOrphanProcesses()
        launchProcess()
    }

    func stop() {
        restartWork?.cancel()
        restartWork = nil
        pipe?.fileHandleForReading.readabilityHandler = nil
        if let process, process.isRunning {
            process.terminate()
        }
        process = nil
        pipe = nil
        isRunning = false
    }

    private func killOrphanProcesses() {
        let killer = Process()
        killer.executableURL = URL(fileURLWithPath: "/usr/bin/pkill")
        killer.arguments = ["-f", "local_voice_openwakeword.py"]
        try? killer.run()
        killer.waitUntilExit()
        Thread.sleep(forTimeInterval: 0.25)
    }

    private func launchProcess() {
        let process = Process()
        let pipe = Pipe()
        process.executableURL = URL(fileURLWithPath: "/bin/zsh")
        process.arguments = ["-lc", shellCommand()]
        process.standardOutput = pipe
        process.standardError = pipe
        process.environment = ProcessInfo.processInfo.environment

        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            guard let self else { return }
            let data = handle.availableData
            guard !data.isEmpty, let text = String(data: data, encoding: .utf8) else { return }
            for rawLine in text.components(separatedBy: .newlines) {
                let line = rawLine.trimmingCharacters(in: .whitespacesAndNewlines)
                if line == "WAKE_DETECTED" || line == "1" {
                    DispatchQueue.main.async {
                        self.onWakeDetected?()
                    }
                }
            }
        }

        process.terminationHandler = { [weak self, weak process] _ in
            DispatchQueue.main.async {
                guard let self else { return }
                if self.process === process {
                    self.isRunning = false
                    self.process = nil
                    self.pipe = nil
                    self.onProcessEnded?()
                }
            }
        }

        do {
            try process.run()
            self.process = process
            self.pipe = pipe
            self.isRunning = true
        } catch {
            self.isRunning = false
            scheduleRestart(after: 1.5)
        }
    }

    private func shellCommand() -> String {
        if command.hasSuffix(".sh") {
            let escaped = command.replacingOccurrences(of: "\"", with: "\\\"")
            return "/bin/bash \"\(escaped)\""
        }
        return command
    }

    private func scheduleRestart(after delay: TimeInterval) {
        restartWork?.cancel()
        let work = DispatchWorkItem { [weak self] in
            guard let self, self.isConfigured, !self.isRunning else { return }
            self.launchProcess()
        }
        restartWork = work
        DispatchQueue.main.asyncAfter(deadline: .now() + delay, execute: work)
    }
}
