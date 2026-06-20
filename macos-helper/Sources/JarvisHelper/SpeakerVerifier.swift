import AVFoundation
import Foundation

/// Lightweight speaker verification — learns Willy's voice fingerprint and rejects unknown speakers.
final class SpeakerVerifier {
    static let shared = SpeakerVerifier()

    private let profileURL: URL
    private let verifyThreshold: Float = 0.62
    private let enrollMinSamples = 8
    private let featureSize = 6

    private var recentFeatures: [[Float]] = []
    private var enrolledProfile: [Float]?
    private var enrolling = false
    private var enrollBuffer: [[Float]] = []

    var isEnrolled: Bool { enrolledProfile != nil }
    var isEnrolling: Bool { enrolling }

    private init() {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let dir = base.appendingPathComponent("JarvisHelper", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        profileURL = dir.appendingPathComponent("voice_profile.json")
        loadProfile()
    }

    func startEnrollment() {
        enrolling = true
        enrollBuffer.removeAll()
        recentFeatures.removeAll()
    }

    func cancelEnrollment() {
        enrolling = false
        enrollBuffer.removeAll()
    }

    @discardableResult
    func finishEnrollment() -> Bool {
        enrolling = false
        guard enrollBuffer.count >= enrollMinSamples else {
            enrollBuffer.removeAll()
            return false
        }
        let profile = average(enrollBuffer)
        enrolledProfile = profile
        enrollBuffer.removeAll()
        saveProfile(profile)
        return true
    }

    func process(_ buffer: AVAudioPCMBuffer) {
        guard let features = extractFeatures(from: buffer) else { return }
        recentFeatures.append(features)
        if recentFeatures.count > 40 {
            recentFeatures.removeFirst(recentFeatures.count - 40)
        }
        if enrolling {
            enrollBuffer.append(features)
        }
    }

    func verifyRecent() -> (verified: Bool, confidence: Float) {
        guard let profile = enrolledProfile, !recentFeatures.isEmpty else {
            return (true, 1.0)
        }
        let sample = average(Array(recentFeatures.suffix(12)))
        let confidence = similarity(profile, sample)
        return (confidence >= verifyThreshold, confidence)
    }

    func status() -> [String: Any] {
        let result = verifyRecent()
        return [
            "enrolled": isEnrolled,
            "enrolling": enrolling,
            "enroll_samples": enrollBuffer.count,
            "enroll_needed": enrollMinSamples,
            "verified": result.verified,
            "confidence": result.confidence,
            "threshold": verifyThreshold,
        ]
    }

    func clearProfile() {
        enrolledProfile = nil
        enrollBuffer.removeAll()
        recentFeatures.removeAll()
        try? FileManager.default.removeItem(at: profileURL)
    }

    private func extractFeatures(from buffer: AVAudioPCMBuffer) -> [Float]? {
        let samples: [Float]
        let sampleRate: Float

        if let channel = buffer.floatChannelData?[0] {
            let count = Int(buffer.frameLength)
            guard count >= 256 else { return nil }
            samples = Array(UnsafeBufferPointer(start: channel, count: count))
            sampleRate = Float(buffer.format.sampleRate)
        } else if let channel = buffer.int16ChannelData?[0] {
            let count = Int(buffer.frameLength)
            guard count >= 256 else { return nil }
            samples = (0..<count).map { Float(channel[$0]) / 32768.0 }
            sampleRate = Float(buffer.format.sampleRate)
        } else {
            return nil
        }

        let rms = sqrt(samples.map { $0 * $0 }.reduce(0, +) / Float(samples.count))
        var zcr: Float = 0
        for i in 1..<samples.count {
            if (samples[i] >= 0) != (samples[i - 1] >= 0) {
                zcr += 1
            }
        }
        zcr /= Float(samples.count)

        let pitch = estimatePitch(samples: samples, sampleRate: sampleRate)
        let peak = samples.map { abs($0) }.max() ?? 0
        var meanDiff: Float = 0
        for i in 1..<samples.count {
            meanDiff += abs(samples[i] - samples[i - 1])
        }
        meanDiff /= Float(max(samples.count - 1, 1))

        let lowBand = bandEnergy(samples: samples, sampleRate: sampleRate, minHz: 80, maxHz: 350)
        let midBand = bandEnergy(samples: samples, sampleRate: sampleRate, minHz: 350, maxHz: 2000)

        return [rms, zcr, pitch, peak, meanDiff, lowBand / max(midBand, 0.0001)]
    }

    private func estimatePitch(samples: [Float], sampleRate: Float) -> Float {
        let n = min(samples.count, 2048)
        guard n > 64 else { return 0 }
        var bestLag = 0
        var bestCorr: Float = 0
        let minLag = Int(sampleRate / 400)
        let maxLag = min(Int(sampleRate / 70), n / 2)
        guard maxLag > minLag else { return 0 }

        for lag in minLag..<maxLag {
            var corr: Float = 0
            for i in 0..<(n - lag) {
                corr += samples[i] * samples[i + lag]
            }
            if corr > bestCorr {
                bestCorr = corr
                bestLag = lag
            }
        }
        guard bestLag > 0 else { return 0 }
        return sampleRate / Float(bestLag)
    }

    /// Simple IIR band-pass energy estimate — no FFT required.
    private func bandEnergy(samples: [Float], sampleRate: Float, minHz: Float, maxHz: Float) -> Float {
        let lowAlpha = min(max(2 * Float.pi * minHz / sampleRate, 0.001), 0.99)
        let highAlpha = min(max(2 * Float.pi * maxHz / sampleRate, 0.001), 0.99)
        var lowPass: Float = 0
        var highPass: Float = 0
        var energy: Float = 0
        for sample in samples {
            lowPass += lowAlpha * (sample - lowPass)
            highPass += highAlpha * (sample - highPass)
            let band = highPass - lowPass
            energy += band * band
        }
        return sqrt(energy / Float(max(samples.count, 1)))
    }

    private func similarity(_ a: [Float], _ b: [Float]) -> Float {
        guard a.count == b.count, !a.isEmpty else { return 0 }
        var dot: Float = 0
        var na: Float = 0
        var nb: Float = 0
        for i in 0..<a.count {
            dot += a[i] * b[i]
            na += a[i] * a[i]
            nb += b[i] * b[i]
        }
        let denom = sqrt(na) * sqrt(nb)
        return denom > 0 ? dot / denom : 0
    }

    private func average(_ vectors: [[Float]]) -> [Float] {
        guard let first = vectors.first else { return [] }
        var result = [Float](repeating: 0, count: first.count)
        for vec in vectors {
            for i in 0..<first.count {
                result[i] += vec[i]
            }
        }
        let count = Float(vectors.count)
        return result.map { $0 / count }
    }

    private func loadProfile() {
        guard let data = try? Data(contentsOf: profileURL),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let features = json["features"] as? [Double],
              features.count == featureSize else { return }
        enrolledProfile = features.map { Float($0) }
    }

    private func saveProfile(_ profile: [Float]) {
        let payload: [String: Any] = [
            "features": profile.map { Double($0) },
            "enrolled_at": ISO8601DateFormatter().string(from: Date()),
        ]
        if let data = try? JSONSerialization.data(withJSONObject: payload) {
            try? data.write(to: profileURL, options: .atomic)
        }
    }
}
