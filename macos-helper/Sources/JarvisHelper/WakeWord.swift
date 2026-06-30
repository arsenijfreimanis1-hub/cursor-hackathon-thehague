import AVFAudio
import AVFoundation
import Foundation
import Speech
import AppKit

final class WakeWordListener: NSObject {
    static let shared = WakeWordListener()
    private let voiceConfig = VoiceBackendConfig.load()
    private lazy var wakeBridge = OpenWakeWordBridge(command: voiceConfig.wakeCommand)
    private lazy var whisperBridge = WhisperBridge(
        command: voiceConfig.whisperCommand,
        modelPath: voiceConfig.whisperModelPath
    )
    private let localRecorder = LocalCommandRecorder()

    private let jarvisURL = URL(string: "http://127.0.0.1:8787/api/chat")!
    private let wakePhrases = [
        "hey willy", "hey willie", "hey william", "hey will", "hey wil",
        "a willy", "a will", "hay willy", "he willy", "hey woody",
        "yo willy", "ok willy", "hey billy",
    ]
    private let exitPhrases = ["thanks", "thank you", "goodbye", "good bye", "stop listening", "that's all", "thats all", "bye"]
    private let enrollPhrases = ["enroll my voice", "remember my voice", "learn my voice", "teach my voice"]
    private let cancelPhrases = ["cancel", "stop", "never mind", "forget it"]
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-GB"))
    private var audioEngine = AVAudioEngine()
    private var activeRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var tapInstalled = false
    private var startingUp = false
    private var awaitingCommand = false
    private var busy = false
    private var needsRestart = false
    private var commandTimer: DispatchWorkItem?
    private var commandDeadline: DispatchWorkItem?
    private var conversationTimer: DispatchWorkItem?
    private var partialFinalizeTimer: DispatchWorkItem?
    private var partialFinalizeText = ""
    private let partialFinalizeDelay: TimeInterval = 1.15
    private let maxCommandLength = 220
    private let silenceBeforeSpeak: TimeInterval = 0.6
    private var lastTranscriptAt = Date.distantPast
    private var pausedForSpeech = false
    private let commandHints = [
        "play", "open", "pause", "stop", "weather", "time", "spotify", "music",
        "remember", "what", "who", "how", "search", "skip", "next", "close",
        "switch", "tell", "check", "cancel", "goodbye", "thanks", "volume",
        "youtube", "launch", "minimize", "minimise", "focus", "recall",
    ]
    private var pendingCommand = ""
    private var lastWakeAt = Date.distantPast
    private var lastCommandSent = ""
    private var lastCommandAt = Date.distantPast
    private let cooldown: TimeInterval = 2
    private let commandCooldown: TimeInterval = 1.5
    private let conversationTimeout: TimeInterval = 180
    private let sleepJunkThreshold: TimeInterval = 45
    private let sleepBackgroundThreshold: TimeInterval = 50
    private var junkSpeechStartedAt = Date.distantPast
    private var junkSpeechEvents = 0
    private var sleepMode = false
    private var sleepPollTimer: DispatchWorkItem?
    private let sleepPollInterval: TimeInterval = 2.5
    private var wakePollActive = false

    private var conversationMode = false
    private var sessionId = ""
    private var lastHealthyAt = Date()
    private let staleThreshold: TimeInterval = 90
    private var speechPermissionRequested = false
    private var micPermissionRequested = false
    private var lastPermissionPromptAt = Date.distantPast
    private let permissionPromptCooldown: TimeInterval = 600
    private var audioRunning = false
    private var audioTransitioning = false
    private var commandTimeoutTimer: DispatchWorkItem?
    private let commandTimeout: TimeInterval = 40
    private var silenceWaitStartedAt = Date.distantPast
    private let maxSilenceWait: TimeInterval = 2.5
    private var localTranscribing = false
    private var guidedEnrollmentActive = false
    private var guidedPhraseRetries = 0

    var isActive = false
    var statusMessage = "initialising"
    var lastHeard = ""
    var lastAction = ""
    var liveTranscript = ""
    var liveTranscriptIsPartial = false
    var lastFinalTranscript = ""
    private(set) var isBusy = false

    var isAwaitingCommand: Bool { awaitingCommand }
    var isConversationMode: Bool { conversationMode }
    var isSleeping: Bool { sleepMode }
    var voiceBackendName: String { voiceConfig.backend.rawValue }
    private var usesLocalBackend: Bool { voiceConfig.usesLocalPipeline }
    var wakePhraseDisplay: String { usesLocalBackend ? "hey jarvis" : "hey willy" }
    var wakePhraseHint: String {
        usesLocalBackend
            ? "Say \"hey jarvis\" to wake William (local wake model)."
            : "Say \"hey willy\" to wake William."
    }
    var usesLocalVoiceBackend: Bool { usesLocalBackend }

    /// Canonical voice state for UIs — mirrors jarvis/services/voice_state.py
    var voiceState: String {
        if Voice.isSpeaking { return "speaking" }
        if busy || isBusy || localTranscribing { return "busy" }
        if sleepMode { return "sleeping" }
        if !isHealthy { return "unhealthy" }
        if awaitingCommand { return "awaiting" }
        if conversationMode { return "conversation" }
        if isActive { return "standby" }
        return "unhealthy"
    }

    func enterSleep() {
        DispatchQueue.main.async { self.enterSleepMode() }
    }
    var isHealthy: Bool {
        guard isActive, hasInputDevice() else { return false }
        if usesLocalBackend {
            if pausedForSpeech || Voice.isSpeaking || localTranscribing { return true }
            if localRecorder.isRecording { return true }
            if guidedEnrollmentActive || SpeakerVerifier.shared.isGuidedEnrollment { return true }
            if wakeBridge.isConfigured && !wakeBridge.isRunning && !sleepMode && !busy {
                startLocalWakeMonitoring()
            }
            return wakeBridge.isRunning || conversationMode || awaitingCommand
        }
        guard speechRecognizer?.isAvailable == true else { return false }
        if pausedForSpeech || Voice.isSpeaking { return true }
        return audioRunning && recognitionTask != nil
    }

