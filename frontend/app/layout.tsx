import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import React from 'react';

const inter = Inter({ subsets: ["latin"] });

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
      <body className={`${inter.className} min-h-screen bg-gradient-to-tr from-slate-50 to-indigo-50/30 flex flex-col`}>
        <header className="sticky top-0 z-50 w-full glass border-b border-indigo-100/50">
          <div className="container mx-auto px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold text-xl">
                F
              </div>
              <span className="font-bold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-700">FairLens</span>
            </div>
            <nav className="hidden md:flex gap-6 text-sm font-medium text-slate-600">
              <a href="/" className="hover:text-indigo-600 transition-colors">Home</a>
              <a href="/upload" className="hover:text-indigo-600 transition-colors">New Audit</a>
              <a href="/results/demo" className="hover:text-indigo-600 transition-colors">View Demo</a>
            </nav>
          </div>
        </header>

        <main className="flex-1 container mx-auto px-4 py-8">
          {children}
        </main>
        
        <footer className="border-t border-slate-200 mt-auto py-6 bg-white/50">
          <div className="container mx-auto px-4 text-center text-sm text-slate-500">
            &copy; {new Date().getFullYear()} FairLens AI. All rights reserved.
          </div>
        </footer>
      </body>
    </html>
  );
}
