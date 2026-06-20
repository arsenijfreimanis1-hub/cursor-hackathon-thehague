import Foundation

final class WhisperBridge {
    private let command: String
    private let modelPath: String

    init(command: String, modelPath: String) {
        self.command = command.trimmingCharacters(in: .whitespacesAndNewlines)
        self.modelPath = modelPath.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var isConfigured: Bool {
        !command.isEmpty
    }

    func transcribe(audioURL: URL, completion: @escaping (Result<String, Error>) -> Void) {
        guard isConfigured else {
            completion(.failure(NSError(domain: "WhisperBridge", code: 1, userInfo: [
                NSLocalizedDescriptionKey: "whisper command not configured",
            ])))
            return
        }

        DispatchQueue.global(qos: .userInitiated).async {
            let process = Process()
            let out = Pipe()
            let err = Pipe()
            process.executableURL = URL(fileURLWithPath: "/bin/zsh")
            process.arguments = ["-lc", self.command]

            var env = ProcessInfo.processInfo.environment
            env["WILLIAM_AUDIO_FILE"] = audioURL.path
            env["WILLIAM_WHISPER_MODEL"] = self.modelPath
            process.environment = env
            process.standardOutput = out
            process.standardError = err

            do {
                try process.run()
                process.waitUntilExit()
                let stdout = String(data: out.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
                let stderr = String(data: err.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
                let combined = [stdout, stderr].joined(separator: "\n")
                let text = combined
                    .components(separatedBy: .newlines)
                    .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                    .filter { !$0.isEmpty && !$0.hasPrefix("[") }
                    .joined(separator: " ")
                    .trimmingCharacters(in: .whitespacesAndNewlines)

                if process.terminationStatus == 0, !text.isEmpty {
                    DispatchQueue.main.async {
                        completion(.success(text))
                    }
                } else {
                    let message = text.isEmpty ? stderr.trimmingCharacters(in: .whitespacesAndNewlines) : text
                    DispatchQueue.main.async {
                        completion(.failure(NSError(domain: "WhisperBridge", code: Int(process.terminationStatus), userInfo: [
                            NSLocalizedDescriptionKey: message.isEmpty ? "whisper transcription failed" : message,
                        ])))
                    }
                }
            } catch {
                DispatchQueue.main.async {
                    completion(.failure(error))
                }
            }
        }
    }
}
