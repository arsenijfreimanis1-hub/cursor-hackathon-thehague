import AVFoundation
import AppKit
import Foundation

enum Sound {
    static let displayName = "wake chime / sleep tone"

    /// Ascending three-note chime — clearly "I'm listening".
    static func listening() {
        playSequence(
            notes: [(523.25, 0.09), (659.25, 0.09), (783.99, 0.14)],
            volume: 0.5
        )
    }

    /// Soft low tone — entering sleep mode.
    static func sleepEntry() {
        playSequence(
            notes: [(220.0, 0.12), (185.0, 0.14), (146.83, 0.18)],
            volume: 0.32
        )
    }

    /// Descending soft tone — clearly "going idle".
    static func notListening() {
        playSequence(
            notes: [(392.0, 0.1), (311.13, 0.11), (233.08, 0.16)],
            volume: 0.38
        )
    }

    private static func playSequence(notes: [(frequency: Double, duration: Double)], volume: Float) {
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                try playNotes(notes, volume: volume)
            } catch {
                DispatchQueue.main.async {
                    if notes[0].frequency > notes.last!.frequency {
                        NSSound(named: "Glass")?.play()
                    } else {
                        NSSound(named: "Basso")?.play()
                    }
                }
            }
        }
    }

    private static func playNotes(_ notes: [(frequency: Double, duration: Double)], volume: Float) throws {
        let engine = AVAudioEngine()
        let player = AVAudioPlayerNode()
        engine.attach(player)

        let format = AVAudioFormat(standardFormatWithSampleRate: 44_100, channels: 1)!
        engine.connect(player, to: engine.mainMixerNode, format: format)
        engine.mainMixerNode.outputVolume = volume

        var buffers: [AVAudioPCMBuffer] = []
        for note in notes {
            guard let buffer = makeToneBuffer(frequency: note.frequency, duration: note.duration, format: format) else {
                continue
            }
            buffers.append(buffer)
        }
        guard !buffers.isEmpty else { throw NSError(domain: "Sound", code: 1) }

        try engine.start()
        player.play()

        let group = DispatchGroup()
        group.enter()
        scheduleBuffers(player: player, buffers: buffers, index: 0) {
            group.leave()
        }
        group.wait()

        player.stop()
        engine.stop()
    }

    private static func scheduleBuffers(
        player: AVAudioPlayerNode,
        buffers: [AVAudioPCMBuffer],
        index: Int,
        completion: @escaping () -> Void
    ) {
        guard index < buffers.count else {
            completion()
            return
        }
        if index == buffers.count - 1 {
            player.scheduleBuffer(buffers[index], completionHandler: completion)
        } else {
            player.scheduleBuffer(buffers[index], completionHandler: nil)
            scheduleBuffers(player: player, buffers: buffers, index: index + 1, completion: completion)
        }
    }

    private static func makeToneBuffer(
        frequency: Double,
        duration: Double,
        format: AVAudioFormat
    ) -> AVAudioPCMBuffer? {
        let sampleRate = format.sampleRate
        let frameCount = AVAudioFrameCount(sampleRate * duration)
        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frameCount),
              let channel = buffer.floatChannelData?[0] else {
            return nil
        }

        buffer.frameLength = frameCount
        let total = Int(frameCount)
        for i in 0..<total {
            let t = Double(i) / sampleRate
            let attack = min(1.0, t / 0.012)
            let release = min(1.0, (duration - t) / 0.04)
            let envelope = Float(attack * release)
            let sample = sin(2.0 * .pi * frequency * t)
            channel[i] = Float(sample) * envelope * 0.85
        }
        return buffer
    }
}
