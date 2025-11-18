import { NextResponse } from "next/server";
import { readFileSync } from "fs";
import { join } from "path";

export async function GET() {
  try {
    const puzzlesPath = join(process.cwd(), "swift-prototype/ios-app/AITrainerGame/AITrainerGame/Resources/puzzles.json");
    const puzzlesData = readFileSync(puzzlesPath, "utf-8");
    const puzzles = JSON.parse(puzzlesData);
    
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

