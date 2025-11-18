import Foundation
import SwiftUI

/// Core lesson data model representing a single puzzle/lesson in the game.
/// Contains all metadata needed to run a lesson: scenario, goal, rules, clues, and feedback configuration.
/// 
/// Lesson Structure:
/// - Each lesson defines a set of attributes (e.g., weather, temperature, storm chance)
/// - Valid questions target exactly ONE attribute at a time
/// - Each attribute maps to a clue that unlocks when the attribute is asked about
/// - The solution is determined by combining clues from multiple attributes
struct Lesson: Identifiable, Codable, Equatable, Hashable {
    let id: Int
    let number: Int
    let module: LessonModule
    let title: String
    let skill: String
    let skillDescription: String
    let goal: String
    let scenario: String
    let answerFormat: String
    let maxTurns: Int
    let exampleQuestions: [String] // Suggested question chips
    let solutionLogic: String
    let systemPrompt: String
    let tutorialScript: DeterministicScript?
    let difficulty: LessonDifficulty?
    
    /// Attributes available in this lesson (extracted from tutorialScript clues)
    var attributes: [String] {
        tutorialScript?.clues.map { $0.title } ?? []
    }
    
    /// Chips for suggested questions (synonym for exampleQuestions)
    var chips: [String] {
        exampleQuestions
    }

    var displayName: String {
        "Lesson \(number) · \(title)"
    }
}

extension Lesson {
    var moduleAccentColor: Color { module.accentColor }
    var moduleIconName: String { module.iconName }
    var moduleSummary: String { module.description }
}

enum LessonModule: String, Codable, CaseIterable {
    case foundation
    case clarity
    case narrowing
    case constraints
    case prioritization
    
    var displayName: String {
        switch self {
        case .foundation: return "Foundation"
        case .clarity: return "Clarity"
        case .narrowing: return "Narrowing"
        case .constraints: return "Constraints"
        case .prioritization: return "Prioritization"
        }
    }
    
    var description: String {
        switch self {
        case .foundation:
            return "Baseline drills to understand how AI responds to clarity."
        case .clarity:
            return "Learn to isolate missing details and eliminate vagueness."
        case .narrowing:
            return "Shrink large search spaces with targeted yes/no questions."
        case .constraints:
            return "Apply one restriction at a time to filter to valid options."
        case .prioritization:
            return "Lead with the highest-leverage question for fast answers."
        }
    }
    
    var iconName: String {
        switch self {
        case .foundation: return "leaf.fill"
        case .clarity: return "sparkles.rectangle.stack"
        case .narrowing: return "line.3.horizontal.decrease.circle.fill"
        case .constraints: return "lock.shield.fill"
        case .prioritization: return "scope"
        }
    }
    
    var accentColor: Color {
        switch self {
        case .foundation: return Color(red: 0.36, green: 0.42, blue: 0.71)
        case .clarity: return Color(red: 0.04, green: 0.62, blue: 0.74)
        case .narrowing: return Color(red: 0.0, green: 0.54, blue: 0.48)
        case .constraints: return Color(red: 0.88, green: 0.58, blue: 0.0)
        case .prioritization: return Color(red: 0.74, green: 0.32, blue: 0.86)
        }
    }
}

/// Lesson difficulty tier for future level-based organization.
/// Currently stored in metadata but hidden from UI.
enum LessonDifficulty: String, Codable, Equatable, Hashable {
    case warmup
    case basic
    case intermediate
    case advanced
}

extension LessonDifficulty {
    var displayName: String {
        switch self {
        case .warmup: return "Warmup"
        case .basic: return "Basic"
        case .intermediate: return "Intermediate"
        case .advanced: return "Advanced"
        }
    }
}

/// Deterministic script for Level 0 tutorial lessons.
/// Provides hard-coded clue unlocking logic, feedback rules, and completion messages.
/// Ensures predictable, consistent behavior for onboarding lessons.
struct DeterministicScript: Codable, Equatable, Hashable {
    struct Clue: Codable, Equatable, Hashable, Identifiable {
        enum Reward: String, Codable, Equatable, Hashable {
            case core
            case supporting
        }

        let id: String
        let title: String
        let keywords: [String]
        let response: String
        let reward: Reward
        let celebrate: String
    }

    struct Fallback: Codable, Equatable, Hashable {
        let broad: String
        let vague: String
        let duplicate: String
        let mismatch: String
        let welcome: String
    }

    let rule: String
    let answer: String
    let clues: [Clue]
    let fallback: Fallback
    let firstTurnAlwaysSucceeds: Bool
    let successHighlight: String
    let failureHighlight: String
    let successReflection: String
    let failureReflection: String
    let microLessonSuccess: String
    let microLessonFailure: String
    let completionMessage: String
}

struct FeedbackRecord: Identifiable, Equatable {
    let id = UUID()
    let turnIndex: Int
    let feedback: Feedback
}

struct EfficiencyRating: Equatable {
    let stars: Int
    let label: String
    let detail: String
    let progress: Double
}

struct LessonResult: Identifiable, Equatable {
    enum Outcome: String, Codable {
        case success
        case retry
    }

    let id = UUID()
    let lesson: Lesson
    let outcome: Outcome
    let turnsUsed: Int
    let totalTurns: Int
    let feedbackRecords: [FeedbackRecord]
    let highlight: String
    let reflection: String
    let microLesson: String
    let efficiency: EfficiencyRating

    var shareSummary: ShareSummary {
        ShareSummary(
            lessonNumber: lesson.number,
            solved: outcome == .success,
            turnsUsed: turnsUsed,
            turnLimit: totalTurns,
            skillName: lesson.skill,
            feedbackRecords: feedbackRecords
        )
    }
}

extension Array where Element == FeedbackRecord {
    var averageScore: Double {
        guard !isEmpty else { return 0 }
        let total = reduce(0.0) { $0 + $1.feedback.type.score }
        return total / Double(count)
    }
}
