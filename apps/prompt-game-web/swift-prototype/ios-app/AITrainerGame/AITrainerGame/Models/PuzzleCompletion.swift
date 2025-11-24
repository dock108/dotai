import Foundation

struct LessonCompletion: Codable {
    let lessonNumber: Int
    let completedAt: Date
    let outcome: LessonResult.Outcome
    let turnsUsed: Int
}

@MainActor
final class LessonCompletionTracker: ObservableObject {
    @Published private(set) var completedLessons: Set<Int> = []
    @Published private(set) var completions: [LessonCompletion] = []
    
    private let userDefaults: UserDefaults
    private let key = "lessonCompletions"
    
    init(userDefaults: UserDefaults = .standard) {
        self.userDefaults = userDefaults
        loadCompletions()
    }
    
    func markComplete(_ result: LessonResult) {
        let completion = LessonCompletion(
            lessonNumber: result.lesson.number,
            completedAt: Date(),
            outcome: result.outcome,
            turnsUsed: result.turnsUsed
        )
        completions.append(completion)
        completedLessons.insert(result.lesson.number)
        saveCompletions()
    }
    
    func isComplete(_ lessonNumber: Int) -> Bool {
        completedLessons.contains(lessonNumber)
    }
    
    var nextLessonNumber: Int? {
        let sorted = completions.sorted { $0.lessonNumber < $1.lessonNumber }
        guard let lastCompleted = sorted.last else {
            return 0
        }
        return lastCompleted.lessonNumber + 1
    }
    
    var mostRecentCompletion: LessonCompletion? {
        completions.max { $0.completedAt < $1.completedAt }
    }
    
    private func loadCompletions() {
        guard let data = userDefaults.data(forKey: key),
              let decoded = try? JSONDecoder().decode([LessonCompletion].self, from: data) else {
            return
        }
        completions = decoded
        completedLessons = Set(decoded.map { $0.lessonNumber })
    }
    
    private func saveCompletions() {
        guard let data = try? JSONEncoder().encode(completions) else { return }
        userDefaults.set(data, forKey: key)
    }
}

