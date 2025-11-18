import Foundation
import Combine

@MainActor
final class LessonStore: ObservableObject {
    @Published private(set) var lessons: [Lesson] = []
    @Published private(set) var loadingError: Error?

    private let repository: LessonRepositoryProtocol

    init(repository: LessonRepositoryProtocol = LessonRepository()) {
        self.repository = repository
        load()
    }

    func load() {
        do {
            lessons = try repository.loadLessons().sorted { $0.number < $1.number }
            loadingError = nil
        } catch {
            loadingError = error
            lessons = []
        }
    }

    func lesson(for number: Int) -> Lesson? {
        lessons.first { $0.number == number }
    }
}
