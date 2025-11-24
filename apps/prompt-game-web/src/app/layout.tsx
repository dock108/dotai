import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@dock108/ui/theme.css";
import "./globals.css";

import { DockFooter, DockHeader } from "@dock108/ui";

export const metadata: Metadata = {
  title: "AI Prompting Game - dock108",
  description: "Learn to prompt AI effectively through interactive lessons",
};

/**
 * Root layout for the prompt-game-web app.
 * 
 * Provides consistent header/footer via shared DockHeader/DockFooter components
 * and applies global theme styles from @dock108/ui.
 * 
 * This app provides an interactive game for learning effective AI prompting
 * through structured lessons, with integration to the theory-engine-api backend
 * for prompt evaluation and scoring.
 */
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <DockHeader />
          <main className="app-main">{children}</main>
          <DockFooter />
        </div>
      </body>
    </html>
  );
}

