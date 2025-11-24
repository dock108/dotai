import type { Metadata } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";

import "@dock108/ui/theme.css";
import "./globals.css";

import { DockFooter, DockHeader } from "@dock108/ui";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "sonner";

/**
 * Inter font configuration for consistent typography.
 * Uses CSS variable for easy theming integration.
 */
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "theory-crypto-web — dock108 strategies",
  description:
    "Describe a crypto pattern and let dock108 build the strategy spec, backtest blueprint, and alert wiring for you.",
};

/**
 * Root layout for the theory-crypto-web app.
 * 
 * Provides consistent header/footer via shared DockHeader/DockFooter components,
 * theme provider for dark/light mode switching, and toast notifications.
 * 
 * This app provides crypto strategy interpretation and backtesting, with integration
 * to the theory-engine-api backend for LLM interpretation, persistence, and backtest execution.
 */
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.variable}>
        <ThemeProvider>
          <div className="app-shell">
            <DockHeader />
            <main className="app-main">{children}</main>
            <DockFooter />
          </div>
          <Toaster position="top-right" richColors />
        </ThemeProvider>
      </body>
    </html>
  );
}

