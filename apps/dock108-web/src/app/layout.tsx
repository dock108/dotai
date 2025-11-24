import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@dock108/ui/theme.css";
import "./globals.css";

import { DockFooter, DockHeader } from "@dock108/ui";

export const metadata: Metadata = {
  title: "Dock108 — Theory Surface Hub",
  description: "One launchpad for every Dock108 experiment.",
};

/**
 * Root layout for the dock108 landing portal.
 * 
 * Provides consistent header/footer via shared DockHeader/DockFooter components
 * and applies global theme styles from @dock108/ui.
 * 
 * This is the main entry point that links to all other dock108 applications.
 */
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="hub-shell">
          <DockHeader ctaHref={null} />
          <main className="hub-main">{children}</main>
          <DockFooter />
        </div>
      </body>
    </html>
  );
}

