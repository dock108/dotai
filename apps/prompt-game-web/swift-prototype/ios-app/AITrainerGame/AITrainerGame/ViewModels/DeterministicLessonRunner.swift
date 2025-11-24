import Foundation

struct ClueProgress: Identifiable, Equatable {
    let id: String
    let title: String
    let isUnlocked: Bool
}

struct DeterministicResultContext {
    let highlight: String
    let reflection: String
    let microLesson: String
}

struct DeterministicRunnerOutput {
    let reply: String
    let feedback: Feedback
    let phaseOverride: GamePhase?
}

final class DeterministicLessonRunner {
    private let script: DeterministicScript
    private var unlockedClueIDs: Set<String> = []
    private var hasGrantedAutoClue = false

    init(script: DeterministicScript) {
        self.script = script
    }

    func respond(to userInput: String, turnIndex: Int) -> DeterministicRunnerOutput {
        let lower = userInput.lowercased()

        if matchesAnswer(lower: lower) {
            return DeterministicRunnerOutput(
                reply: script.completionMessage,
                feedback: Feedback(type: .excellent, message: "Perfect clarity — you solved it!"),
                phaseOverride: .completedSuccess
            )
        }

        if script.firstTurnAlwaysSucceeds && isFirstTurn(turnIndex: turnIndex) && !hasGrantedAutoClue {
            hasGrantedAutoClue = true
            return unlock(clue: script.clues.first)
        }

        let matched = matchingClues(for: lower)
        if matched.count > 1 {
            return DeterministicRunnerOutput(
                reply: script.fallback.broad,
                feedback: Feedback(type: .broad, message: "Too broad — ask about one attribute."),
                phaseOverride: nil
            )
        }

        guard let clue = matched.first else {
            let fallbackMessage = lower.count < 4 ? script.fallback.vague : script.fallback.mismatch
            return DeterministicRunnerOutput(
                reply: fallbackMessage,
                feedback: Feedback(type: .vague, message: "Try naming the exact attribute you want."),
                phaseOverride: nil
            )
        }

        if unlockedClueIDs.contains(clue.id) {
            return DeterministicRunnerOutput(
                reply: script.fallback.duplicate,
                feedback: Feedback(type: .partial, message: "Already shared. Pick another attribute."),
                phaseOverride: nil
            )
        }

        return unlock(clue: clue)
    }

    func progress() -> [ClueProgress] {
        script.clues.map {
            ClueProgress(id: $0.id, title: $0.title, isUnlocked: unlockedClueIDs.contains($0.id))
        }
    }

    func context(for outcome: LessonResult.Outcome) -> DeterministicResultContext {
        switch outcome {
        case .success:
            return DeterministicResultContext(
                highlight: script.successHighlight,
                reflection: script.successReflection,
                microLesson: script.microLessonSuccess
            )
        case .retry:
            return DeterministicResultContext(
                highlight: script.failureHighlight,
                reflection: script.failureReflection,
                microLesson: script.microLessonFailure
            )
        }
    }

    private func matchesAnswer(lower: String) -> Bool {
        let sanitized = lower.replacingOccurrences(of: ".", with: "").trimmingCharacters(in: .whitespacesAndNewlines)
        return sanitized == script.answer.lowercased()
    }

    private func isFirstTurn(turnIndex: Int) -> Bool {
        return turnIndex == 0
    }

    private func matchingClues(for lower: String) -> [DeterministicScript.Clue] {
        script.clues.filter { clue in
            clue.keywords.contains { keyword in
                lower.contains(keyword)
            }
        }
    }

    private func unlock(clue: DeterministicScript.Clue?) -> DeterministicRunnerOutput {
        guard let clue else {
            return DeterministicRunnerOutput(
                reply: script.fallback.mismatch,
                feedback: Feedback(type: .vague, message: "Try focusing on a single detail."),
                phaseOverride: nil
            )
        }
        unlockedClueIDs.insert(clue.id)
        let reply = "\(clue.response)"
        let feedbackType: FeedbackType = clue.reward == .core ? .excellent : .good
        let feedback = Feedback(type: feedbackType, message: clue.celebrate)

        return DeterministicRunnerOutput(
            reply: reply,
            feedback: feedback,
            phaseOverride: nil
        )
    }
}

