import Foundation

struct VoiceUI: Codable, Equatable {
    let state: String
    let label: String
    let detail: String
    let color: String
    let animate: Bool
}

struct OpenClawStatus: Codable {
    let ok: Bool?
    let whatsapp: Bool?
    let bridge: Bool?
    let error: String?
}

struct HealthResponse: Codable {
    let agent: String?
    let voice_ui: VoiceUI?
    let ollama: ServiceStatus?
    let worker: WorkerStatus?
    let macos_helper: HelperStatus?
    let cursor: CursorStatus?
    let openclaw: OpenClawStatus?
    let security: SecurityStatus?
    let scheduler: SchedulerStatus?
}

struct ServiceStatus: Codable {
    let ok: Bool?
    let default_model: String?
    let models: [String]?

    enum CodingKeys: String, CodingKey {
        case ok, models
        case default_model = "default"
    }
}

struct CursorStatus: Codable {
    let configured: Bool?
}

struct SecurityStatus: Codable {
    let full_access: Bool?
}

struct SchedulerStatus: Codable {
    let running: Bool?
}

struct WorkerStatus: Codable {
    let running: Bool?
    let parallel: Int?
    let task_active: Bool?
}

struct HelperStatus: Codable {
    let ok: Bool?
    let live_transcript: String?
    let live_transcript_partial: Bool?
    let last_final_transcript: String?
    let last_heard: String?
    let last_action: String?
    let voice_state: String?
    let wake_status: String?
    let wake_word: String?
    let sleeping: Bool?
    let healthy: Bool?
    let busy: Bool?
    let wake_listening: Bool?
    let awaiting_command: Bool?
    let listening_for_response: Bool?
    let conversation_mode: Bool?
    let voice_speaking: Bool?
    let voice_muted: Bool?
    let microphone: MicStatus?
    let permissions: PermissionStatus?
}

struct MicStatus: Codable {
    let available: Bool?
    let device: String?
}

struct PermissionStatus: Codable {
    let speech: String?
    let microphone: String?
}

struct ChatResponse: Codable {
    let reply: String?
    let session_id: String?
    let subtasks: [String]?
    let error: String?
    let engine: String?
    let executed: Bool?
    let is_new_session: Bool?
    let deferred: Bool?
}

struct ChatMessage: Codable, Identifiable {
    var id: String { "\(role)-\(content.hashValue)" }
    let role: String
    let content: String
    let engine: String?
}

struct SessionMessagesResponse: Codable {
    let messages: [ChatMessage]?
}

struct GoalDetail: Codable, Identifiable {
    let id: Int
    let prompt: String
    let status: String
    let batch_id: String?
    let subtasks: [String]?
    let tree: GoalTree?
    let tasks: [TaskRow]?
}

struct GoalTree: Codable {
    let done: Int?
    let failed: Int?
    let pending: Int?
    let total: Int?
}

struct TaskRow: Codable, Identifiable {
    let id: Int
    let title: String
    let status: String
    let parent_id: Int?
    let batch_id: String?
    let source: String?
}

struct CreateGoalResponse: Codable {
    let id: Int
    let prompt: String
    let status: String
    let subtasks: [String]?
}

struct ApproveGoalResponse: Codable {
    let ok: Bool?
    let error: String?
    let id: Int?
    let status: String?
}

struct DashboardResponse: Codable {
    let agent: String?
    let voice_ui: VoiceUI?
    let ollama: ServiceStatus?
    let macos_helper: HelperStatus?
    let worker: WorkerStatus?
    let security: SecurityStatus?
    let openclaw: OpenClawStatus?
    let tasks_active: [TaskRow]?
    let approvals_pending: [ApprovalRow]?
    let approval_count: Int?
}

struct ApprovalRow: Codable, Identifiable {
    let id: Int
    let action: String?
    let detail: String?
    let status: String?
    let created_at: String?
}

struct TerminalResult: Codable {
    let ok: Bool?
    let stdout: String?
    let stderr: String?
    let error: String?
}

struct ImproveRunStatus: Codable {
    let running: Bool?
    let run_id: Int?
    let status: String?
    let duration_minutes: Int?
    let seconds_remaining: Int?
    let fixes_applied: Int?
    let log: [ImproveLogEntry]?
    let findings: [ImproveFinding]?
}

struct ImproveLogEntry: Codable, Identifiable {
    var id: String { "\(ts ?? "")-\(message ?? "")" }
    let ts: String?
    let level: String?
    let message: String?
}

struct ImproveFinding: Codable, Identifiable {
    var id: String { name }
    let name: String
    let ok: Bool?
    let error: String?
    let detail: String?
}

struct StartImproveRunResponse: Codable {
    let ok: Bool?
    let error: String?
    let run_id: Int?
    let duration_minutes: Int?
    let ends_at: String?
}

struct GenericOK: Codable {
    let ok: Bool?
    let error: String?
    let reply: String?
}

struct SelfStatus: Codable {
    let branch: String?
    let on_sandbox: Bool?
    let diff_stat: String?
}

struct LearningReport: Codable {
    let report: String?
    let lessons_count: Int?
    let updated_at: String?
}

struct EventLogResponse: Codable {
    let events: [EventRow]?
    let stats: EventStats?
}

struct EventRow: Codable, Identifiable {
    let id: Int
    let event_type: String?
    let source: String?
    let detail: String?
    let created_at: String?
}

struct EventStats: Codable {
    let total: Int?
    let today: Int?
}

enum KioskSection: String, CaseIterable, Identifiable {
    case chat = "Command"
    case tasks = "Tasks"
    case home = "Voice"
    case approvals = "Approvals"
    case system = "System"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .home: return "waveform"
        case .chat: return "bubble.left.and.bubble.right.fill"
        case .tasks: return "list.bullet.rectangle"
        case .approvals: return "checkmark.shield.fill"
        case .system: return "gearshape.2.fill"
        }
    }
}
