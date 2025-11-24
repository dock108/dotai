import SwiftUI

struct RootFlowView: View {
    @StateObject private var store = LessonStore()
    @StateObject private var completionTracker = LessonCompletionTracker()
    @AppStorage("hasSeenLaunch") private var hasSeenLaunch = false
    @AppStorage("hasSeenHowToPlay") private var hasSeenHowToPlay = false
    @State private var selectedLesson: Lesson?
    @State private var shouldShowLesson0 = false
    @State private var showHowToPlay = false

    private var hasCompletedLesson0: Bool {
        completionTracker.isComplete(0)
    }

    var body: some View {
        NavigationStack {
            Group {
                if !hasSeenLaunch {
                    LaunchView(onStart: {
                        hasSeenLaunch = true
                        if !hasSeenHowToPlay {
                            showHowToPlay = true
                        } else {
                            shouldShowLesson0 = true
                        }
                    })
                } else if shouldShowLesson0 && !hasCompletedLesson0 {
                    if let lesson0 = store.lesson(for: 0) {
                        LessonPlayView(
                            viewModel: LessonViewModel(lesson: lesson0),
                            completionTracker: completionTracker,
                            onComplete: {
                                shouldShowLesson0 = false
                            }
                        )
                    } else {
                        LessonListView(
                            completionTracker: completionTracker,
                            onSelect: { selectedLesson = $0 }
                        )
                    }
                } else {
                    LessonListView(
                        completionTracker: completionTracker,
                        onSelect: { selectedLesson = $0 }
                    )
                }
            }
            .navigationDestination(item: $selectedLesson) { lesson in
                LessonPlayView(
                    viewModel: LessonViewModel(lesson: lesson),
                    completionTracker: completionTracker,
                    onComplete: {
                        selectedLesson = nil
                    }
                )
            }
        }
        .environmentObject(store)
        .sheet(isPresented: $showHowToPlay) {
            HowToPlayView(onDismiss: {
                hasSeenHowToPlay = true
                showHowToPlay = false
                shouldShowLesson0 = true
            })
        }
    }
}

struct HowToPlayView: View {
    let onDismiss: () -> Void
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Image(systemName: "questionmark.circle.fill")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 60, height: 60)
                    .foregroundColor(.accentColor)
                
                Text("How to Play")
                    .font(.title.bold())
                
            VStack(alignment: .leading, spacing: 16) {
                RuleRow(icon: "1.circle.fill", text: "Look at the puzzle card. Pick ONE attribute you want clarified.")
                RuleRow(icon: "2.circle.fill", text: "Ask a question about only that attribute (color, shape, category, etc.).")
                RuleRow(icon: "3.circle.fill", text: "The game unlocks a clue. Clue markers light up so you see progress.")
                RuleRow(icon: "4.circle.fill", text: "Combine 2–3 clues, then make your guess. Single-question clarity wins.")
            }
                .padding()
                
                Spacer()
                
                Button(action: {
                    dismiss()
                    onDismiss()
                }) {
                    Text("Got it!")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.accentColor)
                        .foregroundColor(.white)
                        .cornerRadius(12)
                }
                .padding(.horizontal)
                .padding(.bottom)
            }
            .padding()
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Skip") {
                        dismiss()
                        onDismiss()
                    }
                }
            }
        }
    }
}

private struct RuleRow: View {
    let icon: String
    let text: String
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(.accentColor)
            Text(text)
                .font(.body)
        }
    }
}

struct RootFlowView_Previews: PreviewProvider {
    static var previews: some View {
        RootFlowView()
    }
}
