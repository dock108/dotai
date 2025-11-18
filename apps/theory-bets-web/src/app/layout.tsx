import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bets - dock108",
  description: "Evaluate your betting theories with data-driven analysis",
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

