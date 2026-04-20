import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Processing Audit | FairLens",
};

export default function LoadingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
