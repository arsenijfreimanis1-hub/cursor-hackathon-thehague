import SwiftUI

struct GoalApprovalSheet: View {
    let goal: GoalDetail
    var onApprove: () -> Void
    var onDismiss: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Approve goal plan")
                .font(.title2.bold())

            Text(goal.prompt)
                .foregroundStyle(.secondary)

            if let subtasks = goal.subtasks, !subtasks.isEmpty {
                Text("Subtasks")
                    .font(.headline)
                ForEach(Array(subtasks.enumerated()), id: \.offset) { index, task in
                    HStack(alignment: .top) {
                        Text("\(index + 1).")
                            .foregroundStyle(.secondary)
                        Text(task)
                    }
                }
            }

            HStack {
                Button("Cancel", action: onDismiss)
                Spacer()
                Button("Approve & run", action: onApprove)
                    .buttonStyle(.borderedProminent)
            }
        }
        .padding(24)
        .frame(minWidth: 420)
    }
}
