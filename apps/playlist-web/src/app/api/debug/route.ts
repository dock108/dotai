import { NextResponse } from "next/server";
import { getRecentDebugLogs } from "@/lib/debugLogger";

export async function GET() {
  const logs = getRecentDebugLogs(10);
  return NextResponse.json({ logs, count: logs.length });
}

