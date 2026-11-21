import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AIGREE: T&C Analyzer",
  description: "Understand Terms & Conditions before you agree.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans">{children}</body>
    </html>
  );
}
