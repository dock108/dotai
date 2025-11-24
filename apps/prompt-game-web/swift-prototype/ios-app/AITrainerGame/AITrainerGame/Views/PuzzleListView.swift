import SwiftUI

struct LessonListView: View {
    @EnvironmentObject private var store: LessonStore
    @ObservedObject var completionTracker: LessonCompletionTracker
    let onSelect: (Lesson) -> Void

    private var moduleOrder: [LessonModule] { [.foundation, .clarity, .narrowing, .constraints, .prioritization] }
    
    private var nextLesson: Lesson? {
        guard let next = completionTracker.nextLessonNumber else { return store.lessons.first }
        return store.lesson(for: next) ?? store.lessons.first
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 32) {
                ForEach(moduleOrder, id: \.self) { module in
                    let lessons = store.lessons.filter { $0.module == module }
                    if !lessons.isEmpty {
                        ModuleSectionView(
                            module: module,
                            lessons: lessons,
                            completionTracker: completionTracker,
                            nextLessonNumber: nextLesson?.number,
                            onSelect: onSelect
                        )
                    }
                }
                
                HowItWorksCard()
            }
            .padding()
        }
        .navigationTitle("Training Modules")
    }
}

private struct ModuleSectionView: View {
    let module: LessonModule
    let lessons: [Lesson]
    let completionTracker: LessonCompletionTracker
    let nextLessonNumber: Int?
    let onSelect: (Lesson) -> Void
    
    private var accentColor: Color { module.accentColor }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 12) {
                ModuleIconBadge(iconName: module.iconName, color: accentColor)
                VStack(alignment: .leading, spacing: 4) {
                    Text(module.displayName)
                        .font(.title3.bold())
                    Text(module.description)
                        .font(.footnote)
                        .foregroundColor(.secondary)
                }
                Spacer()
                ModuleProgressDots(
                    total: lessons.count,
                    completed: lessons.filter { completionTracker.isComplete($0.number) }.count,
                    accentColor: accentColor
                )
            }
            
            VStack(spacing: 12) {
                ForEach(lessons) { lesson in
                    LessonRowCard(
                        lesson: lesson,
                        isComplete: completionTracker.isComplete(lesson.number),
                        isNext: lesson.number == nextLessonNumber,
                        action: { onSelect(lesson) }
                    )
                }
            }
        }
        .padding()
        .background(
            LinearGradient(
                colors: [accentColor.opacity(0.15), accentColor.opacity(0.05)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .clipShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
        )
    }
}

private struct ModuleProgressDots: View {
    let total: Int
    let completed: Int
    let accentColor: Color
    
    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<total, id: \.self) { index in
                Circle()
                    .fill(index < completed ? accentColor : Color(.systemGray4))
                    .frame(width: 8, height: 8)
            }
        }
    }
}

private struct LessonRowCard: View {
    let lesson: Lesson
    let isComplete: Bool
    let isNext: Bool
    let action: () -> Void
    
    private var accentColor: Color { lesson.moduleAccentColor }

    var body: some View {
        Button(action: action) {
            HStack(alignment: .top, spacing: 14) {
                ModuleIconBadge(iconName: lesson.moduleIconName, color: accentColor)
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 8) {
                        Text("Lesson \(lesson.number)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                        if isComplete {
                            Image(systemName: "checkmark.seal.fill")
                                .foregroundColor(.green)
                        }
                    }
                    Text(lesson.title)
                        .font(.headline)
                    Text(lesson.skillDescription)
                        .font(.footnote)
                        .foregroundColor(.secondary)
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 6) {
                    if isNext {
                        Text("Next up")
                            .font(.caption.bold())
                            .padding(.horizontal, 10)
                            .padding(.vertical, 4)
                            .background(accentColor.opacity(0.15))
                            .foregroundColor(accentColor)
                            .clipShape(Capsule())
                    }
                    InfoChip(icon: "timer", text: "\(lesson.maxTurns) Q")
                    InfoChip(icon: "bolt.fill", text: (lesson.difficulty?.displayName ?? "Warmup"))
                }
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .fill(Color(.systemBackground))
                    .shadow(color: accentColor.opacity(0.08), radius: 8, x: 0, y: 3)
            )
        }
        .buttonStyle(.plain)
    }
}

private struct ModuleIconBadge: View {
    let iconName: String
    let color: Color
    
    var body: some View {
        ZStack {
            Circle()
                .fill(color.opacity(0.18))
                .frame(width: 46, height: 46)
            Image(systemName: iconName)
                .foregroundColor(color)
        }
    }
}

private struct InfoChip: View {
    let icon: String
    let text: String
    
    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
            Text(text)
        }
        .font(.caption.bold())
        .padding(.horizontal, 10)
        .padding(.vertical, 4)
        .background(Color(.secondarySystemBackground))
        .clipShape(Capsule())
    }
}

private struct HowItWorksCard: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("How it works")
                .font(.headline)
            Label("One focused question per turn", systemImage: "1.circle.fill")
            Label("Turns are limited — make them count", systemImage: "timer")
            Label("Feedback appears after every AI reply", systemImage: "sparkles")
        }
        .font(.footnote)
        .foregroundColor(.secondary)
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemBackground))
        .cornerRadius(18)
    }
}

struct LessonListView_Previews: PreviewProvider {
    static var previews: some View {
        let store = LessonStore(repository: PreviewLessonRepository())
        NavigationStack {
            LessonListView(
                completionTracker: LessonCompletionTracker(),
                onSelect: { _ in }
            )
        }
        .environmentObject(store)
    }
}
