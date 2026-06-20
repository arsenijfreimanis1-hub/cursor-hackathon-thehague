import SwiftUI

enum KioskTheme {
    static let accent = Color(red: 0.36, green: 0.55, blue: 0.94)
    static let accentDim = Color(red: 0.24, green: 0.35, blue: 0.62)
    static let surface = Color(red: 0.08, green: 0.09, blue: 0.12)
    static let surfaceRaised = Color(red: 0.11, green: 0.13, blue: 0.17)
    static let border = Color.white.opacity(0.08)
    static let success = Color(red: 0.24, green: 0.84, blue: 0.55)
    static let warn = Color(red: 0.96, green: 0.77, blue: 0.26)
    static let danger = Color(red: 0.94, green: 0.44, blue: 0.47)

    static let background = LinearGradient(
        colors: [
            Color(red: 0.04, green: 0.05, blue: 0.09),
            Color(red: 0.07, green: 0.09, blue: 0.14),
            Color(red: 0.05, green: 0.06, blue: 0.11),
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
}

struct KioskCard<Content: View>: View {
    var title: String?
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let title {
                Text(title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .textCase(.uppercase)
                    .tracking(0.6)
            }
            content
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(KioskTheme.surfaceRaised)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(KioskTheme.border, lineWidth: 1)
        )
    }
}

struct StatusPill: View {
    let label: String
    let on: Bool

    var body: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(on ? KioskTheme.success : Color.gray.opacity(0.4))
                .frame(width: 7, height: 7)
            Text(label)
                .font(.caption.weight(.medium))
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(Color.white.opacity(0.05))
        .clipShape(Capsule())
    }
}

struct ToastView: View {
    let message: String

    var body: some View {
        Text(message)
            .font(.subheadline.weight(.medium))
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(.ultraThinMaterial)
            .clipShape(Capsule())
            .shadow(color: .black.opacity(0.25), radius: 8, y: 4)
    }
}

struct PrimaryButtonStyle: ButtonStyle {
    var tint: Color = KioskTheme.accent

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.subheadline.weight(.semibold))
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(tint.opacity(configuration.isPressed ? 0.7 : 1))
            .foregroundStyle(.white)
            .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }
}