    /// True when Willy is waiting for you to speak (post-wake or in conversation), not processing.
    var listeningForResponse: Bool {
        guard isActive, !busy else { return false }
        return awaitingCommand || conversationMode
    }

    private func hasInputDevice() -> Bool {
        let session = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.microphone, .external],
            mediaType: .audio,
            position: .unspecified
        )
        return !session.devices.isEmpty
    }

    func deviceStatus() -> [String: Any] {
        if !hasInputDevice() {
            return [
                "available": false,
                "reason": "No microphone detected. Plug in a USB mic, webcam, or headset.",
            ]
        }
        return ["available": true, "device": AVCaptureDevice.default(for: .audio)?.localizedName ?? "unknown"]
    }

    func authStatus() -> [String: Any] {
        var mic = "unknown"
        if #available(macOS 14.0, *) {
            switch AVAudioApplication.shared.recordPermission {
            case .granted: mic = "granted"
            case .denied: mic = "denied"
            case .undetermined: mic = "undetermined"
            @unknown default: mic = "unknown"
            }
        }
        let speechLabel: String
        if usesLocalBackend {
            speechLabel = "not_required"
        } else {
            let speech = SFSpeechRecognizer.authorizationStatus()
            switch speech {
            case .authorized: speechLabel = "granted"
            case .denied: speechLabel = "denied"
            case .restricted: speechLabel = "restricted"
            case .notDetermined: speechLabel = "undetermined"
            @unknown default: speechLabel = "unknown"
            }
        }
        return [
            "microphone": mic,
            "speech": speechLabel,
            "recognizer_available": usesLocalBackend ? whisperBridge.isConfigured : (speechRecognizer?.isAvailable ?? false),
            "audio_running": audioRunning,
            "conversation_mode": conversationMode,
            "session_id": sessionId,
            "voice_backend": voiceBackendName,
            "wake_command_configured": wakeBridge.isConfigured,
            "whisper_command_configured": whisperBridge.isConfigured,
        ]
    }

    func start() {
        DispatchQueue.main.async { self.startOnMain() }
    }

    /// Keep William listening 24/7 — heals zombie sessions where isActive but mic/recognizer died.
    func ensureAwake() {
        DispatchQueue.main.async { self.ensureAwakeOnMain() }
    }

    func ensureAwakeOnMain() {
        guard hasInputDevice() else {
            isActive = false
            statusMessage = "no microphone"
            return
        }
        guard !startingUp, !busy, !Voice.isSpeaking else { return }

        if usesLocalBackend {
            if sleepMode {
                startLocalWakeMonitoring()
                return
            }
            if localTranscribing || localRecorder.isRecording {
                return
            }
            if !isActive || !isHealthy {
                startOnMain()
            } else {
                startLocalWakeMonitoring()
            }
            return
        }

        if sleepMode {
            scheduleSleepPoll()
            return
        }

        if conversationMode, isHealthy, Date().timeIntervalSince(lastTranscriptAt) < 30 {
            return
        }

        if listeningForResponse, Date().timeIntervalSince(lastTranscriptAt) < 8 {
            return
        }

        if busy, Date().timeIntervalSince(lastCommandAt) > commandTimeout {
            lastAction = "watchdog: unstick busy"
            cancelCommandTimeout()
            busy = false
            isBusy = false
            Voice.stop()
            healSession(force: true)
            return
        }

        if isWaitingForPermissions() {
            if refreshPermissionsIfGranted() {
                return
            }
            return
        }

        let stale = Date().timeIntervalSince(lastHealthyAt) > staleThreshold
        let audioDown = !audioRunning && !pausedForSpeech
        let recognizerDown = recognitionTask == nil && isActive && !pausedForSpeech
        let needsStart = !isActive
            || statusMessage.contains("unavailable")
            || statusMessage.contains("failed")
            || statusMessage == "no microphone"
            || statusMessage == "initialising"
            || statusMessage == "starting"

        if needsStart {
            lastAction = "watchdog: start"
            startOnMain()
            return
        }

        if isActive && (audioDown || recognizerDown || stale) {
            lastAction = "watchdog: heal"
            healSession(force: audioDown || recognizerDown || stale)
        }
    }

    /// User clicked menu or API — allow one fresh permission prompt.
    func requestPermissionsUserInitiated() {
        speechPermissionRequested = false
        micPermissionRequested = false
        lastPermissionPromptAt = .distantPast
        NSApp.activate(ignoringOtherApps: true)
        startOnMain()
    }

    private func isWaitingForPermissions() -> Bool {
        statusMessage == "requesting permissions"
            || statusMessage == "requesting microphone"
            || statusMessage.contains("permission needed")
            || statusMessage.contains("permission denied")
    }

    private func refreshPermissionsIfGranted() -> Bool {
        let speech = SFSpeechRecognizer.authorizationStatus()
        if speech == .authorized {
            if #available(macOS 14.0, *) {
                if AVAudioApplication.shared.recordPermission == .granted {
                    lastAction = "permissions granted"
                    beginSession()
                    return true
                }
                if !micPermissionRequested {
                    ensureMicPermission()
                }
                return false
            }
            beginSession()
            return true
        }
        return false
    }

    private func requestSpeechPermissionOnce() {
        switch SFSpeechRecognizer.authorizationStatus() {
        case .authorized:
            ensureMicPermission()
        case .denied, .restricted:
            isActive = false
            statusMessage = "speech permission denied — enable JarvisHelper in System Settings"
        case .notDetermined:
            let now = Date()
            if speechPermissionRequested,
               now.timeIntervalSince(lastPermissionPromptAt) < permissionPromptCooldown {
                isActive = false
                statusMessage = "speech permission needed — enable JarvisHelper in System Settings"
                return
            }
            speechPermissionRequested = true
            lastPermissionPromptAt = now
            statusMessage = "requesting permissions"
            NSApp.activate(ignoringOtherApps: true)
            SFSpeechRecognizer.requestAuthorization { [weak self] status in
                DispatchQueue.main.async {
                    guard let self else { return }
                    guard status == .authorized else {
                        self.isActive = false
                        self.statusMessage = "speech permission denied — enable JarvisHelper in System Settings"
                        return
                    }
                    self.ensureMicPermission()
                }
            }
        @unknown default:
            isActive = false
            statusMessage = "speech permission unknown"
        }
    }

    private func requestMicPermissionOnce() {
        lastAction = "check mic"
        if #available(macOS 14.0, *) {
            switch AVAudioApplication.shared.recordPermission {
            case .granted:
                beginSession()
            case .denied:
                isActive = false
                statusMessage = "microphone permission denied — enable JarvisHelper in System Settings"
            case .undetermined:
                let now = Date()
                if micPermissionRequested,
                   now.timeIntervalSince(lastPermissionPromptAt) < permissionPromptCooldown {
                    isActive = false
                    statusMessage = "microphone permission needed — enable JarvisHelper in System Settings"
                    return
                }
                micPermissionRequested = true
                lastPermissionPromptAt = now
                statusMessage = "requesting microphone"
                NSApp.activate(ignoringOtherApps: true)
                AVAudioApplication.requestRecordPermission { [weak self] granted in
                    DispatchQueue.main.async {
                        guard let self else { return }
                        guard granted else {
                            self.isActive = false
                            self.statusMessage = "microphone permission denied — enable JarvisHelper in System Settings"
                            return
                        }
                        self.beginSession()
                    }
                }
            @unknown default:
                beginSession()
            }
        } else {
            beginSession()
        }
    }

    private func resetJunkTracking() {
        junkSpeechStartedAt = .distantPast
        junkSpeechEvents = 0
    }

    private func noteJunkSpeech(_ reason: String) {
        let now = Date()
        if junkSpeechStartedAt == .distantPast {
            junkSpeechStartedAt = now
        }
        junkSpeechEvents += 1
        lastAction = reason
        let elapsed = now.timeIntervalSince(junkSpeechStartedAt)
        let threshold = conversationMode ? sleepBackgroundThreshold : sleepJunkThreshold
        if elapsed >= threshold || junkSpeechEvents >= 12 {
            enterSleepMode()
        }
    }

    private func enterSleepMode() {
        guard !sleepMode else { return }
        sleepMode = true
        conversationMode = false
        awaitingCommand = false
        sessionId = ""
        conversationTimer?.cancel()
        commandTimer?.cancel()
        commandDeadline?.cancel()
        cancelPartialFinalize()
        recognitionTask?.cancel()
        stopAudioCapture()
        if usesLocalBackend {
            stopLocalWakeMonitoring()
        }
        isActive = false
        statusMessage = "sleeping"
        resetJunkTracking()
        lastAction = "entering sleep"
        Sound.sleepEntry()
        Voice.speak("Going to sleep, boss. Say hey Willie when you need me.") { [weak self] in
            if self?.usesLocalBackend == true {
                self?.startLocalWakeMonitoring()
            } else {
                self?.scheduleSleepPoll()
            }
        }
    }

    private func exitSleepMode() {
        guard sleepMode else { return }
        sleepMode = false
        wakePollActive = false
        sleepPollTimer?.cancel()
        resetJunkTracking()
        lastAction = "wake from sleep"
        statusMessage = "starting"
        beginSession()
    }

    private func scheduleSleepPoll() {
        if usesLocalBackend {
            startLocalWakeMonitoring()
            return
        }
        sleepPollTimer?.cancel()
        guard sleepMode, !busy, !Voice.isSpeaking else { return }
        let work = DispatchWorkItem { [weak self] in
            self?.pollForWakeWord()
        }
        sleepPollTimer = work
        DispatchQueue.main.asyncAfter(deadline: .now() + sleepPollInterval, execute: work)
    }

    private func pollForWakeWord() {
        if usesLocalBackend {
            startLocalWakeMonitoring()
            return
        }
        guard sleepMode, !busy, !Voice.isSpeaking, !wakePollActive else {
            scheduleSleepPoll()
            return
        }
        guard speechRecognizer?.isAvailable == true else {
            scheduleSleepPoll()
            return
        }
        wakePollActive = true
        do {
            try startAudioCapture()
        } catch {
            wakePollActive = false
            scheduleSleepPoll()
            return
        }
        activeRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let request = activeRequest else {
            wakePollActive = false
            scheduleSleepPoll()
            return
        }
        request.shouldReportPartialResults = true
        recognitionTask = speechRecognizer?.recognitionTask(with: request) { [weak self] result, _ in
            guard let self else { return }
            if let result {
                let text = result.bestTranscription.formattedString.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
                if !text.isEmpty, self.matchesWakePhrase(text) || self.fuzzyNearWake(text) {
                    self.recognitionTask?.cancel()
                    self.stopAudioCapture()
                    self.wakePollActive = false
                    self.exitSleepMode()
                    return
                }
            }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.8) { [weak self] in
            guard let self, self.sleepMode, self.wakePollActive else { return }
            self.recognitionTask?.cancel()
            self.stopAudioCapture()
            self.wakePollActive = false
            self.scheduleSleepPoll()
        }
    }

    private func healSession(force: Bool = false) {
        guard !sleepMode else { return }
        guard !busy, !Voice.isSpeaking, !pausedForSpeech, !audioTransitioning else { return }

        if usesLocalBackend {
            if localTranscribing || localRecorder.isRecording {
                return
            }
            startLocalWakeMonitoring()
            isActive = true
            audioRunning = wakeBridge.isRunning || localRecorder.isRecording
            statusMessage = conversationMode ? "conversation" : "listening"
            lastHealthyAt = Date()
            return
        }

        if audioRunning && audioEngine.isRunning && tapInstalled {
            if force || recognitionTask == nil || needsRestart {
                restartRecognition()
                needsRestart = false
            }
            isActive = true
            statusMessage = conversationMode ? "conversation" : "listening"
            lastHealthyAt = Date()
            return
        }

        do {
            try startAudioCapture()
        } catch {
            lastAction = "heal failed: \(error.localizedDescription)"
            isActive = false
            statusMessage = "audio failed: \(error.localizedDescription)"
            return
        }

        if force || recognitionTask == nil || needsRestart {
            restartRecognition()
            needsRestart = false
        }

        isActive = true
        statusMessage = conversationMode ? "conversation" : "listening"
        lastHealthyAt = Date()
    }

    /// Kiosk / remote: open conversation window without saying the wake word.
    func startListeningForCommand() {
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            if self.sleepMode {
                self.exitSleepMode()
            }
            if !self.isActive {
                self.startOnMain()
            }
            self.sessionId = ""
            self.awaitingCommand = false
            self.clearTranscriptFeed()
            self.enterConversationMode()
            self.lastAction = "manual listen"
            Sound.listening()
            if self.usesLocalBackend {
                self.beginLocalCommandCapture(reason: "manual listen")
            } else {
                self.healSession(force: true)
            }
        }
    }

    func startOnMain() {
        guard !startingUp, !busy else { return }
        if sleepMode {
            exitSleepMode()
            return
        }
        startingUp = true
        defer { startingUp = false }

        statusMessage = "starting"
        lastAction = "boot"

        guard hasInputDevice() else {
            isActive = false
            statusMessage = "no microphone"
            return
        }

        if usesLocalBackend {
            requestMicPermissionOnce()
            return
        }

        switch SFSpeechRecognizer.authorizationStatus() {
        case .authorized:
            requestMicPermissionOnce()
        case .denied, .restricted:
            isActive = false
            statusMessage = "speech permission denied — enable JarvisHelper in System Settings"
        case .notDetermined:
            requestSpeechPermissionOnce()
        @unknown default:
            isActive = false
            statusMessage = "speech permission unknown"
        }
    }

    private func ensureMicPermission() {
        requestMicPermissionOnce()
    }

    private func beginSession() {
        lastAction = "begin session"
        if usesLocalBackend {
            startLocalWakeMonitoring()
            isActive = true
            audioRunning = wakeBridge.isRunning || localRecorder.isRecording
            statusMessage = conversationMode ? "conversation" : (sleepMode ? "sleeping" : "listening")
            lastAction = wakeBridge.isConfigured ? "ready" : "local voice command missing"
            lastHealthyAt = Date()
            return
        }
        guard let speechRecognizer, speechRecognizer.isAvailable else {
            isActive = false
            statusMessage = "speech recognizer unavailable"
            return
        }

        do {
            try startAudioCapture()
        } catch {
            isActive = false
            statusMessage = "audio failed: \(error.localizedDescription)"
            lastAction = statusMessage
            return
        }

        restartRecognition()
        isActive = true
        statusMessage = conversationMode ? "conversation" : "listening"
        lastAction = "ready"
        lastHealthyAt = Date()
    }

    private func stopAudioCapture() {
        if usesLocalBackend {
            localRecorder.cancel()
            audioRunning = false
            return
        }
        if tapInstalled {
            audioEngine.inputNode.removeTap(onBus: 0)
            tapInstalled = false
        }
        if audioEngine.isRunning {
            audioEngine.stop()
        }
        audioRunning = false
    }

    private func startAudioCapture() throws {
        if usesLocalBackend {
            audioRunning = localRecorder.isRecording
            return
        }
        if audioRunning && audioEngine.isRunning && tapInstalled {
            return
        }
        if audioTransitioning { return }
        guard hasInputDevice() else {
            throw NSError(domain: "WakeWord", code: 2, userInfo: [
                NSLocalizedDescriptionKey: "no microphone",
            ])
        }

        audioTransitioning = true
        defer { audioTransitioning = false }

        stopAudioCapture()
        Thread.sleep(forTimeInterval: 0.15)

        let engine = AVAudioEngine()
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        guard format.sampleRate > 0, format.channelCount > 0 else {
            throw NSError(domain: "WakeWord", code: 1, userInfo: [
                NSLocalizedDescriptionKey: "invalid input format",
            ])
        }

        input.installTap(onBus: 0, bufferSize: 4096, format: format) { [weak self] buffer, _ in
            self?.activeRequest?.append(buffer)
            SpeakerVerifier.shared.process(buffer)
        }

        do {
            engine.prepare()
            try engine.start()
        } catch {
            stopAudioCapture()
            throw error
        }
        audioEngine = engine
        tapInstalled = true
        audioRunning = true
        lastAction = "audio running \(Int(format.sampleRate))Hz"
    }

    private func restartRecognition() {
        commandTimer?.cancel()
        recognitionTask?.cancel()
        recognitionTask = nil

        activeRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let request = activeRequest else { return }
        request.shouldReportPartialResults = true
        if #available(macOS 14.0, *) {
            request.addsPunctuation = true
        }
        if conversationMode || awaitingCommand {
            request.taskHint = .dictation
        } else {
            request.taskHint = .search
        }

        recognitionTask = speechRecognizer?.recognitionTask(with: request) { [weak self] result, error in
            guard let self else { return }
            if let result {
                self.handleTranscript(result.bestTranscription.formattedString, isFinal: result.isFinal)
            }
            if let error {
                self.handleRecognitionError(error)
            }
        }
        needsRestart = false
    }

    private func handleRecognitionError(_ error: Error) {
        let msg = error.localizedDescription.lowercased()
        if msg.contains("cancel") { return }
        if msg.contains("no speech detected") {
            if busy {
                needsRestart = true
            } else if isActive {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { [weak self] in
                    guard let self, !self.busy, self.isActive else { return }
                    self.restartRecognition()
                }
            }
            return
        }

        lastAction = "recognition error: \(error.localizedDescription)"
        if msg.contains("siri") || msg.contains("dictation") {
            isActive = false
            statusMessage = "enable Siri and Dictation in System Settings"
            return
        }

        if busy {
            needsRestart = true
            return
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { [weak self] in
            guard let self, !self.busy, self.isActive else {
                self?.needsRestart = true
                return
            }
            self.restartRecognition()
        }
    }

    private func startLocalWakeMonitoring() {
        guard usesLocalBackend, !pausedForSpeech, !Voice.isSpeaking, !busy, !localRecorder.isRecording, !localTranscribing else { return }
        guard !guidedEnrollmentActive, !SpeakerVerifier.shared.isGuidedEnrollment else { return }
        wakeBridge.onWakeDetected = { [weak self] in
            self?.handleLocalWakeDetected()
        }
        wakeBridge.onProcessEnded = { [weak self] in
            guard let self else { return }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                guard self.isActive, !self.busy, !self.sleepMode, !self.guidedEnrollmentActive else { return }
                self.startLocalWakeMonitoring()
            }
        }
        wakeBridge.start()
        audioRunning = wakeBridge.isRunning || localRecorder.isRecording
        if !wakeBridge.isConfigured {
            isActive = false
            statusMessage = "openwakeword command not configured"
            lastAction = "set WILLIAM_OPENWAKEWORD_COMMAND"
            return
        }
        if wakeBridge.isConfigured && !wakeBridge.isRunning {
            lastAction = "wake monitor starting"
        }
        isActive = true
        if !sleepMode && !conversationMode && !awaitingCommand {
            statusMessage = "listening"
        }
        lastHealthyAt = Date()
    }

    private func stopLocalWakeMonitoring() {
        wakeBridge.stop()
        audioRunning = localRecorder.isRecording
    }

    private func handleLocalWakeDetected() {
        guard usesLocalBackend, !busy, !Voice.isSpeaking, !localRecorder.isRecording, !localTranscribing else { return }
        guard Date().timeIntervalSince(lastWakeAt) > voiceConfig.wakeCooldownSeconds else { return }
        resetJunkTracking()
        lastWakeAt = Date()
        if sleepMode {
            sleepMode = false
        }
        enterConversationMode()
        awaitingCommand = true
        pendingCommand = ""
        lastAction = "wake detected"
        Sound.listening()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) { [weak self] in
            self?.beginLocalCommandCapture(reason: "wake")
        }
    }

    private func beginLocalCommandCapture(reason: String) {
        guard usesLocalBackend, !localTranscribing, !busy, !Voice.isSpeaking else { return }
        guard whisperBridge.isConfigured else {
            awaitingCommand = false
            statusMessage = "whisper command not configured"
            lastAction = "set WILLIAM_WHISPER_COMMAND"
            isActive = false
            return
        }
        stopLocalWakeMonitoring()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) { [weak self] in
            self?.startLocalCommandRecorder(reason: reason)
        }
    }

    private func startLocalCommandRecorder(reason: String) {
        guard usesLocalBackend, !localTranscribing, !busy, !Voice.isSpeaking else { return }
        awaitingCommand = true
        audioRunning = true
        statusMessage = "recording"
        lastAction = reason

        do {
            try localRecorder.start(
                maxDuration: voiceConfig.maxCommandSeconds,
                silenceCutoff: voiceConfig.silenceCutoffSeconds,
                silenceThreshold: voiceConfig.silenceThreshold
            ) { [weak self] result in
                guard let self else { return }
                self.audioRunning = false
                switch result {
                case .success(let url):
                    self.transcribeLocalRecording(url)
                case .failure(let error):
                    self.awaitingCommand = false
                    self.lastAction = "record failed: \(error.localizedDescription)"
                    self.statusMessage = "record failed"
                    self.healSession(force: true)
                }
            }
        } catch {
            awaitingCommand = false
            audioRunning = false
            statusMessage = "record failed: \(error.localizedDescription)"
            lastAction = statusMessage
        }
    }

    private func transcribeLocalRecording(_ url: URL) {
        guard usesLocalBackend else { return }
        localTranscribing = true
        statusMessage = "transcribing"
        lastAction = "whisper transcription"

        whisperBridge.transcribe(audioURL: url) { [weak self] result in
            guard let self else { return }
            self.localTranscribing = false
            try? FileManager.default.removeItem(at: url)
            switch result {
            case .success(let text):
                let cleaned = text.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
                self.lastTranscriptAt = Date()
                self.lastHealthyAt = Date()
                if !cleaned.isEmpty {
                    self.lastHeard = cleaned
                    self.liveTranscript = cleaned
                    self.liveTranscriptIsPartial = false
                    self.processTranscript(cleaned, isFinal: true)
                } else {
                    self.handleEmptyLocalCapture()
                }
            case .failure(let error):
                self.awaitingCommand = false
                self.lastAction = "whisper failed: \(error.localizedDescription)"
                self.statusMessage = "transcription failed"
                self.healSession(force: true)
            }
        }
    }

    private func handleEmptyLocalCapture() {
        if conversationMode {
            endConversationMode()
        } else {
            awaitingCommand = false
            statusMessage = sleepMode ? "sleeping" : "listening"
            lastAction = "no speech detected"
            healSession(force: true)
        }
    }

    private func clearTranscriptFeed() {
        liveTranscript = ""
        lastFinalTranscript = ""
        liveTranscriptIsPartial = false
        lastHeard = ""
    }

    func clearTranscriptOnMain() {
        DispatchQueue.main.async { [weak self] in
            self?.clearTranscriptFeed()
        }
    }

    private func enterConversationMode() {
        conversationMode = true
        clearTranscriptFeed()
        if sessionId.isEmpty {
            sessionId = UUID().uuidString.lowercased()
        }
        statusMessage = "conversation"
        refreshConversationTimer()
    }

    private func endConversationMode() {
        conversationMode = false
        sessionId = ""
        awaitingCommand = false
        conversationTimer?.cancel()
        clearTranscriptFeed()
        statusMessage = sleepMode ? "sleeping" : "listening"
        Sound.notListening()
        lastAction = "conversation ended"
        resetJunkTracking()
        if usesLocalBackend {
            healSession(force: true)
        }
    }

    private func refreshConversationTimer() {
        conversationTimer?.cancel()
        let work = DispatchWorkItem { [weak self] in
            self?.endConversationMode()
        }
        conversationTimer = work
        DispatchQueue.main.asyncAfter(deadline: .now() + conversationTimeout, execute: work)
    }

    private func finishBusyAndListen() {
        cancelCommandTimeout()
        busy = false
        isBusy = false
        lastAction = "answered"
        if conversationMode {
            refreshConversationTimer()
        }
        if usesLocalBackend && conversationMode && !sleepMode {
            Sound.listening()
            beginLocalCommandCapture(reason: "follow up")
        } else {
            healSession()
        }
    }

    private func finishDeferred() {
        cancelCommandTimeout()
        busy = false
        isBusy = false
        lastAction = "deferred"
        if conversationMode {
            refreshConversationTimer()
        }
        if usesLocalBackend && conversationMode && !sleepMode {
            Sound.listening()
            beginLocalCommandCapture(reason: "follow up")
        } else {
            healSession()
        }
    }

    private func matchesPhrase(_ text: String, phrases: [String]) -> Bool {
        phrases.contains { text.contains($0) }
    }

    private func schedulePartialFinalize(_ text: String) {
        partialFinalizeText = text
        partialFinalizeTimer?.cancel()
        let work = DispatchWorkItem { [weak self] in
            guard let self else { return }
            guard self.partialFinalizeText == text, !self.busy else { return }
            self.partialFinalizeTimer = nil
            self.processTranscript(text, isFinal: true)
        }
        partialFinalizeTimer = work
        DispatchQueue.main.asyncAfter(deadline: .now() + partialFinalizeDelay, execute: work)
    }

    private func cancelPartialFinalize() {
        partialFinalizeTimer?.cancel()
        partialFinalizeTimer = nil
        partialFinalizeText = ""
    }

    private func shouldAcceptCommand(_ text: String) -> Bool {
        let command = extractCommand(from: text).trimmingCharacters(in: .whitespacesAndNewlines)
        guard command.count >= 2, command.count <= maxCommandLength else { return false }
        if matchesPhrase(command, phrases: wakePhrases) { return false }
        return looksLikeIntentionalCommand(command)
    }

    private func looksLikeIntentionalCommand(_ command: String) -> Bool {
        let words = command.split(separator: " ")
        if words.count <= 1 {
            return commandHints.contains { command.contains($0) }
        }
        if words.count <= 14 { return true }
        return commandHints.contains { command.contains($0) }
    }

    private func fuzzyNearWake(_ text: String) -> Bool {
        let t = text.lowercased()
        let hasGreeting = t.contains("hey") || t.contains("hay") || t.contains("yo ")
            || t.hasPrefix("yo ") || t.contains("ok ")
        guard hasGreeting else { return false }
        let hints = ["will", "willy", "willie", "bill", "billy", "woody", "wil", "william"]
        return hints.contains { t.contains($0) }
    }

    private func shouldTrackPartial(_ text: String) -> Bool {
        conversationMode || awaitingCommand || matchesWakePhrase(text) || fuzzyNearWake(text)
    }

    private func refreshAwaitingDeadline() {
        guard awaitingCommand, !busy else { return }
        commandDeadline?.cancel()
        let work = DispatchWorkItem { [weak self] in
            guard let self, self.awaitingCommand, !self.busy else { return }
            self.awaitingCommand = false
            self.lastAction = "command timeout"
            self.noteJunkSpeech("awaiting timeout")
        }
        commandDeadline = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 14, execute: work)
    }

    private func handleTranscript(_ raw: String, isFinal: Bool) {
        let text = raw.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        lastTranscriptAt = Date()
        lastHealthyAt = Date()

        let wakeRelated = matchesWakePhrase(text) || fuzzyNearWake(text)
        let showInUI = conversationMode || awaitingCommand || wakeRelated
            || (shouldTrackPartial(text) && !sleepMode)
        if showInUI {
            lastHeard = text
            liveTranscript = text
            liveTranscriptIsPartial = !isFinal
        } else if isFinal {
            liveTranscriptIsPartial = false
        }

        if Voice.isSpeaking, text.count >= 4, !matchesPhrase(text, phrases: wakePhrases) {
            lastAction = "barge-in"
            Voice.stop()
            pausedForSpeech = false
            busy = false
            isBusy = false
            healSession(force: true)
        }

        if isFinal {
            lastFinalTranscript = text
            cancelPartialFinalize()
            processTranscript(text, isFinal: true)
            return
        }

        if awaitingCommand {
            refreshAwaitingDeadline()
        }

        if !busy, !Voice.isSpeaking, shouldTrackPartial(text) {
            schedulePartialFinalize(text)
        }
    }

    private func processTranscript(_ text: String, isFinal: Bool) {
        guard isFinal else { return }
        lastFinalTranscript = text
        liveTranscriptIsPartial = false

        if busy {
            if matchesPhrase(text, phrases: cancelPhrases) {
                lastAction = "cancel while busy"
                Voice.stop()
                Voice.speak("Stopping, boss.") { [weak self] in
                    self?.finishBusyAndListen()
                }
            }
            return
        }

        if conversationMode {
            refreshConversationTimer()
            let command = extractCommand(from: text)
            guard shouldAcceptCommand(text) else {
                noteJunkSpeech("ignored background speech")
                return
            }
            resetJunkTracking()
            if matchesPhrase(command, phrases: exitPhrases) {
                endConversationMode()
                Voice.speak("Right then, boss.") { [weak self] in
                    self?.finishBusyAndListen()
                }
                return
            }
            scheduleCommand(command)
            return
        }

        if awaitingCommand {
            let command = extractCommand(from: text)
            guard shouldAcceptCommand(text) else {
                noteJunkSpeech("ignored partial")
                return
            }
            resetJunkTracking()
            scheduleCommand(command)
            return
        }

        guard matchesWakePhrase(text) || fuzzyNearWake(text),
              Date().timeIntervalSince(lastWakeAt) > cooldown else {
            if conversationMode || awaitingCommand {
                noteJunkSpeech("unrecognized speech")
            }
            return
        }
        resetJunkTracking()
        lastWakeAt = Date()
        enterConversationMode()

        let inline = extractCommand(from: text)
        if inline.count >= 3 {
            lastAction = "wake + command"
            Sound.listening()
            scheduleCommand(inline)
            return
        }

        lastAction = "wake detected"
        awaitingCommand = true
        pendingCommand = ""
        Sound.listening()
        refreshAwaitingDeadline()
    }

    private func cancelCommandTimeout() {
        commandTimeoutTimer?.cancel()
        commandTimeoutTimer = nil
    }

    private func armCommandTimeout() {
        cancelCommandTimeout()
        let work = DispatchWorkItem { [weak self] in
            guard let self, self.busy else { return }
            self.lastAction = "command timeout"
            self.busy = false
            self.isBusy = false
            Voice.stop()
            self.healSession(force: true)
        }
        commandTimeoutTimer = work
        DispatchQueue.main.asyncAfter(deadline: .now() + commandTimeout, execute: work)
    }

    private var lastScheduledCommand = ""
    private var lastScheduledAt = Date.distantPast

    private func scheduleCommand(_ text: String) {
        let command = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard command.count >= 2 else { return }
        if command == lastScheduledCommand, Date().timeIntervalSince(lastScheduledAt) < 3 {
            return
        }
        lastScheduledCommand = command
        lastScheduledAt = Date()
        cancelPartialFinalize()
        pendingCommand = command
        commandTimer?.cancel()
        let work = DispatchWorkItem { [weak self] in
            guard let self, !self.busy else { return }
            self.runCommand(self.pendingCommand)
        }
        commandTimer = work
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2, execute: work)
    }

    private func pauseListeningForSpeech() {
        pausedForSpeech = true
        if usesLocalBackend {
            stopLocalWakeMonitoring()
            localRecorder.cancel()
            audioRunning = false
            return
        }
        recognitionTask?.cancel()
        stopAudioCapture()
    }

    private func resumeAfterSpeech(_ completion: @escaping () -> Void) {
        pausedForSpeech = false
        healSession(force: true)
        completion()
    }

    private func waitForUserSilence(then completion: @escaping () -> Void) {
        silenceWaitStartedAt = Date()
        func check() {
            let silentFor = Date().timeIntervalSince(lastTranscriptAt)
            let waited = Date().timeIntervalSince(silenceWaitStartedAt)
            if silentFor >= silenceBeforeSpeak || waited >= maxSilenceWait {
                silenceWaitStartedAt = .distantPast
                completion()
                return
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.12) { check() }
        }
        check()
    }

    private func deliverReply(_ reply: String, deferred: Bool?, endSession: Bool?) {
        waitForUserSilence { [weak self] in
            guard let self else { return }
            self.pauseListeningForSpeech()
            Voice.speak(reply) { [weak self] in
                guard let self else { return }
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) {
                    self.resumeAfterSpeech {
                        if endSession == true {
                            self.endConversationMode()
                        }
                        if deferred == true {
                            self.finishDeferred()
                        } else {
                            self.finishBusyAndListen()
                        }
                    }
                }
            }
        }
    }

    private func runCommand(_ text: String) {
        let command = extractCommand(from: text).trimmingCharacters(in: .whitespacesAndNewlines)
        guard command.count >= 2, !busy else { return }

        let now = Date()
        if command == lastCommandSent, now.timeIntervalSince(lastCommandAt) < commandCooldown {
            return
        }
        lastCommandSent = command
        lastCommandAt = now

        let lower = command.lowercased()
        if matchesPhrase(lower, phrases: enrollPhrases) {
            handleVoiceEnrollment()
            return
        }

        if SpeakerVerifier.shared.isEnrolling {
            let done = SpeakerVerifier.shared.finishEnrollment()
            let msg = done
                ? "Got it, boss. I'll recognize your voice from now on."
                : "Keep talking a bit longer, boss. Say enroll my voice again when you're ready."
            busy = true
            isBusy = true
            Voice.speak(msg) { [weak self] in
                self?.finishBusyAndListen()
            }
            return
        }

        if SpeakerVerifier.shared.isEnrolled, !SpeakerVerifier.shared.isGuidedEnrollment, !guidedEnrollmentActive {
            let check = SpeakerVerifier.shared.verifyRecent()
            if !check.verified {
                busy = true
                isBusy = true
                lastAction = "voice rejected (confidence \(String(format: "%.2f", check.confidence)))"
                Voice.speak("Sorry boss, I don't recognize your voice.") { [weak self] in
                    self?.finishBusyAndListen()
                }
                return
            }
        }

        awaitingCommand = false
        busy = true
        isBusy = true
        commandTimer?.cancel()
        commandDeadline?.cancel()
        lastAction = "command: \(command)"
        Sound.notListening()
        Sound.responding()
        recognitionTask?.cancel()
        armCommandTimeout()

        queryJarvis(command) { [weak self] reply, deferred, endSession in
            guard let self else { return }
            DispatchQueue.main.async {
                self.deliverReply(reply, deferred: deferred, endSession: endSession)
            }
        }
    }

    private func extractCommand(from text: String) -> String {
        let lower = text.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        guard !lower.isEmpty else { return "" }

        var start = lower.startIndex
        for phrase in wakePhrases {
            var search = lower.startIndex..<lower.endIndex
            while let range = lower.range(of: phrase, options: [], range: search) {
                if range.upperBound > start {
                    start = range.upperBound
                }
                search = range.upperBound..<lower.endIndex
            }
        }

        let verbs = [
            "play", "open", "pause", "stop", "skip", "next", "previous",
            "weather", "what", "who", "how", "remember", "close", "switch",
            "focus", "launch", "tell", "check", "recall", "minimize", "minimise",
        ]
        for verb in verbs {
            if let range = lower.range(of: "\\b\(verb)\\b", options: .regularExpression) {
                if lower.distance(from: lower.startIndex, to: range.lowerBound) <= 80,
                   range.lowerBound < start || lower.distance(from: start, to: range.lowerBound) < 12 {
                    start = range.lowerBound
                    break
                }
            }
        }

        var command = String(lower[start...]).trimmingCharacters(in: .whitespacesAndNewlines)
        command = stripWakePhrases(command)

        let noiseMarkers = [
            "summary of the conversation", "the user was", "preparing to leave",
            "costco", "hello like",
        ]
        for marker in noiseMarkers {
            if let range = command.range(of: marker) {
                command = String(command[..<range.lowerBound]).trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }

        if command.count > 120 {
            command = String(command.prefix(120))
            if let lastSpace = command.lastIndex(of: " ") {
                command = String(command[..<lastSpace])
            }
        }
        return command.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func stripWakePhrases(_ text: String) -> String {
        var result = text
        for phrase in wakePhrases {
            result = result.replacingOccurrences(of: phrase, with: "")
        }
        return result.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func matchesWakePhrase(_ text: String) -> Bool {
        wakePhrases.contains { text.contains($0) } || fuzzyNearWake(text)
    }

    func startVoiceEnrollment() {
        DispatchQueue.main.async { self.startGuidedVoiceEnrollment() }
    }

    func startGuidedVoiceEnrollment() {
        guard !busy, !guidedEnrollmentActive else { return }
        busy = true
        isBusy = true
        guidedEnrollmentActive = true
        guidedPhraseRetries = 0
        stopLocalWakeMonitoring()
        SpeakerVerifier.shared.startGuidedEnrollment()
        lastAction = "guided voice enrollment started"
        statusMessage = "voice training"
        promptGuidedPhrase(isFirst: true)
    }

    func cancelGuidedVoiceEnrollment() {
        guidedEnrollmentActive = false
        guidedPhraseRetries = 0
        SpeakerVerifier.shared.cancelEnrollment()
        statusMessage = sleepMode ? "sleeping" : "listening"
        lastAction = "voice enrollment cancelled"
        finishBusyAndListen()
    }

    private func promptGuidedPhrase(isFirst: Bool = false, retry: Bool = false) {
        guard guidedEnrollmentActive,
              let phrase = SpeakerVerifier.shared.currentGuidedPhrase() else {
            completeGuidedEnrollment()
            return
        }
        let index = SpeakerVerifier.shared.guidedPhraseCount > 0
            ? min(SpeakerVerifier.shared.status()["guided_phrase_index"] as? Int ?? 0, SpeakerVerifier.shared.guidedPhraseCount - 1) + 1
            : 1
        let total = SpeakerVerifier.shared.guidedPhraseCount
        let intro = isFirst
            ? "Right boss. I'll learn your voice. Repeat each phrase after me. "
            : ""
        let retryMsg = retry ? "Let's try that once more. " : ""
        let spoken = "\(intro)\(retryMsg)Phrase \(index) of \(total). \(phrase)."
        Voice.speak(spoken) { [weak self] in
            self?.recordGuidedPhrase()
        }
    }

    private func recordGuidedPhrase() {
        guard guidedEnrollmentActive else { return }
        statusMessage = "voice training — listening"
        do {
            try localRecorder.start(
                maxDuration: 5.0,
                silenceCutoff: 1.2,
                silenceThreshold: voiceConfig.silenceThreshold
            ) { [weak self] result in
                guard let self else { return }
                if case .success(let url) = result {
                    try? FileManager.default.removeItem(at: url)
                }
                self.handleGuidedPhraseRecorded()
            }
        } catch {
            lastAction = "enrollment record failed: \(error.localizedDescription)"
            Voice.speak("Sorry boss, the microphone glitched. Let's try that phrase again.") { [weak self] in
                self?.promptGuidedPhrase(retry: true)
            }
        }
    }

    private func handleGuidedPhraseRecorded() {
        let gained = SpeakerVerifier.shared.samplesSincePhraseStart()
        if gained >= 2 {
            guidedPhraseRetries = 0
            let result = SpeakerVerifier.shared.completeGuidedPhrase()
            if result.done {
                completeGuidedEnrollment()
            } else {
                promptGuidedPhrase()
            }
            return
        }

        if guidedPhraseRetries < 1 {
            guidedPhraseRetries += 1
            promptGuidedPhrase(retry: true)
            return
        }

        guidedPhraseRetries = 0
        let result = SpeakerVerifier.shared.completeGuidedPhrase()
        if result.done {
            completeGuidedEnrollment(force: true)
        } else {
            promptGuidedPhrase()
        }
    }

    private func completeGuidedEnrollment(force: Bool = false) {
        guidedEnrollmentActive = false
        let ok = SpeakerVerifier.shared.finishEnrollment()
        let wake = self.wakePhraseDisplay
        let msg: String
        if ok {
            msg = "Perfect boss. I've learned your voice. Say \(wake) to wake me, then give me a command."
        } else if force {
            msg = "I got some of your voice, boss, but not enough. Say teach my voice to try again."
        } else {
            msg = "I got some of your voice, boss, but not enough. Say teach my voice to try again."
        }
        lastAction = ok ? "guided voice enrollment complete" : "guided voice enrollment incomplete"
        statusMessage = sleepMode ? "sleeping" : "listening"
        Voice.speak(msg) { [weak self] in
            self?.finishBusyAndListen()
        }
    }

    private func handleVoiceEnrollment() {
        startGuidedVoiceEnrollment()
    }

    private func queryJarvis(
        _ message: String,
        completion: @escaping (String, Bool?, Bool?) -> Void
    ) {
        var body: [String: Any] = ["message": message, "source": "voice"]
        if !sessionId.isEmpty {
            body["session_id"] = sessionId
        }
        if SpeakerVerifier.shared.isEnrolled {
            let check = SpeakerVerifier.shared.verifyRecent()
            body["speaker_verified"] = check.verified
            body["speaker_confidence"] = check.confidence
        }

        var request = URLRequest(url: jarvisURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 30
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        URLSession.shared.dataTask(with: request) { [weak self] data, _, error in
            let fallback = "Sorry boss, I'm having trouble right now."
            if let error {
                DispatchQueue.main.async {
                    self?.lastAction = "jarvis error: \(error.localizedDescription)"
                    completion(fallback, false, false)
                }
                return
            }
            guard let data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let reply = json["reply"] as? String,
                  !reply.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                DispatchQueue.main.async { completion(fallback, false, false) }
                return
            }
            if let sid = json["session_id"] as? String, !sid.isEmpty {
                DispatchQueue.main.async { self?.sessionId = sid }
            }
            let isNew = json["is_new_session"] as? Bool ?? false
            let deferred = json["deferred"] as? Bool
            let endSession = json["end_session"] as? Bool
            DispatchQueue.main.async {
                if isNew {
                    self?.clearTranscriptFeed()
                }
                completion(reply, deferred, endSession)
            }
        }.resume()
    }
}
