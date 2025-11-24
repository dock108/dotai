import Foundation

protocol LessonRepositoryProtocol {
    func loadLessons() throws -> [Lesson]
}

struct LessonRepository: LessonRepositoryProtocol {
    private let filename: String
    private let bundle: Bundle

    init(filename: String = "puzzles", bundle: Bundle = .main) {
        self.filename = filename
        self.bundle = bundle
    }

    func loadLessons() throws -> [Lesson] {
        guard let url = bundle.url(forResource: filename, withExtension: "json") else {
            throw LessonRepositoryError.fileMissing
        }
        do {
            let data = try Data(contentsOf: url)
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            return try decoder.decode([Lesson].self, from: data)
        } catch {
            throw LessonRepositoryError.corrupted
        }
    }
}

enum LessonRepositoryError: LocalizedError {
    case fileMissing
    case corrupted

    var errorDescription: String? {
        switch self {
        case .fileMissing:
            return "Unable to locate lessons data in the app bundle."
        case .corrupted:
            return "The lesson data is corrupted."
        }
    }
}
