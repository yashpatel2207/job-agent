import "./globals.css";
import Link from "next/link";
import { Manrope, JetBrains_Mono } from "next/font/google";

const sans = Manrope({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
  weight: ["300", "400", "500", "600", "700", "800"],
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["400", "500"],
});

export const metadata = {
  title: "Job Agent",
  description: "A daily, ranked queue of jobs worth applying to.",
};

function todayLong() {
  return new Date().toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body>
        <div className="relative">
          <header className="nav-bar">
            <div className="max-w-6xl mx-auto px-6 sm:px-10 h-14 flex items-center justify-between gap-6">
              <Link href="/" className="flex items-baseline gap-3">
                <span className="text-[17px] font-semibold tracking-snug text-ink">
                  Job Agent
                </span>
              </Link>
              <nav className="flex items-center gap-7">
                <Link href="/" className="nav-link">Queue</Link>
                <Link href="/applied" className="nav-link">Applied</Link>
                <Link href="/profile" className="nav-link">Profile</Link>
              </nav>
              <span className="hidden md:inline text-[12px] text-slate font-medium">
                {todayLong()}
              </span>
            </div>
          </header>

          <main className="max-w-6xl mx-auto px-6 sm:px-10 py-12 sm:py-16">{children}</main>

          <footer className="max-w-6xl mx-auto px-6 sm:px-10 py-10 mt-20 border-t border-hairline">
            <div className="flex flex-wrap justify-between items-center gap-4 text-[12px] text-slate">
              <span>Job Agent · Local instance</span>
              <span>Curated nightly · Apply manually · No auto-submit</span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
