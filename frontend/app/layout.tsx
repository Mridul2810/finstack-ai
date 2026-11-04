import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinStack AI - Equity Research Copilot",
  description:
    "Ask questions about public stocks, answered from SEC filings with citations.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
