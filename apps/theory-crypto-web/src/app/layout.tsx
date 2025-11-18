import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Crypto - dock108",
  description: "Evaluate your crypto theories with historical pattern analysis",
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

