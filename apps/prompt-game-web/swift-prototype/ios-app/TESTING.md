# AI Productivity Trainer – Testing Guide

This guide focuses on **manual and lightweight automated testing** for the AI Productivity Trainer app. It assumes you are running on Xcode 15+ with an iOS 17+ simulator or device.

---

## 1. Environments

### 1.1 Local dev

- Device: any iOS 17+ simulator (e.g., iPhone 15 Pro) or physical device  
- Scheme: `AITrainerGame`  
- Secrets:
  - Ensure `Secrets.plist` exists in `AITrainerGame/AITrainerGame/Resources/` with a valid `LLM_API_KEY` and `LLM_MODEL`.
  - Alternatively, set `OPENAI_API_KEY` in the scheme environment.

### 1.2 Mock LLM mode (for deterministic UI tests)

Use `MockLLMService` in previews or tests by injecting it into `PuzzleViewModel` instead of the real `LLMService`. This lets you:

- Verify tag parsing  
- Test progress row updates  
- Test end-of-lesson transitions without real network calls

---

## 2. Smoke Tests (Happy Path)

### 2.1 First launch

1. Clean install the app.  
2. Verify the **Tutorial** screen shows:
   - Title: “AI Productivity Trainer”
   - Three cards describing AI-powered lessons, focused questions, and practical skills.
3. Tap **Start lessons**.  
4. Confirm you land in **Lesson 0** or lesson list depending on the current flow.

### 2.2 Lesson 0 – Clarify a Vague Request

Goal: ensure the tutorial lesson is extremely approachable.

1. Start Lesson 0.  
2. Verify header:
   - Scenario card shows the manager/folder story in full.
   - “How this puzzle works” card explains goal and answer format.
   - Skill focus mentions **Asking clarifying questions**.
3. Check example questions above the input:
   - Buttons like “Who needs this folder?”.  
   - Tapping a chip should populate the text field.
4. Send a vague question (e.g., “What is this folder protecting?”):
   - The GM should respond with concrete suggested clarifying questions.
   - `<PROGRESS>` should usually map to 🟨 or 🟩 (not always ⬛).
5. Ask 1–2 of the suggested clarifying questions.  
6. Make a final guess (e.g., `master key blueprint`).  
7. Verify end screen shows:
   - “Lesson completed”.  
   - Messages used (X / limit).  
   - Skill focus and XP.  
   - “Lesson Recap” and “Skill Focus” sections with real-world example.
8. Check the share sheet:
   - Text includes `AI Lesson #0 — Completed in X messages`  
   - And `Skill: Asking clarifying questions`.

### 2.3 Lesson list behaviour

1. Return to the lesson list.  
2. Verify:
   - Title: “AI Lessons”.  
   - Each row reads `Lesson N — Title`.  
   - A `Skill: …` line appears under each description.  
   - Recently completed card shows Lesson 0.  
   - “Next Up” section highlights the next incomplete lesson.

### 2.4 Random later lessons

For at least lessons 3, 5, 7, 9:

1. Open the lesson.  
2. Confirm the scenario text matches a productivity theme (projects, summaries, assumptions, etc.).  
3. Ask a few messages that demonstrate the target skill (e.g., breaking tasks into steps).  
4. Ensure the GM:
   - Sometimes praises good skill usage.  
   - Nudges you when you are vague.  
5. Complete or exhaust messages and verify the end screen shows the correct **Skill Focus** and share card.

---

## 3. Behavioural Edge Cases

### 3.1 No network / LLM error

1. Temporarily invalidate the API key or disconnect the network.  
2. Attempt to send a message.  
3. Verify:
   - An assistant message appears with a clear error (from `LLMServiceError`).  
   - A toast shows a user-friendly message like “Unable to reach the AI service.”  
   - The app does not crash and you can try again once fixed.

### 3.2 Spamming messages

1. Tap send repeatedly while a request is in flight.  
2. Verify:
   - The send button disables while `viewModel.isLoading` is `true`.  
   - Only one request is in flight, no duplicate messages.

### 3.3 Message limit boundary

1. Play any lesson until you are on the last allowed message.  
2. After sending it, verify:
   - Messages remaining reaches 0.  
   - Progress row fills to the correct length.  
   - `GAME_STATE` drives you to end-of-lesson (either completed or try again).

---

## 4. Visual & Layout Checks

### 4.1 Small devices

On an iPhone SE-sized simulator:

- Scenario and “How this puzzle works” cards should not be truncated.  
- Goal and Answer Format must wrap cleanly.  
- Example question chips should be fully readable without overlapping the input.

### 4.2 Dark mode

Enable dark mode and verify:

- All text remains legible (no low-contrast combinations).  
- Cards use system or soft accent colors appropriately.  
- Progress row (🟩🟨⬛) remains clear.

---

## 5. Code-Level Tests (where feasible)

### 5.1 Tag parsing

Write unit tests for `Parser.parse(content:)` in `LLMService.swift`:

- Input strings with:
  - Both `<PROGRESS>` and `<GAME_STATE>` tags.  
  - Missing one or both tags.  
  - Tags surrounded by extra text and newlines.
- Assert that:
  - `LLMResponse.progress` and `.gameState` map correctly.  
  - Returned `content` has the tags removed and is trimmed.

### 5.2 Puzzle repository

Unit test `PuzzleRepository` using a test bundle with a small JSON fixture:

- Happy path: valid JSON → expected number of lessons.  
- Error paths: missing file and corrupted JSON → appropriate `PuzzleRepositoryError`.

### 5.3 View model

Unit test `PuzzleViewModel` with `MockLLMService`:

- `sendMessage` appends user + assistant messages as expected.  
- `turnsRemaining` and `progressHistory` update correctly.  
- Win/fail transitions populate `PuzzleResult` and open the end sheet.

---

## 6. Regression Checklist (Before Release)

Run this quick checklist before each build you ship:

1. Launches and shows tutorial correctly.  
2. Lesson 0 feels trivially approachable and teaches clarifying questions.  
3. Lesson list labels are all “Lesson …” and show skills.  
4. At least one later lesson (e.g., #5) behaves sensibly with the new prompt.  
5. End-of-lesson screen shows Skill Focus, XP, and working share sheet.  
6. No crashes or obvious visual regressions on a small simulator.

Keeping this checklist short makes it sustainable as you iterate on content and skills.