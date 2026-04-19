import "./globals.css";
import Link from "next/link";

export const metadata = {
  title: "Job Agent",
  description: "Daily queue of tailored job applications",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-[hsl(var(--border))]">
            <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
              <Link href="/" className="font-medium text-[15px]">
                Job Agent
              </Link>
              <nav className="flex items-center gap-6 text-sm text-[hsl(var(--muted-foreground))]">
                <Link href="/" className="hover:text-[hsl(var(--foreground))]">
                  Queue
                </Link>
                <Link href="/applied" className="hover:text-[hsl(var(--foreground))]">
                  Applied
                </Link>
                <Link href="/profile" className="hover:text-[hsl(var(--foreground))]">
                  Profile
                </Link>
              </nav>
            </div>
          </header>
          <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
