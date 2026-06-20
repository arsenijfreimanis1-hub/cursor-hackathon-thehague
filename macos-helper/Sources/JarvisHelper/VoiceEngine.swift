import AVFoundation
import Foundation

enum VoiceBackend: String {
    case appleLegacy = "apple_legacy"
    case localOpenWakeWordWhisper = "local_openwakeword_whisper"

    init(rawValue: String?) {
        switch (rawValue ?? "").trimmingCharacters(in: .whitespacesAndNewlines).lowercased() {
        case VoiceBackend.localOpenWakeWordWhisper.rawValue:
            self = .localOpenWakeWordWhisper
        default:
            self = .appleLegacy
        }
    }
}

struct VoiceBackendConfig {
    let backend: VoiceBackend
    let wakeCommand: String
    let whisperCommand: String
    let whisperModelPath: String
    let maxCommandSeconds: TimeInterval
    let silenceCutoffSeconds: TimeInterval
    let silenceThreshold: Float
    let wakeCooldownSeconds: TimeInterval

    static func load() -> VoiceBackendConfig {
        let env = ProcessInfo.processInfo.environment
        return VoiceBackendConfig(
            backend: VoiceBackend(rawValue: env["WILLIAM_VOICE_BACKEND"]),
            wakeCommand: env["WILLIAM_OPENWAKEWORD_COMMAND"] ?? "",
            whisperCommand: env["WILLIAM_WHISPER_COMMAND"] ?? "",
            whisperModelPath: env["WILLIAM_WHISPER_MODEL"] ?? "",
            maxCommandSeconds: Self.doubleValue(env["WILLIAM_COMMAND_RECORD_SECONDS"], default: 6.0),
            silenceCutoffSeconds: Self.doubleValue(env["WILLIAM_COMMAND_SILENCE_SECONDS"], default: 1.1),
            silenceThreshold: Self.floatValue(env["WILLIAM_COMMAND_SILENCE_THRESHOLD"], default: 0.010),
            wakeCooldownSeconds: Self.doubleValue(env["WILLIAM_WAKE_COOLDOWN_SECONDS"], default: 2.0)
        )
    }

    var usesLocalPipeline: Bool {
        backend == .localOpenWakeWordWhisper
    }

    private static func doubleValue(_ raw: String?, default fallback: Double) -> Double {
        guard let raw, let value = Double(raw), value > 0 else { return fallback }
        return value
    }

    private static func floatValue(_ raw: String?, default fallback: Float) -> Float {
        guard let raw, let value = Float(raw), value > 0 else { return fallback }
        return value
    }
}

final class LocalCommandRecorder {
    private var engine = AVAudioEngine()
    private var outputFile: AVAudioFile?
    private var completion: ((Result<URL, Error>) -> Void)?
    private var stopWork: DispatchWorkItem?
    private var sampleURL: URL?
    private(set) var isRecording = false
    private var startedAt = Date.distantPast
    private var lastSpeechAt = Date.distantPast
    private var heardSpeech = false

    func start(
        maxDuration: TimeInterval,
        silenceCutoff: TimeInterval,
        silenceThreshold: Float,
        completion: @escaping (Result<URL, Error>) -> Void
    ) throws {
        if isRecording {
            stop()
        }

        let tempURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("william-command-\(UUID().uuidString).wav")
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        guard format.sampleRate > 0, format.channelCount > 0 else {
            throw NSError(domain: "LocalCommandRecorder", code: 1, userInfo: [
                NSLocalizedDescriptionKey: "invalid microphone input format",
            ])
        }

        let file = try AVAudioFile(forWriting: tempURL, settings: format.settings)
        self.outputFile = file
        self.completion = completion
        self.sampleURL = tempURL
        self.startedAt = Date()
        self.lastSpeechAt = Date()
        self.heardSpeech = false

        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 2048, format: format) { [weak self] buffer, _ in
            guard let self else { return }
            do {
                try file.write(from: buffer)
            } catch {
                self.finish(.failure(error))
                return
            }

            SpeakerVerifier.shared.process(buffer)

            let level = self.averageLevel(buffer)
            let now = Date()
            if level >= silenceThreshold {
                self.heardSpeech = true
                self.lastSpeechAt = now
            }

            let running = now.timeIntervalSince(self.startedAt)
            let silentFor = now.timeIntervalSince(self.lastSpeechAt)
            if running >= maxDuration || (self.heardSpeech && silentFor >= silenceCutoff && running >= 0.8) {
                DispatchQueue.main.async {
                    self.stop()
                }
            }
        }

        engine.prepare()
        try engine.start()
        isRecording = true

        let work = DispatchWorkItem { [weak self] in
            self?.stop()
        }
        stopWork = work
        DispatchQueue.main.asyncAfter(deadline: .now() + maxDuration + 0.35, execute: work)
    }

    func stop() {
        guard isRecording else { return }
        stopWork?.cancel()
        stopWork = nil
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        isRecording = false

        if let url = sampleURL {
            finish(.success(url))
        } else {
            finish(.failure(NSError(domain: "LocalCommandRecorder", code: 2, userInfo: [
                NSLocalizedDescriptionKey: "missing audio sample",
            ])))
        }
    }

    func cancel() {
        guard isRecording else { return }
        stopWork?.cancel()
        stopWork = nil
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        isRecording = false
        if let url = sampleURL {
            try? FileManager.default.removeItem(at: url)
        }
        completion = nil
        outputFile = nil
        sampleURL = nil
    }

    private func finish(_ result: Result<URL, Error>) {
        engine.inputNode.removeTap(onBus: 0)
        if engine.isRunning {
            engine.stop()
        }
        isRecording = false
        let callback = completion
        completion = nil
        outputFile = nil
        sampleURL = nil
        callback?(result)
    }

    private func averageLevel(_ buffer: AVAudioPCMBuffer) -> Float {
        guard let channel = buffer.floatChannelData?[0] else { return 0 }
        let frameCount = Int(buffer.frameLength)
        if frameCount == 0 { return 0 }
        var total: Float = 0
        for idx in 0..<frameCount {
            total += abs(channel[idx])
        }
        return total / Float(frameCount)
    }
}
