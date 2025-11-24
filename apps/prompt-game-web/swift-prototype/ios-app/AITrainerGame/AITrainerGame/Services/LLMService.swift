import Foundation

struct LLMConfiguration {
    let apiKey: String
    let model: String
    let temperature: Double

    init(apiKey: String? = nil, model: String? = nil, temperature: Double = 0.5, secretsProvider: SecretsProvider = SecretsProvider()) {
        let providedKey = apiKey?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let resolvedKey = providedKey.isEmpty ? secretsProvider.apiKey : providedKey
        let resolvedModel = model ?? secretsProvider.preferredModel ?? "gpt-4o-mini"

        self.apiKey = resolvedKey
        self.model = resolvedModel
        self.temperature = temperature
    }
}

struct LLMResponse {
    let content: String
    let phase: GamePhase?
}

protocol LLMServiceProtocol {
    func sendMessage(lesson: Lesson, history: [Message]) async throws -> LLMResponse
}

final class LLMService: LLMServiceProtocol {
    private let configuration: LLMConfiguration
    private let urlSession: URLSession
    private let promptBuilder: SystemPromptBuilder

    init(configuration: LLMConfiguration = LLMConfiguration(), urlSession: URLSession = .shared, promptBuilder: SystemPromptBuilder = SystemPromptBuilder()) {
        self.configuration = configuration
        self.urlSession = urlSession
        self.promptBuilder = promptBuilder
    }

    func sendMessage(lesson: Lesson, history: [Message]) async throws -> LLMResponse {
        guard !configuration.apiKey.isEmpty else {
            throw LLMServiceError.missingAPIKey
        }

        let requestBody = ChatCompletionRequest(
            model: configuration.model,
            temperature: configuration.temperature,
            messages: promptBuilder.makePayload(for: lesson, history: history)
        )

        let request = try makeRequest(body: requestBody)
        let (data, response) = try await urlSession.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse, (200..<300).contains(httpResponse.statusCode) else {
            let serverMessage = String(data: data, encoding: .utf8) ?? ""
            throw LLMServiceError.server(serverMessage)
        }

        let decoded = try JSONDecoder().decode(ChatCompletionResponse.self, from: data)
        guard let message = decoded.choices.first?.message.content else {
            throw LLMServiceError.missingContent
        }

        return Parser.parse(content: message.trimmingCharacters(in: .whitespacesAndNewlines))
    }

    private func makeRequest(body: ChatCompletionRequest) throws -> URLRequest {
        let url = URL(string: "https://api.openai.com/v1/chat/completions")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("Bearer \(configuration.apiKey)", forHTTPHeaderField: "Authorization")
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(body)
        return request
    }
}

// MARK: - Request/Response DTOs

private struct ChatCompletionRequest: Encodable {
    let model: String
    let temperature: Double
    let messages: [ChatMessagePayload]
}

struct ChatMessagePayload: Encodable {
    let role: String
    let content: String
}

private struct ChatCompletionResponse: Decodable {
    struct Choice: Decodable {
        struct CompletionMessage: Decodable {
            let role: String
            let content: String
        }
        let index: Int
        let message: CompletionMessage
    }
    let choices: [Choice]
}

// MARK: - Parser

enum Parser {
    static func parse(content: String) -> LLMResponse {
        var sanitized = content
        let phase = extract(tag: "GAME_PHASE", from: &sanitized).flatMap(GamePhase.init(rawValue:))
        sanitized = sanitized.trimmingCharacters(in: .whitespacesAndNewlines)
        return LLMResponse(content: sanitized, phase: phase)
    }

    private static func extract(tag: String, from content: inout String) -> String? {
        let pattern = "<\(tag)>(.*?)</\(tag)>"
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.dotMatchesLineSeparators]) else {
            return nil
        }
        let range = NSRange(content.startIndex..<content.endIndex, in: content)
        guard let match = regex.firstMatch(in: content, options: [], range: range),
              let tagRange = Range(match.range(at: 0), in: content),
              let valueRange = Range(match.range(at: 1), in: content) else {
            return nil
        }
        let value = String(content[valueRange])
        content.removeSubrange(tagRange)
        return value
    }
}

// MARK: - Prompt Builder

struct SystemPromptBuilder {
    func makePayload(for lesson: Lesson, history: [Message]) -> [ChatMessagePayload] {
        var payload: [ChatMessagePayload] = []
        payload.append(ChatMessagePayload(role: ChatRole.system.rawValue, content: systemPrompt(for: lesson)))
        for message in history {
            guard message.role != .system else { continue }
            payload.append(ChatMessagePayload(role: message.role.rawValue, content: message.content))
        }
        return payload
    }

    private func systemPrompt(for lesson: Lesson) -> String {
        """
        You are the Game Master for a puzzle lesson.
        Lesson: \(lesson.number) — \(lesson.title)
        Skill: \(lesson.skill) — \(lesson.skillDescription)
        Goal: \(lesson.goal)
        Scenario: \(lesson.scenario)
        Answer format: \(lesson.answerFormat)
        Solution logic: \(lesson.solutionLogic)

        CORE RULES (STRICT ENFORCEMENT)
        1. ONE ATTRIBUTE PER QUESTION: The user must ask about exactly ONE attribute (color, shape, size, material, etc.) at a time. If they combine multiple attributes or ask broad questions, you MUST reject it and ask them to focus on one detail.
        2. ONE CLUE PER QUESTION: Each valid single-attribute question unlocks exactly ONE clue. Never give multiple clues in one response.
        3. CONSISTENT CLUE TEXT: Use the same clue wording each time the same attribute is asked. No creative variations.
        4. NEVER REVEAL THE ANSWER: Do not state the answer directly. Only reveal clues that point toward it.
        5. NO CONTRADICTIONS: If a question is too broad or vague, say so clearly. Do not praise broad questions as "good" — they violate the rule.

        RESPONSE FORMAT
        - Keep replies to 1-2 short sentences.
        - Be friendly and playful, but firm about the rules.
        - When a question targets one attribute correctly, reveal the clue for that attribute.
        - When a question is too broad/vague, clearly state: "Too broad — ask about one attribute at a time."
        - When the user solves it, celebrate and output <GAME_PHASE>COMPLETED_SUCCESS</GAME_PHASE>.

        TAGGING (MANDATORY)
        After every reply, output exactly one tag on a new line:
        - <GAME_PHASE>ACTIVE</GAME_PHASE> while the lesson continues
        - <GAME_PHASE>COMPLETED_SUCCESS</GAME_PHASE> when the user solves it
        - <GAME_PHASE>COMPLETED_FAIL</GAME_PHASE> only if they explicitly give up

        TONE
        - Playful, modern, brief. No corporate jargon.
        - Enforce rules consistently — don't be lenient with rule violations.

        EXTRA CONTEXT
        \(lesson.systemPrompt)
        """
    }
}

// MARK: - Errors

enum LLMServiceError: LocalizedError {
    case missingAPIKey
    case server(String)
    case missingContent

    var errorDescription: String? {
        switch self {
        case .missingAPIKey:
            return "Missing OPENAI_API_KEY environment variable."
        case .server(let message):
            return "Server error: \(message)"
        case .missingContent:
            return "The language model response was empty."
        }
    }
}

// MARK: - Mock

struct MockLLMService: LLMServiceProtocol {
    var cannedReply: String = "You carefully inspect the control panel.\n<GAME_PHASE>ACTIVE</GAME_PHASE>"

    func sendMessage(lesson: Lesson, history: [Message]) async throws -> LLMResponse {
        Parser.parse(content: cannedReply)
    }
}
