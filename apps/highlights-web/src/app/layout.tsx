import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@dock108/ui/theme.css";
import "./globals.css";

import { DockFooter, DockHeader } from "@dock108/ui";

export const metadata: Metadata = {
  title: "Build Your Own Sports Highlight Show | dock108",
  description: "Tell us what games you care about. We'll build you a looping highlight show you can leave on all day.",
};

/**
 * Root layout for the highlights-web app.
 * 
 * Provides consistent header/footer via shared DockHeader/DockFooter components
 * and applies global theme styles from @dock108/ui.
 * 
 * This app allows users to build custom sports highlight playlists from natural
 * language queries, with integration to the theory-engine-api backend.
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

