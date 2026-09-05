import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "AI Content Factory Studio",
  description: "Internal generation console for AI Content Factory",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "Arial, Helvetica, sans-serif", background: "#f7f7f5", color: "#111" }}>
        {children}
      </body>
    </html>
  );
}
