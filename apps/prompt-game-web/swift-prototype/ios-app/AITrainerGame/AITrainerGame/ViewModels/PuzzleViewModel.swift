import Foundation

@MainActor
final class LessonViewModel: ObservableObject {
    @Published private(set) var lesson: Lesson
    @Published private(set) var messages: [Message] = []
    @Published var inputText: String = ""
    @Published private(set) var turnsRemaining: Int
    @Published private(set) var phase: GamePhase
    @Published private(set) var result: LessonResult?
    @Published var isLoading = false
    @Published var showResultSheet = false
    @Published var toastMessage: String?
    @Published private(set) var feedbackRecords: [FeedbackRecord] = []
    @Published private(set) var ruleText: String?
    @Published private(set) var clueProgress: [ClueProgress] = []

    var turnsUsed: Int {
        lesson.maxTurns - turnsRemaining
    }

    var validationMessage: String? {
        validationState.message
    }

    var canSendMessage: Bool {
        !isLoading && !phase.isCompleted && turnsRemaining > 0 && validationState.isValid
    }

    var turnCounterLabel: String {
        switch phase {
        case .completedFail, .completedSuccess:
            return "Lesson ended"
        default:
            let plural = turnsRemaining == 1 ? "question" : "questions"
            return "\(turnsRemaining) \(plural) remaining"
        }
    }

    private var validationState: MessageValidationState {
        engine.validationState(for: inputText)
    }

    private let llmService: LLMServiceProtocol
    private let engine: LessonEngine
    private let feedbackEngine = FeedbackEngine()
    private var deterministicRunner: DeterministicLessonRunner?

    init(lesson: Lesson, llmService: LLMServiceProtocol = LLMService()) {
        self.lesson = lesson
        self.llmService = llmService
        let engine = LessonEngine(lesson: lesson)
        self.engine = engine
        self.turnsRemaining = engine.turnsRemaining
        self.phase = engine.phase
        configureDeterministicRunner()
    }

    func sendMessage() async {
        let trimmed = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        let validation = engine.validationState(for: trimmed)
        guard validation.isValid else {
            if let message = validation.message {
                toastMessage = message
            }
            return
        }
        guard canSendMessage else { return }

        engine.captureUserInput(trimmed)
        let userMessage = Message(role: .user, content: trimmed)
        messages.append(userMessage)
        inputText = ""

        if deterministicRunner != nil {
            handleDeterministicMessage(for: trimmed)
        } else {
            await fetchAssistantReply(for: trimmed)
        }
    }

    func restart() {
        engine.reset()
        configureDeterministicRunner()
        messages = []
        result = nil
        toastMessage = nil
        showResultSheet = false
        syncStateFromEngine()
    }

    func updateLesson(_ lesson: Lesson) {
        self.lesson = lesson
        engine.updateLesson(lesson)
        configureDeterministicRunner()
        messages = []
        result = nil
        showResultSheet = false
        toastMessage = nil
        syncStateFromEngine()
    }

    private func fetchAssistantReply(for latestInput: String) async {
        isLoading = true
        defer { isLoading = false }
        do {
            let response = try await llmService.sendMessage(lesson: lesson, history: messages)
            let feedback = feedbackEngine.feedback(for: latestInput, lesson: lesson, turnIndex: engine.nextTurnIndex)
            let assistantMessage = Message(role: .assistant, content: response.content, feedback: feedback, phase: response.phase)
            messages.append(assistantMessage)
            advanceTurn(with: feedback, phaseOverride: response.phase)
        } catch {
            let errorMessage = Message(role: .assistant, content: "⚠️ \(error.localizedDescription)")
            messages.append(errorMessage)
            toastMessage = "Unable to reach the AI service."
            advanceTurn(with: nil, phaseOverride: nil)
        }
    }

    private func advanceTurn(with feedback: Feedback?, phaseOverride: GamePhase?) {
        let updatedPhase = engine.registerTurn(feedback: feedback, phaseOverride: phaseOverride)
        syncStateFromEngine()
        if updatedPhase.isCompleted {
            finalizeResult(for: updatedPhase)
        }
    }

