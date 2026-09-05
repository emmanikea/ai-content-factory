import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "AI Content Factory Studio",
  description: "Internal generation console for AI Content Factory",
};

const links = [
  ["Generate", "/"],
  ["Characters", "/characters"],
  ["Projects", "/projects"],
  ["Jobs", "/jobs"],
] as const;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "Arial, Helvetica, sans-serif", background: "#f7f7f5", color: "#111" }}>
        <header style={{ borderBottom: "1px solid #e2e2dd", background: "white" }}>
          <div style={{ maxWidth: 1120, margin: "0 auto", padding: "14px 24px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 24 }}>
            <Link href="/" style={{ color: "#111", fontWeight: 800, textDecoration: "none", letterSpacing: -0.2 }}>
              AI Content Factory
            </Link>
            <nav style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
              {links.map(([label, href]) => (
                <Link key={href} href={href} style={{ color: "#444", textDecoration: "none", fontSize: 14 }}>
                  {label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
