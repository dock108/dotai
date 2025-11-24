"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ThemeProviderProps } from "next-themes/dist/types";

/**
 * Theme provider wrapper for dark/light mode switching.
 * 
 * Wraps next-themes ThemeProvider with dock108 defaults:
 * - Uses "class" attribute for theme switching (required for Tailwind)
 * - Defaults to system preference
 * - Enables automatic system theme detection
 */
export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return (
    <NextThemesProvider attribute="class" defaultTheme="system" enableSystem {...props}>
      {children}
    </NextThemesProvider>
  );
}

