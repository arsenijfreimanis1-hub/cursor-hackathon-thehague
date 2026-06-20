import Foundation

enum VoiceUIMapper {
    static func map(helper: HelperStatus) -> VoiceUI {
        guard helper.ok == true else {
            return VoiceUI(
                state: "offline",
                label: "Offline",
                detail: "JarvisHelper is not reachable",
                color: "#6b7280",
                animate: false
            )
        }

        if helper.voice_speaking == true {
            return preset("speaking")
        }
        if helper.busy == true {
            return preset("busy")
        }
        if helper.sleeping == true {
            return preset("sleeping")
        }
        if helper.healthy == false {
            return VoiceUI(
                state: "unhealthy",
                label: "Unhealthy",
                detail: helper.wake_status ?? "Check microphone and speech permissions",
                color: "#ef4444",
                animate: false
            )
        }
        if helper.awaiting_command == true || helper.listening_for_response == true {
            if helper.conversation_mode == true {
                return preset("conversation")
            }
            return preset("awaiting")
        }
        if helper.conversation_mode == true {
            return preset("conversation")
        }
        if helper.wake_listening == true || helper.voice_state == "standby" {
            return preset("standby")
        }
        if let vs = helper.voice_state, let mapped = presetOptional(vs) {
            return mapped
        }
        return preset("standby")
    }

    private static func presetOptional(_ state: String) -> VoiceUI? {
        switch state {
        case "offline", "unhealthy", "sleeping", "standby", "awaiting",
             "conversation", "busy", "speaking":
            return preset(state)
        default:
            return nil
        }
    }

    private static func preset(_ state: String) -> VoiceUI {
        switch state {
        case "sleeping":
            return VoiceUI(state: state, label: "Sleeping", detail: "Say Hey Willy — or tap Listen", color: "#7c3aed", animate: true)
        case "standby":
            return VoiceUI(state: state, label: "On guard", detail: "Say Hey Willy to start", color: "#f59e0b", animate: false)
        case "awaiting":
            return VoiceUI(state: state, label: "I'm listening", detail: "Speak your command", color: "#22c55e", animate: true)
        case "conversation":
            return VoiceUI(state: state, label: "Go ahead", detail: "Conversation mode — 3 min window", color: "#22c55e", animate: true)
        case "busy":
            return VoiceUI(state: state, label: "Thinking…", detail: "Processing your request", color: "#3b82f6", animate: true)
        case "speaking":
            return VoiceUI(state: state, label: "Speaking", detail: "William is talking", color: "#3b82f6", animate: true)
        case "unhealthy":
            return VoiceUI(state: state, label: "Unhealthy", detail: "Check mic & speech permissions", color: "#ef4444", animate: false)
        default:
            return VoiceUI(state: "offline", label: "Offline", detail: "Cannot reach services", color: "#6b7280", animate: false)
        }
    }
}
