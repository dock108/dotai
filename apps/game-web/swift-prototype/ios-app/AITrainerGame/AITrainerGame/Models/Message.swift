import Foundation

enum ChatRole: String, Codable {
    case system
    case user
    case assistant
}

enum GamePhase: String, Codable {
    case intro = "INTRO"
    case active = "ACTIVE"
    case completedSuccess = "COMPLETED_SUCCESS"
    case completedFail = "COMPLETED_FAIL"

    var isCompleted: Bool {
        switch self {
        case .intro, .active:
            return false
        case .completedSuccess, .completedFail:
            return true
        }
    }
}

enum FeedbackTone {
    case positive
    case neutral
    case caution
    case warning
}

enum FeedbackType: String, Codable, CaseIterable {
    case excellent
    case good
    case partial
    case vague
    case broad
    case offTrack
    case guessing

    var tone: FeedbackTone {
        switch self {
        case .excellent, .good:
            return .positive
        case .partial, .guessing:
            return .neutral
        case .vague:
            return .caution
        case .broad, .offTrack:
            return .warning
        }
    }

    var shortLabel: String {
        switch self {
        case .excellent: return "Great focus"
        case .good: return "Nice clarity"
        case .partial: return "Almost there"
        case .vague: return "Too fuzzy"
        case .broad: return "Too broad"
        case .offTrack: return "Off track"
        case .guessing: return "Guessing"
        }
    }

    var score: Double {
        switch self {
        case .excellent: return 1.0
        case .good: return 0.8
        case .partial: return 0.55
        case .guessing: return 0.45
        case .vague: return 0.35
        case .broad: return 0.25
        case .offTrack: return 0.15
        }
    }

    var symbol: String {
        switch self {
        case .excellent: return "🟢"
        case .good: return "🟢"
        case .partial: return "🟡"
        case .guessing: return "🟡"
        case .vague: return "🟠"
        case .broad: return "🟠"
        case .offTrack: return "🔴"
        }
    }
}

struct Feedback: Identifiable, Equatable {
    let id = UUID()
    let type: FeedbackType
    let message: String
}

struct Message: Identifiable, Equatable {
    let id = UUID()
    let role: ChatRole
    let content: String
    let feedback: Feedback?
    let phase: GamePhase?

    init(role: ChatRole, content: String, feedback: Feedback? = nil, phase: GamePhase? = nil) {
        self.role = role
        self.content = content
        self.feedback = feedback
        self.phase = phase
    }
}
