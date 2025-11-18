import SwiftUI

struct LaunchView: View {
    let onStart: () -> Void

    var body: some View {
        VStack(spacing: 32) {
            Spacer()

            VStack(spacing: 16) {
                Image(systemName: "sparkles")
                    .resizable()
                    .scaledToFit()
                    .frame(width: 80, height: 80)
                    .foregroundColor(.mint)

                Text("Prompt Arcade")
                    .font(.system(size: 48, weight: .bold))

                Text("Practice laser-focused questions inside short, playful lessons.")
                    .font(.title3)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
            }

            VStack(alignment: .leading, spacing: 12) {
                Text("Each run gives you a tiny puzzle, a skill to sharpen, and only a handful of turns. Ask one crisp question, get instant feedback, win the clue.")
                    .font(.body)
                    .foregroundColor(.primary)
                    .multilineTextAlignment(.center)
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(16)
            }
            .padding(.horizontal)

            VStack(alignment: .leading, spacing: 16) {
                FeatureRow(icon: "target", text: "Goal + skill clear from the start")
                FeatureRow(icon: "timer", text: "Limited turns keep every word intentional")
                FeatureRow(icon: "sparkles", text: "Instant feedback after every AI reply")
            }
            .padding()
            .frame(maxWidth: 400)

            Spacer()

            Button(action: onStart) {
                Text("Play the first lesson")
                    .font(.title3.bold())
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.accentColor)
                    .foregroundColor(.white)
                    .cornerRadius(18)
            }
            .padding(.horizontal, 32)
            .padding(.bottom, 40)
        }
        .padding()
    }
}

private struct FeatureRow: View {
    let icon: String
    let text: String
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(.accentColor)
                .frame(width: 30)
            Text(text)
                .font(.body)
        }
    }
}

struct LaunchView_Previews: PreviewProvider {
    static var previews: some View {
        LaunchView(onStart: {})
    }
}

