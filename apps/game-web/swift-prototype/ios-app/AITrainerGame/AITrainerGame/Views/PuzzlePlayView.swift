import SwiftUI

struct LessonPlayView: View {
    @StateObject var viewModel: LessonViewModel
    let completionTracker: LessonCompletionTracker?
    let onComplete: (() -> Void)?
    
    private var accentColor: Color {
        viewModel.lesson.moduleAccentColor
    }
    
    init(
        viewModel: LessonViewModel,
        completionTracker: LessonCompletionTracker? = nil,
        onComplete: (() -> Void)? = nil
    ) {
        _viewModel = StateObject(wrappedValue: viewModel)
        self.completionTracker = completionTracker
        self.onComplete = onComplete
    }

    var body: some View {
        VStack(spacing: 0) {
            lessonHeader
            Divider()
            chatTranscript
            messageComposer
        }
        .background(Color(.systemGroupedBackground))
        .navigationTitle("Lesson \(viewModel.lesson.number)")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $viewModel.showResultSheet, onDismiss: {
            viewModel.restart()
            if let result = viewModel.result {
                completionTracker?.markComplete(result)
                onComplete?()
            }
        }) {
            if let result = viewModel.result {
                EndGameView(
                    result: result,
                    onReplay: { viewModel.restart() },
                    onNext: { onComplete?() }
                )
                .presentationDetents([.large])
            }
        }
        .toast(message: $viewModel.toastMessage)
    }

    private var lessonHeader: some View {
        VStack(alignment: .leading, spacing: 16) {
            ObjectiveBar(lesson: viewModel.lesson)
            missionBriefing
            
            if !viewModel.clueProgress.isEmpty {
                ClueProgressView(progress: viewModel.clueProgress, accentColor: accentColor)
            }
            
            HStack(spacing: 8) {
                if !viewModel.feedbackRecords.isEmpty {
                    FeedbackTimelineView(
                        records: viewModel.feedbackRecords,
                        totalTurns: viewModel.lesson.maxTurns
                    )
                }
                Spacer()
                TurnCounterView(label: viewModel.turnCounterLabel, turnsRemaining: viewModel.turnsRemaining, phase: viewModel.phase)
            }
        }
        .padding()
        .background(Color(.systemGroupedBackground))
    }

    private var missionBriefing: some View {
        VStack(alignment: .leading, spacing: 12) {
            MissionQuickStats(
                title: "Attributes in play",
                values: viewModel.lesson.attributes.isEmpty ? ["Weather", "Temperature", "Storm chance"] : viewModel.lesson.attributes,
                accentColor: accentColor
            )
            
            MissionQuickStats(
                title: "Rules of engagement",
                values: [
                    "One question per turn",
                    "Single attribute per question",
                    "Focused = clue unlocked"
                ],
                accentColor: accentColor,
                bulletStyle: .dash
            )
            
            MissionObjectiveRow(answerFormat: viewModel.lesson.answerFormat)
            
            if let rule = viewModel.ruleText {
                MissionHintRow(
                    text: rule,
                    accentColor: accentColor,
                    showTooltip: viewModel.lesson.number == 0
                )
            }
            
            DisclosureGroup("Task background") {
                Text(viewModel.lesson.scenario)
                                .font(.footnote)
                                .foregroundColor(.secondary)
                    .padding(.top, 4)
            }
            .tint(accentColor)
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(Color(.systemBackground))
                .overlay(
                    RoundedRectangle(cornerRadius: 24, style: .continuous)
                        .stroke(accentColor.opacity(0.15), lineWidth: 1.5)
                )
        )
    }

    private var chatTranscript: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    ForEach(viewModel.messages) { message in
                        MessageBubbleView(message: message, accentColor: accentColor)
                            .id(message.id)
                    }
                }
                .padding()
            }
            .background(
                RoundedRectangle(cornerRadius: 24)
                    .fill(Color(.secondarySystemBackground))
                    .overlay(
                        RoundedRectangle(cornerRadius: 24)
                            .stroke(accentColor.opacity(0.15), lineWidth: 1.5)
                    )
            )
            .padding(.horizontal)
            .onChange(of: viewModel.messages.count) { _, _ in
                if let lastId = viewModel.messages.last?.id {
                    withAnimation {
                        proxy.scrollTo(lastId, anchor: .bottom)
                    }
                }
            }
        }
    }

    private var messageComposer: some View {
        VStack(spacing: 12) {
            if !viewModel.lesson.exampleQuestions.isEmpty {
                ExampleChipRow(questions: viewModel.lesson.exampleQuestions, accentColor: accentColor) { question in
                    viewModel.inputText = question
                }
                .padding(.horizontal)
                .padding(.top, 12)
            }
            
            VStack(alignment: .leading, spacing: 8) {
                Text("Your Question")
                    .font(.caption.bold())
                    .foregroundColor(.secondary)
                HStack(alignment: .bottom, spacing: 12) {
                    TextField(placeholderText, text: $viewModel.inputText, axis: .vertical)
                        .lineLimit(1...4)
                        .padding(12)
                        .background(
                            RoundedRectangle(cornerRadius: 16)
                                .stroke(accentColor.opacity(0.4), lineWidth: 1.5)
                        )
                        .disabled(viewModel.phase.isCompleted)
                    Button(action: { Task { await viewModel.sendMessage() } }) {
                        if viewModel.isLoading {
                            ProgressView()
                        } else {
                            VStack(spacing: 4) {
                                Image(systemName: "terminal")
                                Text("Send")
                                    .font(.caption2.bold())
                            }
                        }
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .background(viewModel.canSendMessage ? accentColor : Color.gray)
                    .foregroundColor(.white)
                    .cornerRadius(14)
                    .disabled(!viewModel.canSendMessage)
                }
                if let validation = viewModel.validationMessage {
                    Text(validation)
                            .font(.caption)
                            .foregroundColor(.red)
                    } else {
                    Text("\(viewModel.inputText.count) / 240")
                            .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding([.horizontal, .bottom])
        }
        .background(Color(.systemBackground))
    }
    
    private var placeholderText: String {
        viewModel.ruleText ?? "Ask a single, vivid question..."
    }
}

// MARK: - Subviews

private struct ExampleChipRow: View {
    let questions: [String]
    let accentColor: Color
    let onTap: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Available moves")
                .font(.caption.bold())
                .foregroundColor(.secondary)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(questions, id: \.self) { question in
                        Button(action: { onTap(question) }) {
                            HStack(spacing: 6) {
                                Image(systemName: "target")
                                Text(question)
                            }
                            .font(.caption.bold())
                            .foregroundColor(accentColor)
                            .padding(.horizontal, 14)
                            .padding(.vertical, 10)
                            .background(
                                RoundedRectangle(cornerRadius: 16, style: .continuous)
                                    .stroke(accentColor, lineWidth: 1.5)
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.vertical, 4)
            }
        }
        .padding(.horizontal)
    }
}

private struct ObjectiveBar: View {
    let lesson: Lesson
    
    var body: some View {
        HStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(lesson.moduleAccentColor.opacity(0.15))
                    .frame(width: 38, height: 38)
                Image(systemName: lesson.moduleIconName)
                    .foregroundColor(lesson.moduleAccentColor)
            }
            VStack(alignment: .leading, spacing: 2) {
                Text("\(lesson.module.displayName) · Objective")
                    .font(.caption.bold())
                    .foregroundColor(.secondary)
                Text(lesson.goal)
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(2)
            }
            Spacer()
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 12)
        .background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(lesson.moduleAccentColor.opacity(0.08))
        )
    }
}

