import type { Metadata } from "next";
import { type ReactNode } from "react";

export const metadata: Metadata = {
  title: "Processing Audit | FairLens",
};

export default function LoadingLayout({ children }: { children: ReactNode }) {
  return children;
}
