import { NextResponse } from "next/server";
import { z } from "zod";

const requestSchema = z.object({
  topic: z.string().min(3),
  length: z.enum(["5_15", "15_30", "30_60", "60_180", "180_600", "600_plus"]),
  sportsMode: z.boolean().default(false),
  keepEndingHidden: z.boolean().optional(),
  endingDelayChoice: z.enum(["1h", "2h", "3h", "5h", "surprise"]).optional(),
});

export async function POST(request: Request) {
  try {
    const payload = requestSchema.parse(await request.json());
    
    // Forward to theory-engine API
    const theoryEngineUrl = process.env.THEORY_ENGINE_URL || "http://localhost:8000";
    const response = await fetch(`${theoryEngineUrl}/api/theory/playlist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: payload.topic,
        domain: "playlist",
        user_tier: "free",
        length: payload.length,
        sportsMode: payload.sportsMode,
        keepEndingHidden: payload.keepEndingHidden,
        endingDelayChoice: payload.endingDelayChoice,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: "Theory engine error" }));
      throw new Error(errorData.message || "Failed to generate playlist");
    }

    const data = await response.json();
    return NextResponse.json({ ok: true, playlist: data.playlist });
  } catch (error: unknown) {
    console.error("[API] Playlist generation error:", error);

    const message =
      error instanceof z.ZodError
        ? "Please double-check your inputs."
        : error instanceof Error
        ? error.message
        : "Something went wrong.";
    const status = error instanceof z.ZodError ? 400 : 500;
    return NextResponse.json({ ok: false, message }, { status });
  }
}

