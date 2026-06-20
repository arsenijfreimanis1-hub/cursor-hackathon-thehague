import Foundation

final class OpenWakeWordBridge {
    private let command: String
    private var process: Process?
    private var pipe: Pipe?
    private(set) var isRunning = false
    var onWakeDetected: (() -> Void)?

    init(command: String) {
        self.command = command.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var isConfigured: Bool {
        !command.isEmpty
    }

    func start() {
        guard isConfigured, !isRunning else { return }

        let process = Process()
        let pipe = Pipe()
        process.executableURL = URL(fileURLWithPath: "/bin/zsh")
        process.arguments = ["-lc", command]
        process.standardOutput = pipe
        process.standardError = pipe

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
        }
    }

    func stop() {
        pipe?.fileHandleForReading.readabilityHandler = nil
        if let process, process.isRunning {
            process.terminate()
        }
        process = nil
        pipe = nil
        isRunning = false
    }
}
