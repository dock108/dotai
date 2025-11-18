import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stocks - dock108",
  description: "Evaluate your stock theories with fundamentals and historical analysis",
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

