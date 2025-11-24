import SwiftUI

struct EndGameView: View {
    let result: LessonResult
    let onReplay: () -> Void
    let onNext: (() -> Void)?
    @Environment(\.dismiss) private var dismiss

    init(result: LessonResult, onReplay: @escaping () -> Void, onNext: (() -> Void)? = nil) {
        self.result = result
        self.onReplay = onReplay
        self.onNext = onNext
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    ResultHeaderView(result: result)
                    EfficiencyView(result: result)
                    MicroLessonView(result: result)
                    ShareCardView(summary: result.shareSummary)

                    HStack {
                        Button("Replay") {
                            dismiss()
                            onReplay()
                        }
                        .buttonStyle(.bordered)

                        Spacer()

                        Button(result.lesson.number == 0 ? "Continue" : "Next lesson") {
                            dismiss()
                            onNext?()
                        }
                        .buttonStyle(.borderedProminent)
                    }
                }
                .padding()
            }
            .navigationTitle(result.outcome == .success ? "Lesson complete" : "Try again")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

private struct ResultHeaderView: View {
    let result: LessonResult

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(result.outcome == .success ? "Run ended" : "Run ended")
                .font(.headline)
            Text("Turns: \(result.turnsUsed)/\(result.totalTurns)")
                .font(.subheadline)
                .foregroundColor(.secondary)
            Text(result.highlight)
                .font(.body)
                .padding(.top, 4)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct EfficiencyView: View {
    let result: LessonResult

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                HStack(spacing: 4) {
                    ForEach(0..<3, id: \.self) { index in
                        Image(systemName: index < result.efficiency.stars ? "star.fill" : "star")
                            .foregroundColor(.yellow)
                            .font(.caption)
                    }
                }
                Spacer()
                ProgressView(value: result.efficiency.progress)
                    .tint(.mint)
                    .frame(width: 100)
            }
        }
        .padding(.vertical, 8)
    }
}

private struct MicroLessonView: View {
    let result: LessonResult

    var body: some View {
        Text(result.microLesson)
            .font(.subheadline)
            .foregroundColor(.secondary)
    }
}

struct EndGameView_Previews: PreviewProvider {
    static var previews: some View {
        let lesson = PreviewLessonRepository().sample
        let feedbacks = [
            FeedbackRecord(turnIndex: 0, feedback: Feedback(type: .good, message: "Nice!")),
            FeedbackRecord(turnIndex: 1, feedback: Feedback(type: .excellent, message: "Great!"))
        ]
        let efficiency = EfficiencyRating(stars: 3, label: "Laser Focused", detail: "Great flow.", progress: 0.9)
        let result = LessonResult(
            lesson: lesson,
            outcome: .success,
            turnsUsed: 3,
            totalTurns: lesson.maxTurns,
            feedbackRecords: feedbacks,
            highlight: "Solved in 3 turns.",
            reflection: "Keep leading with the most telling detail.",
            microLesson: "Asking for one trait at a time keeps answers crisp.",
            efficiency: efficiency
        )
        EndGameView(result: result, onReplay: {})
    }
}
