import Foundation

actor JarvisAPIClient {
    static let shared = JarvisAPIClient()

    var coreBase = URL(string: "http://127.0.0.1:8787/api")!
    var helperBase = URL(string: "http://127.0.0.1:8788")!

    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 45
        return URLSession(configuration: config)
    }()

    func fetchImproveRunStatus() async throws -> ImproveRunStatus {
        try await get(ImproveRunStatus.self, url: coreBase.appendingPathComponent("self/improve-run/status"))
    }

    func startImproveRun(minutes: Int) async throws -> StartImproveRunResponse {
        try await post(StartImproveRunResponse.self, url: coreBase.appendingPathComponent("self/improve-run/start"), body: [
            "duration_minutes": minutes,
        ])
    }

    func stopImproveRun() async throws -> GenericOK {
        try await post(GenericOK.self, url: coreBase.appendingPathComponent("self/improve-run/stop"), body: [:])
    }

    func reconnectOpenClaw() async throws -> GenericOK {
        try await post(GenericOK.self, url: coreBase.appendingPathComponent("openclaw/reconnect"), body: [:])
    }

    func fetchDashboard() async throws -> DashboardResponse {
        try await get(DashboardResponse.self, url: coreBase.appendingPathComponent("dashboard"))
    }

    func fetchHealth() async throws -> HealthResponse {
        try await get(HealthResponse.self, url: coreBase.appendingPathComponent("health"))
    }

    func fetchHelperStatus() async throws -> HelperStatus {
        try await get(HelperStatus.self, url: helperBase.appendingPathComponent("status"))
    }

    func sendChat(_ message: String, sessionId: String?) async throws -> ChatResponse {
        var body: [String: Any] = ["message": message, "source": "kiosk"]
        if let sessionId { body["session_id"] = sessionId }
        return try await post(ChatResponse.self, url: coreBase.appendingPathComponent("chat"), body: body)
    }

    func fetchSessionMessages(_ sessionId: String) async throws -> [ChatMessage] {
        let res: SessionMessagesResponse = try await get(
            SessionMessagesResponse.self,
            url: coreBase.appendingPathComponent("sessions/\(sessionId)/messages")
        )
        return res.messages ?? []
    }

    func createGoal(_ prompt: String) async throws -> CreateGoalResponse {
        try await post(CreateGoalResponse.self, url: coreBase.appendingPathComponent("goals"), body: [
            "prompt": prompt,
            "source": "kiosk",
        ])
    }

    func fetchGoal(_ id: Int) async throws -> GoalDetail {
        try await get(GoalDetail.self, url: coreBase.appendingPathComponent("goals/\(id)"))
    }

    func approveGoal(_ id: Int) async throws -> ApproveGoalResponse {
        try await post(ApproveGoalResponse.self, url: coreBase.appendingPathComponent("goals/\(id)/approve"), body: [:])
    }

    func fetchTasks() async throws -> [TaskRow] {
        try await get([TaskRow].self, url: coreBase.appendingPathComponent("tasks"))
    }

    func fetchApprovals() async throws -> [ApprovalRow] {
        try await get([ApprovalRow].self, url: coreBase.appendingPathComponent("approvals"))
    }

    func resolveApproval(_ id: Int, approved: Bool) async throws -> GenericOK {
        try await post(GenericOK.self, url: coreBase.appendingPathComponent("approvals/\(id)"), body: [
            "approved": approved,
        ])
    }

    func voiceSleep() async throws {
        _ = try await postJSON(url: coreBase.appendingPathComponent("voice/sleep"), body: [:])
    }

    func voiceWake() async throws {
        _ = try await postJSON(url: coreBase.appendingPathComponent("voice/ensure-awake"), body: [:])
    }

    func voiceListen() async throws {
        _ = try await postJSON(url: coreBase.appendingPathComponent("voice/listen"), body: [:])
    }

    func clearTranscript() async throws {
        _ = try await postJSON(url: coreBase.appendingPathComponent("voice/clear-transcript"), body: [:])
    }

    func setMuted(_ muted: Bool) async throws {
        _ = try await postJSON(url: coreBase.appendingPathComponent("macos/mute"), body: ["muted": muted])
    }

    func setFullAccess(_ enabled: Bool) async throws {
        _ = try await postJSON(url: coreBase.appendingPathComponent("security/full-access"), body: ["enabled": enabled])
    }

    func runTerminal(_ command: String) async throws -> TerminalResult {
        try await post(TerminalResult.self, url: coreBase.appendingPathComponent("terminal/run"), body: [
            "command": command,
        ])
    }

    func analyzeDesktop() async throws -> GenericOK {
        try await post(GenericOK.self, url: coreBase.appendingPathComponent("desktop/analyze"), body: [:])
    }

    func triggerBriefing() async throws {
        _ = try await postJSON(url: coreBase.appendingPathComponent("scheduler/briefing"), body: [:])
    }

    func fetchLearningReport() async throws -> LearningReport {
        try await get(LearningReport.self, url: coreBase.appendingPathComponent("learning/report"))
    }

    func fetchSelfStatus() async throws -> SelfStatus {
        try await get(SelfStatus.self, url: coreBase.appendingPathComponent("self/status"))
    }

    func proposeSelfChange(_ description: String) async throws -> GenericOK {
        try await post(GenericOK.self, url: coreBase.appendingPathComponent("self/propose"), body: [
            "description": description,
        ])
    }

    func fetchEvents() async throws -> EventLogResponse {
        try await get(EventLogResponse.self, url: coreBase.appendingPathComponent("events"))
    }

    func testNotify() async throws {
        var components = URLComponents(url: coreBase.appendingPathComponent("macos/notify"), resolvingAgainstBaseURL: false)!
        components.queryItems = [
            URLQueryItem(name: "title", value: "William Agent"),
            URLQueryItem(name: "message", value: "Kiosk test notification"),
            URLQueryItem(name: "speak", value: "false"),
        ]
        var request = URLRequest(url: components.url!)
        request.httpMethod = "POST"
        let (_, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
    }

    private func get<T: Decodable>(_ type: T.Type, url: URL) async throws -> T {
        let (data, response) = try await session.data(from: url)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(T.self, from: data)
    }

    private func post<T: Decodable>(_ type: T.Type, url: URL, body: [String: Any]) async throws -> T {
        let data = try await postJSON(url: url, body: body)
        return try JSONDecoder().decode(T.self, from: data)
    }

    @discardableResult
    private func postJSON(url: URL, body: [String: Any]) async throws -> Data {
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            if let http = response as? HTTPURLResponse, let err = String(data: data, encoding: .utf8) {
                throw NSError(domain: "JarvisAPI", code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: err])
            }
            throw URLError(.badServerResponse)
        }
        return data
    }
}
