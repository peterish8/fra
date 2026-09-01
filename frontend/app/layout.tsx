import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Financial Research Agent",
  description: "An evidence-first workspace for company research.",
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