    private func finalizeResult(for phase: GamePhase) {
        guard result == nil else { return }
        let outcome: LessonResult.Outcome = phase == .completedSuccess ? .success : .retry
        let summary = deterministicRunner?.context(for: outcome)
        let highlight = summary?.highlight ?? (outcome == .success
                                              ? "You solved \(lesson.title) in \(max(turnsUsed, 1)) turns."
                                              : "The signal stayed hidden. Try one more focused question.")
        let reflection = summary?.reflection ?? (outcome == .success
                                                 ? "Great use of \(lesson.skill.lowercased())."
                                                 : "Hidden logic: \(lesson.solutionLogic).")
        let microLesson = summary?.microLesson ?? (outcome == .success
                                                   ? lesson.skillDescription
                                                   : "Next time, lead with \(lesson.skill.lowercased()).")

        let lessonResult = engine.makeResult(outcome: outcome, highlight: highlight, reflection: reflection, microLesson: microLesson)
        result = lessonResult
        feedbackRecords = lessonResult.feedbackRecords
        showResultSheet = true
    }

    private func syncStateFromEngine() {
        turnsRemaining = engine.turnsRemaining
        phase = engine.phase
        feedbackRecords = engine.feedbackRecords
        updateClueProgress()
    }

    private func handleDeterministicMessage(for trimmed: String) {
        guard let runner = deterministicRunner else { return }
        let output = runner.respond(to: trimmed, turnIndex: engine.nextTurnIndex)
        let assistantMessage = Message(role: .assistant, content: output.reply, feedback: output.feedback, phase: output.phaseOverride)
        messages.append(assistantMessage)
        updateClueProgress()
        advanceTurn(with: output.feedback, phaseOverride: output.phaseOverride)
    }

    private func configureDeterministicRunner() {
        if let script = lesson.tutorialScript {
            deterministicRunner = DeterministicLessonRunner(script: script)
            ruleText = script.rule
        } else {
            deterministicRunner = nil
            ruleText = nil
        }
        updateClueProgress()
    }

    private func updateClueProgress() {
        if let runner = deterministicRunner {
            clueProgress = runner.progress()
        } else {
            clueProgress = []
        }
    }
}

// MARK: - Lesson Engine

/// Validates user input before sending a message.
/// Checks for empty input, length limits, duplicate messages, and question count.
struct MessageValidationState {
    let isValid: Bool
    let message: String?
}

/// Core game engine managing lesson state, turn tracking, validation, and result generation.
/// Separates gameplay logic from UI concerns.
final class LessonEngine {
    private(set) var lesson: Lesson
    private(set) var phase: GamePhase = .intro
    private(set) var turnsRemaining: Int
    private(set) var feedbackRecords: [FeedbackRecord] = []

    private let maxInputLength = 240
    private var lastInputFingerprint: Int?

    init(lesson: Lesson) {
        self.lesson = lesson
        self.turnsRemaining = lesson.maxTurns
    }

    var nextTurnIndex: Int {
        lesson.maxTurns - turnsRemaining
    }

    func updateLesson(_ lesson: Lesson) {
        self.lesson = lesson
        reset()
    }

    func reset() {
        phase = .intro
        turnsRemaining = lesson.maxTurns
        feedbackRecords = []
        lastInputFingerprint = nil
    }

    func validationState(for text: String) -> MessageValidationState {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return MessageValidationState(isValid: false, message: nil) }

        if turnsRemaining == 0 {
            return MessageValidationState(isValid: false, message: "You're out of messages — try again!")
        }

        if trimmed.count > maxInputLength {
            return MessageValidationState(isValid: false, message: "Keep it under \(maxInputLength) characters.")
        }

        let questionCount = trimmed.filter { $0 == "?" }.count
        if questionCount > 1 {
            return MessageValidationState(isValid: false, message: "One question per message. Pick the most important one.")
        }

        let fingerprint = trimmed.lowercased().hashValue
        if let last = lastInputFingerprint, last == fingerprint {
            return MessageValidationState(isValid: false, message: "You've already asked that. Try a new angle.")
        }

