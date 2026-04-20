import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Audit Results | FairLens",
};

export default function ResultsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
