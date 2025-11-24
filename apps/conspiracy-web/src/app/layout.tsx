import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@dock108/ui/theme.css";
import "./globals.css";

import { DockFooter, DockHeader } from "@dock108/ui";

export const metadata: Metadata = {
  title: "Conspiracies - dock108",
  description: "Evaluate conspiracy theories with fact-checking and evidence analysis",
};

/**
 * Root layout for the conspiracy theory evaluation app.
 * 
 * Provides consistent header/footer via shared DockHeader/DockFooter components
 * and applies global theme styles from @dock108/ui.
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

