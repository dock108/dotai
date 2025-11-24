import { NextResponse } from "next/server";
import { readFileSync } from "fs";
import { join } from "path";

/**
 * API route handler for fetching a single lesson by ID.
 * 
 * Reads lesson definitions from the Swift prototype's puzzles.json file
 * and returns the full puzzle data for the specified lesson ID.
 * Used by the game page to load lesson details including scenario, goal,
 * answer format, and max turns.
 */
export async function GET(request: Request, { params }: { params: { id: string } }) {
  try {
    const puzzlesPath = join(process.cwd(), "swift-prototype/ios-app/AITrainerGame/AITrainerGame/Resources/puzzles.json");
    const puzzlesData = readFileSync(puzzlesPath, "utf-8");
    const puzzles = JSON.parse(puzzlesData);
    
    const puzzle = puzzles.find((p: any) => p.id === parseInt(params.id));

    if (!puzzle) {
      return NextResponse.json({ error: "Lesson not found" }, { status: 404 });
    }

    return NextResponse.json(puzzle);
  } catch (error) {
    console.error("Error loading puzzle:", error);
    return NextResponse.json({ error: "Failed to load lesson" }, { status: 500 });
  }
}

