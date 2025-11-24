import { NextResponse } from "next/server";

/**
 * Request payload for scoring a user's prompt attempt.
 */
interface ScoreRequest {
  lessonId: number;
  userMessage: string;
  history: Array<{ role: string; content: string }>;
  scenario: string;
}

/**
 * API route handler for scoring user prompts in the AI prompting game.
 * 
 * Acts as a proxy between the frontend and theory-engine-api:
 * 1. Receives user's prompt attempt and lesson context
 * 2. Forwards to POST /api/theory/evaluate
 * 3. Transforms response to game score format (verdict, confidence, reasoning, flags)
 * 
 * The game doesn't use domain routing, so domain is set to null.
 */
export async function POST(request: Request) {
  try {
    const body: ScoreRequest = await request.json();

    // Forward to theory-engine API
    // Use NEXT_PUBLIC_THEORY_ENGINE_URL for consistency with other apps
    const theoryEngineUrl = process.env.NEXT_PUBLIC_THEORY_ENGINE_URL || process.env.THEORY_ENGINE_URL || "http://localhost:8000";
    const response = await fetch(`${theoryEngineUrl}/api/theory/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: body.userMessage,
        domain: null, // Game doesn't use domain routing
        user_tier: "free",
      }),
    });

    if (!response.ok) {
      throw new Error("Theory engine API error");
    }

    const data = await response.json();

    // Transform theory engine response to game score format
    return NextResponse.json({
      verdict: data.verdict || "Processing",
      confidence: data.confidence || 0.5,
      reasoning: data.reasoning || "No reasoning provided",
      guardrail_flags: data.guardrail_flags || [],
    });
  } catch (error) {
    console.error("Score API error:", error);
    return NextResponse.json(
      {
        verdict: "Error",
        confidence: 0,
        reasoning: "Could not process your message. Please try again.",
        guardrail_flags: [],
      },
      { status: 500 }
    );
  }
}

