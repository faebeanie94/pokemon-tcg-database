import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Card Catalog",
  description:
    "Multi-game card lookup and matching for card grading.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[var(--surface)] text-[var(--text)] antialiased">
        {children}
      </body>
    </html>
  );
}
