import type { Metadata } from "next";
import { type ReactNode } from "react";

export const metadata: Metadata = {
  title: "Audit Results | FairLens",
};

export default function ResultsLayout({ children }: { children: ReactNode }) {
  return children;
}
