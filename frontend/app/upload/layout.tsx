import type { Metadata } from "next";
import { type ReactNode } from "react";

export const metadata: Metadata = {
  title: "New Audit | FairLens",
};

export default function UploadLayout({ children }: { children: ReactNode }) {
  return children;
}
