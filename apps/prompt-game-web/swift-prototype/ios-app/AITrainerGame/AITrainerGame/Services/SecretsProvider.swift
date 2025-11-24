import Foundation

struct SecretsProvider {
    private let bundle: Bundle
    private let environment: [String: String]

    init(bundle: Bundle = .main, environment: [String: String] = ProcessInfo.processInfo.environment) {
        self.bundle = bundle
        self.environment = environment
    }

    var apiKey: String {
        if let envKey = environment["OPENAI_API_KEY"], envKey.isEmpty == false {
            return envKey
        }
        if let fileKey = loadValue(for: "LLM_API_KEY") { return fileKey }
        return ""
    }

    var preferredModel: String? {
        loadValue(for: "LLM_MODEL")
    }

    private func loadValue(for key: String) -> String? {
        guard let url = bundle.url(forResource: "Secrets", withExtension: "plist"),
              let data = try? Data(contentsOf: url),
              let dictionary = try? PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any],
              let value = dictionary[key] as? String,
              value.isEmpty == false else {
            return nil
        }
        return value
    }
}
