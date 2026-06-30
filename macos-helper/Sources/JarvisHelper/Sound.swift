import AppKit
import AVFoundation
import Foundation

enum Sound {
    static let displayName = "paying_attention.caf / stop_attention.caf"

    /// Ascending chime — clearly "I'm listening".
    static func listening() {
        playBundleSound(named: "paying_attention", fallback: listeningSynth)
    }

    /// Soft low tone — entering sleep mode.
    static func sleepEntry() {
        playSynth(
            notes: [(220.0, 0.12), (185.0, 0.14), (146.83, 0.18)],
            volume: 0.32
        )
    }

    /// Descending tone — going idle / command accepted.
    static func notListening() {
        playBundleSound(named: "stop_attention", fallback: notListeningSynth)
    }

    /// Brief acknowledgment — processing command.
    static func responding() {
        playSynth(notes: [(440.0, 0.06), (554.37, 0.08)], volume: 0.28)
    }

    private static func listeningSynth() {
        playSynth(
            notes: [(523.25, 0.09), (659.25, 0.09), (783.99, 0.14)],
            volume: 0.5
        )
    }

    private static func notListeningSynth() {
        playSynth(
            notes: [(392.0, 0.1), (311.13, 0.11), (233.08, 0.16)],
            volume: 0.38
        )
    }

    private static func playBundleSound(named: String, fallback: @escaping () -> Void) {
        DispatchQueue.main.async {
            if let url = Bundle.main.url(forResource: named, withExtension: "caf", subdirectory: "Sounds")
                ?? Bundle.main.url(forResource: named, withExtension: "caf") {
                let sound = NSSound(contentsOf: url, byReference: true)
                sound?.volume = 0.85
                if sound?.play() == true {
                    return
                }
            }
            fallback()
        }
    }

    private static func playSynth(
        notes: [(frequency: Double, duration: Double)],
        volume: Float
    ) {
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
