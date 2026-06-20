import SwiftUI

struct PromptComposer: View {
    @Binding var text: String
    var onSubmit: () -> Void
    var onGoal: () -> Void
    var onSleep: () -> Void
    var onWake: () -> Void

    var body: some View {
        HStack(alignment: .bottom, spacing: 12) {
            TextField("Ask William…", text: $text, axis: .vertical)
                .textFieldStyle(.plain)
                .lineLimit(1...4)
                .padding(12)
                .background(.white.opacity(0.06))
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .onSubmit(onSubmit)

            VStack(spacing: 8) {
                Button("Send", action: onSubmit)
                    .buttonStyle(.borderedProminent)
                Button("Goal", action: onGoal)
                    .buttonStyle(.bordered)
                HStack {
                    Button("Sleep", action: onSleep)
                    Button("Wake", action: onWake)
                }
                .buttonStyle(.borderless)
                .font(.caption)
            }
        }
    }
}
