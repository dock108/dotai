import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Conspiracies - dock108",
  description: "Evaluate conspiracy theories with fact-checking and evidence analysis",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

