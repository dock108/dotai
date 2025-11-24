import { NextResponse } from "next/server";
import { readFileSync } from "fs";
import { join } from "path";

/**
 * API route handler for fetching available lessons.
 * 
 * Reads lesson definitions from the Swift prototype's puzzles.json file
 * to maintain consistency between web and iOS versions. Returns a simplified
 * lesson list with metadata needed for the home page.
 */
export async function GET() {
  try {
    const puzzlesPath = join(process.cwd(), "swift-prototype/ios-app/AITrainerGame/AITrainerGame/Resources/puzzles.json");
    const puzzlesData = readFileSync(puzzlesPath, "utf-8");
    const puzzles = JSON.parse(puzzlesData);
    
    // Transform puzzle data to lesson format for the web UI
    const lessons = puzzles.map((puzzle: any) => ({
      id: puzzle.id,
      number: puzzle.number,
      title: puzzle.title,
      skill: puzzle.skill,
      skillDescription: puzzle.skillDescription,
      goal: puzzle.goal,
      scenario: puzzle.scenario,
    }));

    return NextResponse.json(lessons);
  } catch (error) {
    console.error("Error loading puzzles:", error);
    return NextResponse.json({ error: "Failed to load lessons" }, { status: 500 });
  }
}