        return MessageValidationState(isValid: true, message: nil)
    }

    func captureUserInput(_ text: String) {
        lastInputFingerprint = text.lowercased().hashValue
        if phase == .intro {
            phase = .active
        }
    }

    func registerTurn(feedback: Feedback?, phaseOverride: GamePhase?) -> GamePhase {
        if let feedback {
            let record = FeedbackRecord(turnIndex: nextTurnIndex, feedback: feedback)
            feedbackRecords.append(record)
        }

        turnsRemaining = max(turnsRemaining - 1, 0)

        if let override = phaseOverride {
            phase = override
        } else if turnsRemaining == 0 {
            phase = .completedFail
        } else if phase == .intro {
            phase = .active
        }
        return phase
    }

    func makeResult(outcome: LessonResult.Outcome, highlight: String, reflection: String, microLesson: String) -> LessonResult {
        let efficiency = EfficiencyRating.make(
            outcome: outcome,
            averageScore: feedbackRecords.averageScore,
            turnsUsed: max(1, lesson.maxTurns - turnsRemaining),
            totalTurns: lesson.maxTurns
        )

        return LessonResult(
            lesson: lesson,
            outcome: outcome,
            turnsUsed: max(1, lesson.maxTurns - turnsRemaining),
            totalTurns: lesson.maxTurns,
            feedbackRecords: feedbackRecords,
            highlight: highlight,
            reflection: reflection,
            microLesson: microLesson,
            efficiency: efficiency
        )
    }
}

private extension EfficiencyRating {
    static func make(outcome: LessonResult.Outcome, averageScore: Double, turnsUsed: Int, totalTurns: Int) -> EfficiencyRating {
        let turnEfficiency = 1 - (Double(turnsUsed) / Double(max(totalTurns, 1)))
        let composite = max(0, min(1, (averageScore * 0.65) + (turnEfficiency * 0.35)))

        if outcome == .retry {
            return EfficiencyRating(
                stars: 1,
                label: "Keep Exploring",
                detail: "Recenter on the skill focus and try again.",
                progress: max(0.2, composite * 0.5)
            )
        }

        if composite >= 0.8 {
            return EfficiencyRating(
                stars: 3,
                label: "Laser Focused",
                detail: "You solved it with crisp, constraint-driven questions.",
                progress: composite
            )
        } else if composite >= 0.55 {
            return EfficiencyRating(
                stars: 2,
                label: "Dialed In",
                detail: "Nice flow. Tighten one more detail for bonus stars.",
                progress: composite
            )
        } else {
            return EfficiencyRating(
                stars: 1,
                label: "Keep Exploring",
                detail: "You found the answer—now push for sharper constraints.",
                progress: composite
            )
        }
    }
}

// MARK: - Feedback Engine

/// Generates heuristic-based feedback for user questions.
/// Analyzes input for clarity, specificity, constraint usage, and alignment with lesson skill.
struct FeedbackEngine {
    private let broadWords: [String] = [
        "everything", "anything", "else", "other", "all", "more info", "anything else"
    ]

    private let constraintWords: [String] = [
        "color", "size", "shape", "material", "exact", "specific", "type", "pattern", "range",
        "limit", "where", "when", "who", "which", "compare", "difference", "category", "clue",
        "detail", "constraint", "narrow", "filter"
    ]

    private let offTrackWords: [String] = [
        "manager", "project", "email", "task", "deadline", "sprint", "ticket", "work"
    ]

    private let guessWords: [String] = [
        "is it", "it's", "i think it's", "the answer is", "is the answer", "i guess"
    ]

    func feedback(for text: String, lesson: Lesson, turnIndex: Int) -> Feedback {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let lower = trimmed.lowercased()
        let words = lower.split(separator: " ")
        let wordCount = words.count

        let containsBroad = broadWords.contains(where: { lower.contains($0) })
        let containsConstraint = constraintWords.filter { lower.contains($0) }.count
        let containsGuess = guessWords.contains(where: { lower.contains($0) })
        let containsOffTrack = offTrackWords.contains(where: { lower.contains($0) })
        let questionCount = lower.filter { $0 == "?" }.count
        let containsAnd = lower.contains(" and ") || lower.contains(",")

        let type: FeedbackType
        if containsOffTrack {
            type = .offTrack
        } else if containsGuess {
            type = .guessing
        } else if wordCount < 4 || questionCount == 0 {
            type = .vague
        } else if containsBroad || containsAnd {
            type = .broad
        } else if containsConstraint >= 2 || lower.contains("exact") {
            type = .excellent
        } else if containsConstraint == 1 {
            type = .good
        } else if questionCount > 1 {
            type = .partial
        } else {
            type = .partial
        }

        let message: String
        switch type {
        case .excellent:
            message = "Great clarity."
        case .good:
            message = "Nice focus."
        case .partial:
            message = "Add one detail."
        case .vague:
            message = "Too fuzzy."
        case .broad:
            message = "Too broad — one detail only."
        case .offTrack:
            message = "Off track."
        case .guessing:
            message = "Try asking instead."
        }

        return Feedback(type: type, message: message)
    }
}
