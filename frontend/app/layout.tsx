import type { Metadata } from "next";

import { DevAuthGate } from "@/components/dev/dev-auth-gate";
import { GlobalAppShell } from "@/components/layout/global-app-shell";

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
      <body><DevAuthGate><GlobalAppShell>{children}</GlobalAppShell></DevAuthGate></body>
    </html>
  );
}
