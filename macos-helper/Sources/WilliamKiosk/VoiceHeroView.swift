import SwiftUI

struct VoiceHeroView: View {
    let voiceUI: VoiceUI

    @State private var pulse = false

    var body: some View {
        VStack(spacing: 20) {
            ZStack {
                Circle()
                    .fill(Color(hex: voiceUI.color).opacity(0.12))
                    .frame(width: 200, height: 200)
                    .scaleEffect(pulse && voiceUI.animate ? 1.06 : 1.0)
                    .animation(voiceUI.animate ? .easeInOut(duration: 1.8).repeatForever(autoreverses: true) : .default, value: pulse)

                Circle()
                    .stroke(Color(hex: voiceUI.color).opacity(0.45), lineWidth: 2.5)
                    .frame(width: 156, height: 156)

                Image(systemName: symbolName)
                    .font(.system(size: 56, weight: .medium))
                    .foregroundStyle(Color(hex: voiceUI.color))
                    .symbolEffect(.pulse, isActive: voiceUI.animate)
            }

            VStack(spacing: 6) {
                Text(voiceUI.label)
                    .font(.system(size: 32, weight: .semibold, design: .rounded))

                Text(voiceUI.detail)
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 480)
            }
        }
        .padding(.vertical, 20)
        .onAppear { pulse = true }
        .onChange(of: voiceUI.state) { _, _ in pulse = true }
    }

    private var symbolName: String {
        switch voiceUI.state {
        case "sleeping": return "moon.zzz.fill"
        case "standby": return "ear.fill"
        case "awaiting", "conversation": return "mic.fill"
        case "busy": return "brain.head.profile"
        case "speaking": return "speaker.wave.2.fill"
        case "unhealthy": return "exclamationmark.triangle.fill"
        default: return "network.slash"
        }
    }
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let r = Double((int >> 16) & 0xFF) / 255
        let g = Double((int >> 8) & 0xFF) / 255
        let b = Double(int & 0xFF) / 255
        self.init(red: r, green: g, blue: b)
    }
}
