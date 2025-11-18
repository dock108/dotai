import { NextResponse } from "next/server";
import { readFileSync } from "fs";
import { join } from "path";

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