private struct MissionQuickStats: View {
    enum BulletStyle {
        case dot, dash
    }
    
    let title: String
    let values: [String]
    let accentColor: Color
    var bulletStyle: BulletStyle = .dot
    
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title.uppercased())
                .font(.caption2.weight(.semibold))
                .foregroundColor(accentColor)
                .tracking(1)
            ForEach(values, id: \.self) { value in
                HStack(alignment: .top, spacing: 6) {
                    Text(bulletStyle == .dot ? "•" : "–")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(value)
                        .font(.subheadline)
                }
            }
        }
    }
}

private struct MissionObjectiveRow: View {
    let answerFormat: String
    
    var body: some View {
        HStack {
            Text("What you must figure out")
                .font(.caption2.bold())
                .foregroundColor(.secondary)
            Spacer()
            Text(answerFormat)
                .font(.callout.weight(.semibold))
        }
    }
}

private struct MissionHintRow: View {
    let text: String
    let accentColor: Color
    let showTooltip: Bool
    @State private var showSheet = false
    
    var body: some View {
        Button {
            if showTooltip { showSheet = true }
        } label: {
                        HStack {
                Image(systemName: "lightbulb")
                    .foregroundColor(accentColor)
                Text(text)
                    .font(.footnote)
                    .foregroundColor(.secondary)
                            Spacer()
                if showTooltip {
                    Image(systemName: "questionmark.circle")
                                .foregroundColor(.secondary)
                        }
            }
            .padding(10)
            .background(accentColor.opacity(0.1))
            .cornerRadius(12)
        }
        .buttonStyle(.plain)
        .sheet(isPresented: $showSheet) {
            TutorialTooltipView()
        }
    }
}

private struct TurnCounterView: View {
    let label: String
    let turnsRemaining: Int
    let phase: GamePhase

