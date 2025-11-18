import { NextResponse } from "next/server";
import { z } from "zod";
import { generatePlaylist } from "@/lib/playlistService";

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
    const playlist = await generatePlaylist(payload);
    return NextResponse.json({ ok: true, playlist });
  } catch (error: unknown) {
    // Log the full error for debugging
    console.error("[API] Playlist generation error:", error);
    if (error instanceof Error) {
      console.error("[API] Error stack:", error.stack);
    }

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

