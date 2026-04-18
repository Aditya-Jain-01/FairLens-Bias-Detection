import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "New Audit | FairLens",
};

export default function UploadLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