    var body: some View {
        Text(label)
            .font(.caption2)
            .foregroundColor(color)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(color.opacity(0.1))
            .clipShape(Capsule())
    }

    private var color: Color {
        if phase.isCompleted {
            return .gray
        } else if turnsRemaining <= 1 {
            return .red
        } else {
            return .blue
        }
    }
}

struct SkillBadgeView: View {
    let text: String

    var body: some View {
        Text(text.uppercased())
            .font(.caption2.bold())
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
            .background(Color(red: 0.8, green: 0.86, blue: 1.0))
            .foregroundColor(Color(red: 0.33, green: 0.29, blue: 0.64))
            .clipShape(Capsule())
    }
}

private struct FeedbackTimelineView: View {
    let records: [FeedbackRecord]
    let totalTurns: Int

    var body: some View {
        HStack(spacing: 6) {
            ForEach(0..<totalTurns, id: \.self) { index in
                Circle()
                    .fill(color(for: records.first { $0.turnIndex == index }?.feedback.type))
                    .frame(width: 10, height: 10)
            }
        }
    }

    private func color(for type: FeedbackType?) -> Color {
        guard let type else {
            return Color.gray // Inactive attribute
        }
        switch type {
        case .excellent, .good:
            return .green // Valid focused question
        case .partial, .guessing:
            return .yellow // Vague
        case .vague:
            return .orange // Too fuzzy
        case .broad, .offTrack:
            return .red // Too broad
        }
    }
}

private struct MessageBubbleView: View {
    let message: Message
    let accentColor: Color

    var body: some View {
        VStack(alignment: message.role == .assistant ? .leading : .trailing, spacing: 6) {
            VStack(alignment: .leading, spacing: 6) {
                Text(message.role == .assistant ? "AI DETAIL" : "YOUR QUESTION")
                    .font(.caption2.bold())
                    .foregroundColor(message.role == .assistant ? accentColor : .secondary)
                Text(message.content)
                    .font(.body.monospacedDigit())
            }
            .padding(14)
            .background(bubbleColor)
            .foregroundColor(message.role == .assistant ? .primary : .white)
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))

            if message.role == .assistant, let feedback = message.feedback {
                FeedbackTagView(feedback: feedback)
            }
        }
        .frame(maxWidth: .infinity, alignment: message.role == .assistant ? .leading : .trailing)
    }

    private var bubbleColor: Color {
        message.role == .assistant
            ? accentColor.opacity(0.1)
            : accentColor
    }
}

private struct FeedbackTagView: View {
    let feedback: Feedback

    var body: some View {
        Text(feedback.message)
            .font(.caption)
            .foregroundColor(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(color.opacity(0.12))
            .clipShape(Capsule())
    }

    private var color: Color {
        switch feedback.type {
        case .excellent, .good:
            return .green // Valid focused question
        case .partial, .guessing:
            return .yellow // Vague
        case .vague:
            return .orange // Too fuzzy
        case .broad, .offTrack:
            return .red // Too broad
        }
    }
}

private struct RuleBanner: View {
    let rule: String

    var body: some View {
        Text(rule)
            .font(.caption)
            .foregroundColor(.secondary)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
    }
}

private struct ClueProgressView: View {
    let progress: [ClueProgress]
    let accentColor: Color

    var body: some View {
        let nextAvailable = progress.first(where: { !$0.isUnlocked })?.id
        
        HStack(spacing: 10) {
            Text("Details:")
                .font(.caption.bold())
                .foregroundColor(.secondary)
            ForEach(progress) { item in
                let state = ClueState.resolve(for: item, nextAvailableId: nextAvailable)
                HStack(spacing: 6) {
                    ZStack {
                        Circle()
                            .fill(fillColor(for: state))
                            .frame(width: 28, height: 28)
                        Image(systemName: state.iconName(for: item.title))
                            .foregroundColor(iconColor(for: state))
                            .font(.caption)
                    }
                    Text(item.title)
                        .font(.caption2.weight(state == .unlocked ? .semibold : .regular))
                        .foregroundColor(textColor(for: state))
                }
                .padding(.horizontal, 6)
                .padding(.vertical, 4)
                .background(
                    Capsule()
                        .fill(pillColor(for: state))
                )
            }
        }
    }
    
    private func fillColor(for state: ClueState) -> Color {
        switch state {
        case .unlocked: return accentColor.opacity(0.2)
        case .available: return Color.yellow.opacity(0.25)
        case .locked: return Color(.systemGray6)
        }
    }
    
    private func iconColor(for state: ClueState) -> Color {
        switch state {
        case .unlocked: return accentColor
        case .available: return Color.orange
        case .locked: return Color.gray
        }
    }
    
    private func textColor(for state: ClueState) -> Color {
        switch state {
        case .unlocked, .available: return .primary
        case .locked: return .secondary
        }
    }
    
