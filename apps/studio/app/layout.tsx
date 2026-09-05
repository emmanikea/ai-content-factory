import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "AI Content Factory Studio",
  description: "Internal creative production studio for AI Content Factory",
};

const groups = [
  { label: "Create", items: [["Generate", "/"]] },
  { label: "Talent & assets", items: [["Characters", "/characters"], ["Library", "/library"]] },
  { label: "Production", items: [["Projects", "/projects"], ["Jobs", "/jobs"]] },
] as const;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <Link href="/" className="brand">AI Content Factory</Link>
            {groups.map((group) => (
              <div key={group.label}>
                <div className="nav-label">{group.label}</div>
                {group.items.map(([label, href]) => (
                  <Link key={href} href={href} className="nav-link">{label}</Link>
                ))}
              </div>
            ))}
          </aside>
          <div className="shell-main">{children}</div>
        </div>
      </body>
    </html>
  );
}
