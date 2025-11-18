# AI Productivity Trainer (Lessons v1.0)

SwiftUI iOS app where users complete 11 short AI-powered **lessons** (0–10). Each lesson is a micro productivity challenge that trains one prompting skill (clarifying questions, breaking tasks down, summarising, etc.), and the end screen walks through what the user did well with a Wordle-style share card.

## Project Layout

```
AITrainerGame/
  AITrainerGame.xcodeproj      # Xcode project (iOS 17+)
  AITrainerGame/
    AITrainerGameApp.swift     # App entry, navigation shell
    Models/                    # Lesson data (Puzzle), Message, ShareSummary, etc.
    Data/                      # JSON loader + puzzles.json dataset (lessons)
    ViewModels/                # PuzzleStore + PuzzleViewModel turn logic
    Services/                  # LLMService w/ OpenAI-style API call + parser
    Views/                     # Tutorial, list, gameplay, end card, share view
    Resources/
      Assets.xcassets          # AppIcon placeholders
      Preview Content/         # Preview assets bundle
      Info.plist               # Minimal Info plist
```

## Running the App

1. Open `AITrainerGame/AITrainerGame.xcodeproj` in Xcode 15+
2. Select the `AITrainerGame` scheme and an iOS 17 simulator (or device)
3. Provide an API key for your chat model of choice (see below)
4. Build & run.

### Configuring the LLM

`LLMService` now reads secrets through `SecretsProvider`, which looks for (in order):

1. A runtime `OPENAI_API_KEY` environment variable — handy for local dev.
2. A bundled `Secrets.plist` file (gitignored) that you can generate per build.

Steps for **local development**:

```bash
cp AITrainerGame/AITrainerGame/Resources/Secrets.template.plist AITrainerGame/AITrainerGame/Resources/Secrets.plist
plutil -replace LLM_API_KEY -string "sk-your-key" AITrainerGame/AITrainerGame/Resources/Secrets.plist
plutil -replace LLM_MODEL -string "gpt-4o-mini" AITrainerGame/AITrainerGame/Resources/Secrets.plist
```

Steps for **CI/TestFlight** builds:

1. Save your provider key in the CI secrets manager.
2. Before `xcodebuild`, run a script that copies the template and injects the secret (example below).

```bash
cp AITrainerGame/AITrainerGame/Resources/Secrets.template.plist AITrainerGame/AITrainerGame/Resources/Secrets.plist
plutil -replace LLM_API_KEY -string "$OPENAI_API_KEY" AITrainerGame/AITrainerGame/Resources/Secrets.plist
```

Because `Secrets.plist` is ignored by git, nothing sensitive lands in the repo. TestFlight builds will contain the key (there’s no backend in this MVP), but the key never lives in source control. Rotate/revoke as needed.

You can still override the defaults programmatically by passing a custom `LLMConfiguration` (useful for previews/tests).

The service currently targets `gpt-4o-mini` with temperature 0.5. Adjust `LLMConfiguration` or the template file for alternative models.

### Lesson Loop

- Tutorial cards onboard users to the lesson / skill framing
- Lesson list displays 11 lessons (#0–10) with message limits and descriptions
- `PuzzlePlayView` (lesson play view) shows scenario, “How this puzzle works”, chat log, progress row, and messages remaining
- After every AI reply the `<PROGRESS>` and `<GAME_STATE>` tags are parsed to update Wordle-style progress squares and determine completion
- `EndGameView` summarizes the lesson outcome, explanation, **Skill Focus**, what went well, a real-world tip, and offers replay/next controls
- `ShareSummary` produces a Wordle-style share snippet such as:
  - `AI Lesson #3 — Completed in 4 messages`
  - `🟩🟨⬛🟩⬛⬛`
  - `Skill: Clarifying Questions`

## Data + Prompt Template

- `puzzles.json` contains all 11 lessons, including scenario text, goals, answer formats, skill metadata, and message limits. Update this file to tune copy or add new lessons.
- `Puzzle` model exposes `skill` and `skillDescription` (backed by `skillName` / `teachingGoal`) for productivity-focused UI and prompts.
- `LLMService.SystemPromptBuilder` implements the shared system prompt template and injects:
  - Lesson number, scenario, goal, answer format
  - Skill name & description
  - Productivity trainer guidance:
    - Briefly praise good use of the skill
    - Gently nudge away from vague/broad questions

## Outstanding / Next Steps

- 🔄 Plug in a real API key and test live completions on physical devices
- 🎨 Optionally tune the color palette via `Assets.xcassets` to match your brand
- 🧪 Add more unit/UI tests (see `TESTING.md`)
- 📋 Consider persisting solved/failed state across launches using your preferred storage

## Sharing & Docs

- Wordle-style summary lives in `ShareCardView` / `ShareSummary`
- This README captures build/run instructions and the productivity framing for lessons; see `TESTING.md` for a detailed testing guide