    private func pillColor(for state: ClueState) -> Color {
        switch state {
        case .unlocked: return accentColor.opacity(0.08)
        case .available: return Color.yellow.opacity(0.18)
        case .locked: return Color(.systemGray5)
        }
    }
    
    private enum ClueState: Equatable {
        case unlocked
        case available
        case locked
        
        static func resolve(for item: ClueProgress, nextAvailableId: String?) -> ClueState {
            if item.isUnlocked { return .unlocked }
            if item.id == nextAvailableId { return .available }
            return .locked
        }
        
        func iconName(for title: String) -> String {
            let lower = title.lowercased()
            if lower.contains("weather") { return "sun.max.fill" }
            if lower.contains("temp") { return "thermometer" }
            if lower.contains("storm") || lower.contains("rain") { return "cloud.bolt.rain.fill" }
            if lower.contains("category") { return "line.horizontal.3.decrease.circle" }
            if lower.contains("constraint") { return "slider.horizontal.3" }
            return self == .unlocked ? "checkmark" : "questionmark"
        }
    }
}

private struct TutorialTooltipButton: View {
    @State private var showTooltip = false
    
    var body: some View {
        Button(action: { showTooltip = true }) {
            Image(systemName: "questionmark.circle")
                    .font(.caption)
                    .foregroundColor(.secondary)
        }
        .sheet(isPresented: $showTooltip) {
            TutorialTooltipView()
        }
    }
}

private struct TutorialTooltipView: View {
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 20) {
                Text("What counts as a single-detail question?")
                    .font(.headline)
                
                VStack(alignment: .leading, spacing: 12) {
                    Text("Valid examples:")
                        .font(.subheadline.bold())
                    
                    ExampleRow(question: "What's the weather?", isValid: true)
                    ExampleRow(question: "What's the temperature?", isValid: true)
                    ExampleRow(question: "Is there any storm chance?", isValid: true)
                    
                    Text("Invalid example:")
                        .font(.subheadline.bold())
                        .padding(.top, 8)
                    
                    ExampleRow(question: "What's the weather AND temperature?", isValid: false)
                }
                
                Spacer()
            }
            .padding()
            .navigationTitle("How to ask")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

private struct ExampleRow: View {
    let question: String
    let isValid: Bool

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: isValid ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundColor(isValid ? .green : .red)
            Text(question)
                .font(.subheadline)
        }
    }
}

struct LessonPlayView_Previews: PreviewProvider {
    static var previews: some View {
        LessonPlayView(
            viewModel: LessonViewModel(lesson: PreviewLessonRepository().sample),
            completionTracker: nil
        )
    }
}

struct PreviewLessonRepository: LessonRepositoryProtocol {
    func loadLessons() throws -> [Lesson] {
        [
            Lesson(
                id: 0,
                number: 0,
                module: .foundation,
                title: "One Question, One Detail",
                skill: "Clarity",
                skillDescription: "Ask for one missing fact at a time.",
                goal: "Identify the best day for a walk using 3 clear questions.",
                scenario: "You want to pick the best day this week for a long walk. The AI assistant knows three details: weather, temperature, and storm chance. It will reveal one detail at a time, but only if your question focuses on a single attribute.",
                answerFormat: "Day of the week",
                maxTurns: 3,
                exampleQuestions: ["What's the weather?", "What's the temperature?", "Is there any storm chance?"],
                solutionLogic: "Each attribute (weather, temperature, storm chance) reveals one detail. Saturday has sunny weather, 72° temperature, and 0% storm chance.",
                systemPrompt: "Keep responses clear and focused on one attribute at a time.",
                tutorialScript: nil,
                difficulty: .warmup
            )
        ]
    }

    var sample: Lesson {
        (try? loadLessons().first) ?? Lesson(
            id: 0,
            number: 0,
            module: .foundation,
            title: "One Question, One Detail",
            skill: "Clarity",
            skillDescription: "Ask for one missing fact at a time.",
            goal: "Identify the best day for a walk using 3 clear questions.",
            scenario: "You want to pick the best day this week for a long walk. The AI assistant knows three details: weather, temperature, and storm chance. It will reveal one detail at a time, but only if your question focuses on a single attribute.",
            answerFormat: "Day of the week",
            maxTurns: 3,
            exampleQuestions: ["What's the weather?", "What's the temperature?", "Is there any storm chance?"],
            solutionLogic: "Each attribute (weather, temperature, storm chance) reveals one detail. Saturday has sunny weather, 72° temperature, and 0% storm chance.",
            systemPrompt: "Keep responses clear and focused on one attribute at a time.",
            tutorialScript: nil,
            difficulty: .warmup
        )
    }
}
