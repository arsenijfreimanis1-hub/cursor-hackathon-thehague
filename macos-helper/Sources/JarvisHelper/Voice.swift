import AVFoundation

enum Voice {
    private static let synthesizer = AVSpeechSynthesizer()
    private static var finishHandler: (() -> Void)?

    static let displayName = "British (en-GB)"
    static var isMuted = false
    static var isSpeaking = false

    static func setMuted(_ muted: Bool) {
        isMuted = muted
        if muted, synthesizer.isSpeaking {
            stop()
        }
    }

    static func stop() {
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
        isSpeaking = false
    }

    private static let preferredVoices = ["Daniel", "Arthur", "Serena", "Martha", "Kate"]

    private static func pickVoice() -> AVSpeechSynthesisVoice? {
        let all = AVSpeechSynthesisVoice.speechVoices().filter { $0.language.hasPrefix("en-GB") }
        for name in preferredVoices {
            if let match = all.first(where: { $0.name.contains(name) }) {
                return match
            }
        }
        return AVSpeechSynthesisVoice(language: "en-GB")
    }

    static func sanitize(_ text: String) -> String {
        var s = text
        let patterns = [
            #"\[[^\]]+\]"#,
            #"\([^)]*\)"#,
            #"[`*#_]"#,
            #"https?://\S+"#,
        ]
        for pattern in patterns {
            s = s.replacingOccurrences(of: pattern, with: " ", options: .regularExpression)
        }
        s = s.replacingOccurrences(of: "\\s+", with: " ", options: .regularExpression)
        return s.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    static func speak(_ text: String, completion: (() -> Void)? = nil) {
        let trimmed = sanitize(text)
        guard !trimmed.isEmpty else {
            completion?()
            return
        }
        if isMuted {
            completion?()
            return
        }
        if synthesizer.isSpeaking {
            synthesizer.stopSpeaking(at: .immediate)
        }
        finishHandler = completion
        isSpeaking = true
        let utterance = AVSpeechUtterance(string: trimmed)
        utterance.voice = pickVoice()
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate * 0.88
        utterance.pitchMultiplier = 1.0
        utterance.preUtteranceDelay = 0.08
        utterance.postUtteranceDelay = 0.12
        synthesizer.delegate = Delegate.shared
        synthesizer.speak(utterance)
    }

    private final class Delegate: NSObject, AVSpeechSynthesizerDelegate {
        static let shared = Delegate()

        func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
            DispatchQueue.main.async {
                isSpeaking = false
                let handler = finishHandler
                finishHandler = nil
                handler?()
            }
        }

        func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didCancel utterance: AVSpeechUtterance) {
            DispatchQueue.main.async {
                isSpeaking = false
                let handler = finishHandler
                finishHandler = nil
                handler?()
            }
        }
    }
}
