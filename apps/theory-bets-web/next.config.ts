import type { NextConfig } from "next";

/**
 * Next.js configuration for theory-bets-web app.
 * 
 * Transpiles @dock108/ui package to ensure compatibility with Next.js
 * build process. This is required for all apps using shared UI components.
 */
const nextConfig: NextConfig = {
  transpilePackages: ["@dock108/ui"],
};

export default nextConfig;

