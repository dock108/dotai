import SwiftUI

struct TutorialCard: Identifiable {
    let id = UUID()
    let title: String
    let message: String
    let imageName: String
}

struct TutorialView: View {
    let onFinish: () -> Void

    private let cards: [TutorialCard] = [
        TutorialCard(title: "AI-powered lessons", message: "Each lesson is a small productivity challenge powered by an AI assistant.", imageName: "brain"),
        TutorialCard(title: "Ask focused questions", message: "You use short, strategic messages to move forward — just like with real AI tools.", imageName: "timer"),
        TutorialCard(title: "Train practical AI skills", message: "Every lesson teaches a prompting skill you can apply at work.", imageName: "sparkles")
    ]

    @State private var selection = 0

    var body: some View {
        VStack(spacing: 24) {
            Text("AI Productivity Trainer")
                .font(.largeTitle.bold())
            Text("Complete short AI lessons that build real-world prompting skills.")
                .multilineTextAlignment(.center)
                .foregroundColor(.secondary)

            TabView(selection: $selection) {
                ForEach(Array(cards.enumerated()), id: \.offset) { index, card in
                    TutorialCardView(card: card)
                        .padding()
                        .tag(index)
                }
            }
            .tabViewStyle(.page(indexDisplayMode: .always))
            .frame(height: 300)

            Button(action: onFinish) {
                Text(selection == cards.count - 1 ? "Start lessons" : "Skip tutorial")
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.accentColor)
                    .foregroundColor(.white)
                    .cornerRadius(12)
            }
            .padding(.horizontal)
        }
        .padding()
    }
}

private struct TutorialCardView: View {
    let card: TutorialCard

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: card.imageName)
                .resizable()
                .scaledToFit()
                .frame(width: 64, height: 64)
                .foregroundColor(.accentColor)
            Text(card.title)
                .font(.title2.bold())
            Text(card.message)
                .multilineTextAlignment(.center)
                .foregroundColor(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity)
        .background(Color(uiColor: .secondarySystemBackground))
        .cornerRadius(20)
    }
}

struct TutorialView_Previews: PreviewProvider {
    static var previews: some View {
        TutorialView(onFinish: {})
    }
}
