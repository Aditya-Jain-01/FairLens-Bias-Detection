import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";
import React from "react";

const inter = Inter({ subsets: ["latin"], variable: "--font-body" });
const spaceGrotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-display" });

export const metadata: Metadata = {
  title: "FairLens | AI Bias Detection Platform",
  description: "Detect, analyze, and remediate bias in machine learning models.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${spaceGrotesk.variable} min-h-screen text-cyan-50`}>
        <div className="grid-bg pointer-events-none fixed inset-0 opacity-40" />
        <div className="pointer-events-none fixed inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_top,rgba(80,245,225,0.16),transparent_60%)]" />

        <div className="relative mx-auto flex min-h-screen w-full max-w-[1440px] flex-col px-3 py-3 sm:px-5 sm:py-5">
          <header className="panel sticky top-3 z-50 border border-cyan-400/10 px-4 py-4 sm:px-6">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="relative flex h-12 w-12 items-center justify-center overflow-hidden rounded-2xl border border-cyan-300/20 bg-[radial-gradient(circle_at_top,rgba(105,252,235,0.22),rgba(14,34,50,0.9)_58%)] text-lg font-bold text-cyan-100 shadow-[0_12px_28px_rgba(20,184,166,0.15)]">
                  <div className="absolute inset-[1px] rounded-[15px] bg-[linear-gradient(180deg,rgba(8,20,31,0.82),rgba(8,17,27,0.96))]" />
                  <div className="absolute inset-x-2 top-1 h-4 rounded-full bg-cyan-300/20 blur-md" />
                  <span className="relative font-[family-name:var(--font-display)] tracking-[0.08em] text-cyan-200">
                    FL
                  </span>
                </div>
                <div className="space-y-0.5">
                  <div className="flex items-baseline gap-2">
                    <div className="font-[family-name:var(--font-display)] text-[1.35rem] font-semibold tracking-tight text-white">
                      Fair<span className="text-cyan-300">Lens</span>
                    </div>
                    <div className="rounded-full border border-cyan-400/10 bg-cyan-400/5 px-2 py-0.5 text-[10px] uppercase tracking-[0.22em] text-cyan-100/55">
                      Console
                    </div>
                  </div>
                  <div className="text-[11px] uppercase tracking-[0.34em] text-cyan-100/40">
                    Bias Audit Workspace
                  </div>
                </div>
              </div>

              <nav className="hidden items-center gap-2 md:flex">
                <a href="/" className="rounded-full border border-cyan-400/10 px-4 py-2 text-sm text-cyan-50/80 transition hover:border-cyan-300/30 hover:text-cyan-50">
                  Overview
                </a>
                <a href="/upload" className="rounded-full border border-cyan-400/10 px-4 py-2 text-sm text-cyan-50/80 transition hover:border-cyan-300/30 hover:text-cyan-50">
                  New Audit
                </a>
                <a href="/results/demo" className="rounded-full border border-cyan-400/10 px-4 py-2 text-sm text-cyan-50/80 transition hover:border-cyan-300/30 hover:text-cyan-50">
                  Demo Workspace
                </a>
              </nav>
            </div>
          </header>

          <main className="flex-1 px-1 py-6 sm:px-2 sm:py-8">{children}</main>

          <footer className="mt-auto px-4 pb-4 pt-3 text-center text-sm text-cyan-100/45">
            <div className="panel-soft px-6 py-4">
              FairLens workspace for hosted bias audits and downloadable compliance reports.
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
