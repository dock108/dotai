import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@dock108/ui/theme.css";
import "./globals.css";

import { DockFooter, DockHeader } from "@dock108/ui";

export const metadata: Metadata = {
  title: "AI-Curated YouTube Playlists | dock108",
  description: "Topic, length, and preferences. We handle the curation.",
};

/**
 * Root layout for the playlist-web app.
 * 
 * Provides consistent header/footer via shared DockHeader/DockFooter components
 * and applies global theme styles from @dock108/ui.
 * 
 * This app allows users to generate AI-curated YouTube playlists from natural
 * language topics, with integration to the theory-engine-api backend.
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
