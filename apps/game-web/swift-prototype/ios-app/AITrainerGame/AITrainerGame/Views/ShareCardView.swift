import SwiftUI

struct ShareCardView: View {
    let summary: ShareSummary

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Share your run")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(summary.titleLine)
                        .font(.headline)
                    Text(summary.detailLine)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                Spacer()
                Text(summary.solved ? "✨" : "🔁")
                    .font(.system(size: 32))
            }

            VStack(alignment: .leading, spacing: 8) {
                ProgressView(value: summary.progress)
                    .tint(.mint)
                Text(summary.feedbackLine)
                    .font(.system(.body, design: .monospaced))
            }

            ShareLink("Save + share", item: summary.shareText)
                .buttonStyle(.borderedProminent)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(Color(.secondarySystemBackground))
        )
    }
}

struct ShareCardView_Previews: PreviewProvider {
    static var previews: some View {
        let feedback = [
            FeedbackRecord(turnIndex: 0, feedback: Feedback(type: .good, message: "")),
            FeedbackRecord(turnIndex: 1, feedback: Feedback(type: .excellent, message: "")),
            FeedbackRecord(turnIndex: 2, feedback: Feedback(type: .partial, message: ""))
        ]
        ShareCardView(
            summary: ShareSummary(
                lessonNumber: 1,
                solved: true,
                turnsUsed: 3,
                turnLimit: 5,
                skillName: "Narrowing scope",
                feedbackRecords: feedback
            )
        )
        .padding()
    }
}
