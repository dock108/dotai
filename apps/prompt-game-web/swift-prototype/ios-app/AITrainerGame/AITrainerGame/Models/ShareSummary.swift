import Foundation

struct ShareSummary: Equatable {
    let lessonNumber: Int
    let solved: Bool
    let turnsUsed: Int
    let turnLimit: Int
    let skillName: String
    let feedbackRecords: [FeedbackRecord]

    var titleLine: String {
        let status = solved ? "Completed" : "Tried"
        return "Lesson \(lessonNumber) — \(status) in \(turnsUsed)/\(turnLimit) turns"
    }

    var detailLine: String {
        "Skill: \(skillName)"
    }

    var feedbackLine: String {
        let sequence = feedbackRecords
            .sorted { $0.turnIndex < $1.turnIndex }
            .map { $0.feedback.type.symbol }
            .joined()
        let remainingCount = max(turnLimit - feedbackRecords.count, 0)
        let padding = String(repeating: "⚪️", count: remainingCount)
        return sequence + padding
    }

    var skillLine: String {
        "Skill trained: \(skillName)"
    }

    var shareText: String {
        [titleLine, feedbackLine, skillLine, "Can you beat my score?"].joined(separator: "\n")
    }

    var progress: Double {
        guard turnLimit > 0 else { return 0 }
        return Double(min(feedbackRecords.count, turnLimit)) / Double(turnLimit)
    }
}
