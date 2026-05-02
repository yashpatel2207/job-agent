"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchJobs, fetchStats, Job, Stats } from "@/lib/api";
import { JobCard } from "@/components/JobCard";
import { StatCard } from "@/components/StatCard";
import { CronControlPanel } from "@/components/CronControlPanel";
import { TierNav, TierNavItem } from "@/components/TierNav";
import { Pagination } from "@/components/Pagination";

type Age = "all" | "7d" | "14d" | "older";

const PAGE_SIZE = 10;
const TIER_IDS = {
  strong: "tier-strong",
  worth: "tier-worth",
  lower: "tier-lower",
} as const;

function scrollToSection(id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  const top = el.getBoundingClientRect().top + window.scrollY - 120;
  window.scrollTo({ top, behavior: "smooth" });
}

const AGE_LABEL: Record<Age, string> = {
  all: "any time",
  "7d": "the last 7 days",
  "14d": "the last 14 days",
  older: "more than 14 days ago",
};

export default function QueuePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [minScore, setMinScore] = useState(7.0);
  const [age, setAge] = useState<Age>("7d");
  const [company, setCompany] = useState<string>("all");
  const [query, setQuery] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [j, s] = await Promise.all([
        fetchJobs({ status: "new", min_score: minScore }),
        fetchStats(),
      ]);
      setJobs(j);
      setStats(s);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [minScore]);

  const ageMatches = (j: Job) => {
    if (age === "all") return true;
    const iso = j.posted_at || j.scraped_at;
    if (!iso) return false;
    const days = (Date.now() - new Date(iso).getTime()) / 86400000;
    if (age === "7d") return days <= 7;
    if (age === "14d") return days <= 14;
    return days > 14;
  };

  const ageFiltered = useMemo(() => jobs.filter(ageMatches), [jobs, age]);
  const companyOptions = useMemo(() => {
    const counts = new Map<string, number>();
    for (const j of ageFiltered) counts.set(j.company, (counts.get(j.company) ?? 0) + 1);
    return Array.from(counts.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([name, count]) => ({ name, count }));
  }, [ageFiltered]);

  useEffect(() => {
    if (company !== "all" && !companyOptions.some((c) => c.name === company)) {
      setCompany("all");
    }
  }, [companyOptions, company]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return ageFiltered.filter((j) => {
      if (company !== "all" && j.company !== company) return false;
      if (q && !j.title.toLowerCase().includes(q) && !j.company.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [ageFiltered, company, query]);

  const topTier = useMemo(() => visible.filter((j) => (j.score ?? 0) >= 8.0), [visible]);
  const midTier = useMemo(
    () => visible.filter((j) => (j.score ?? 0) >= 7.0 && (j.score ?? 0) < 8.0),
    [visible],
  );
  const lowTier = useMemo(() => visible.filter((j) => (j.score ?? 0) < 7.0), [visible]);

  const [strongPage, setStrongPage] = useState(1);
  const [worthPage, setWorthPage] = useState(1);
  const [lowerPage, setLowerPage] = useState(1);

  // Reset all tier pagination when the visible set shifts
  useEffect(() => {
    setStrongPage(1);
    setWorthPage(1);
    setLowerPage(1);
  }, [minScore, age, company, query]);

  // Clamp pages if a tier shrinks below the current page
  useEffect(() => {
    const max = Math.max(1, Math.ceil(topTier.length / PAGE_SIZE));
    if (strongPage > max) setStrongPage(max);
  }, [topTier.length, strongPage]);
  useEffect(() => {
    const max = Math.max(1, Math.ceil(midTier.length / PAGE_SIZE));
    if (worthPage > max) setWorthPage(max);
  }, [midTier.length, worthPage]);
  useEffect(() => {
    const max = Math.max(1, Math.ceil(lowTier.length / PAGE_SIZE));
    if (lowerPage > max) setLowerPage(max);
  }, [lowTier.length, lowerPage]);

  const topPaged = useMemo(
    () => topTier.slice((strongPage - 1) * PAGE_SIZE, strongPage * PAGE_SIZE),
    [topTier, strongPage],
  );
  const midPaged = useMemo(
    () => midTier.slice((worthPage - 1) * PAGE_SIZE, worthPage * PAGE_SIZE),
    [midTier, worthPage],
  );
  const lowPaged = useMemo(
    () => lowTier.slice((lowerPage - 1) * PAGE_SIZE, lowerPage * PAGE_SIZE),
    [lowTier, lowerPage],
  );

  const tierNavItems: TierNavItem[] = useMemo(() => {
    const items: TierNavItem[] = [];
    if (topTier.length > 0)
      items.push({ id: TIER_IDS.strong, label: "Strong", count: topTier.length, accent: "teal" });
    if (midTier.length > 0)
      items.push({ id: TIER_IDS.worth, label: "Worth reviewing", count: midTier.length, accent: "amber" });
    if (lowTier.length > 0)
      items.push({ id: TIER_IDS.lower, label: "Lower", count: lowTier.length, accent: "slate" });
    return items;
  }, [topTier.length, midTier.length, lowTier.length]);

  const handlePageChange = (
    setter: (n: number) => void,
    anchorId: string,
    next: number,
  ) => {
    setter(next);
    // wait for DOM update before scrolling
    requestAnimationFrame(() => scrollToSection(anchorId));
  };

  const filtersActive =
    age !== "7d" || company !== "all" || query.trim() !== "";

  const clearFilters = () => {
    setAge("7d");
    setCompany("all");
    setQuery("");
  };

  const subtitle = loading
    ? "Loading today's listings…"
    : `${visible.length} ${visible.length === 1 ? "match" : "matches"}` +
      ` at or above ${minScore.toFixed(1)}, posted ${AGE_LABEL[age]}` +
      (company !== "all" ? `, at ${company}` : "") +
      (query.trim() ? `, matching "${query.trim()}"` : "") +
      ".";

  return (
    <div>
      {/* Hero */}
      <header className="mb-14">
        <p className="text-[13px] font-semibold text-teal tracking-snug mb-4 reveal">
          Daily briefing
        </p>
        <h1
          className="font-semibold text-[56px] sm:text-[88px] leading-[0.98] tracking-tightest text-ink reveal"
          style={{ animationDelay: "0.05s" }}
        >
          Today's <span className="text-teal">queue.</span>
        </h1>
        <p
          className="mt-5 text-[18px] sm:text-[19px] leading-relaxed text-slate max-w-2xl reveal"
          style={{ animationDelay: "0.1s" }}
        >
          {subtitle}
        </p>
      </header>

      <CronControlPanel />

      {stats && (
        <section
          className="card grid grid-cols-2 md:grid-cols-4 mb-10 reveal overflow-hidden"
          style={{ animationDelay: "0.12s" }}
        >
          <StatCard label="In queue" value={stats.new.toLocaleString()} />
          <StatCard label="Ready to review" value={stats.ready_to_review.toLocaleString()} />
          <StatCard label="Avg score" value={stats.avg_score.toFixed(1)} accent />
          <StatCard label="Applied (total)" value={stats.applied.toLocaleString()} />
        </section>
      )}

      {/* Filter bar */}
      <section
        className="card p-5 sm:p-6 mb-12 reveal"
        style={{ animationDelay: "0.15s" }}
      >
        <div className="grid grid-cols-1 md:grid-cols-[1.6fr_auto_auto_1fr] gap-4 md:gap-5 items-end">
          <FilterCell label="Search">
            <div className="relative">
              <span className="pointer-events-none absolute left-5 top-1/2 -translate-y-1/2 text-mute">
                <SearchIcon />
              </span>
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Title or company"
                className="search pl-11"
              />
              {query && (
                <button
                  onClick={() => setQuery("")}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[12px] text-slate hover:text-ink transition-colors"
                  aria-label="Clear search"
                >
                  Clear
                </button>
              )}
            </div>
          </FilterCell>

          <FilterCell label="Min score">
            <SelectControl
              value={String(minScore)}
              onChange={(v) => setMinScore(parseFloat(v))}
              options={[
                { value: "0", label: "All" },
                { value: "5", label: "5.0+" },
                { value: "7", label: "7.0+" },
                { value: "8", label: "8.0+" },
              ]}
            />
          </FilterCell>

          <FilterCell label="Posted">
            <SelectControl
              value={age}
              onChange={(v) => setAge(v as Age)}
              options={[
                { value: "all", label: "Any time" },
                { value: "7d", label: "Last 7 days" },
                { value: "14d", label: "Last 14 days" },
                { value: "older", label: "Older than 14 days" },
              ]}
            />
          </FilterCell>

          <FilterCell label={`Company · ${companyOptions.length}`}>
            <SelectControl
              value={company}
              onChange={setCompany}
              options={[
                { value: "all", label: `All companies (${ageFiltered.length})` },
                ...companyOptions.map((c) => ({
                  value: c.name,
                  label: `${c.name} (${c.count})`,
                })),
              ]}
            />
          </FilterCell>
        </div>
        {filtersActive && (
          <div className="mt-4 pt-4 border-t border-hairline flex justify-end">
            <button
              onClick={clearFilters}
              className="text-[13px] text-blue hover:underline font-medium"
            >
              Reset filters
            </button>
          </div>
        )}
      </section>

      {loading && <p className="text-[14px] text-slate py-12 text-center">Loading listings…</p>}

      {!loading && visible.length === 0 && (
        <div className="card p-12 text-center">
          <p className="font-semibold text-[26px] tracking-snug mb-3 text-ink">
            {jobs.length === 0 ? "Nothing in the queue." : "Nothing matches the filters."}
          </p>
          <p className="text-[15px] text-slate max-w-md mx-auto">
            {jobs.length === 0
              ? "Either today's scrape hasn't run yet, or nothing matched your criteria. Try lowering the minimum score, or wait for tomorrow's edition."
              : `${jobs.length} ${jobs.length === 1 ? "listing is" : "listings are"} hidden by the current filters. Try widening the posting window, clearing the company, or emptying the search.`}
          </p>
          {filtersActive && (
            <button onClick={clearFilters} className="btn-primary mt-6">
              Reset filters
            </button>
          )}
        </div>
      )}

      {!loading && tierNavItems.length > 0 && <TierNav tiers={tierNavItems} />}

      {topTier.length > 0 && (
        <Section
          id={TIER_IDS.strong}
          title="Strong matches"
          accent="text-teal"
          meta={`${topTier.length} · 8.0+`}
        >
          {topPaged.map((j, i) => (
            <JobCard key={j.id} job={j} index={i} onChange={load} />
          ))}
          <Pagination
            page={strongPage}
            pageCount={Math.max(1, Math.ceil(topTier.length / PAGE_SIZE))}
            total={topTier.length}
            pageSize={PAGE_SIZE}
            onPageChange={(p) => handlePageChange(setStrongPage, TIER_IDS.strong, p)}
          />
        </Section>
      )}

      {midTier.length > 0 && (
        <Section
          id={TIER_IDS.worth}
          title="Worth reviewing"
          accent="text-amber"
          meta={`${midTier.length} · 7.0 – 7.9`}
        >
          {midPaged.map((j, i) => (
            <JobCard key={j.id} job={j} index={i} onChange={load} />
          ))}
          <Pagination
            page={worthPage}
            pageCount={Math.max(1, Math.ceil(midTier.length / PAGE_SIZE))}
            total={midTier.length}
            pageSize={PAGE_SIZE}
            onPageChange={(p) => handlePageChange(setWorthPage, TIER_IDS.worth, p)}
          />
        </Section>
      )}

      {lowTier.length > 0 && (
        <Section
          id={TIER_IDS.lower}
          title="Lower matches"
          accent="text-slate"
          meta={`${lowTier.length}`}
        >
          {lowPaged.map((j, i) => (
            <JobCard key={j.id} job={j} index={i} onChange={load} />
          ))}
          <Pagination
            page={lowerPage}
            pageCount={Math.max(1, Math.ceil(lowTier.length / PAGE_SIZE))}
            total={lowTier.length}
            pageSize={PAGE_SIZE}
            onPageChange={(p) => handlePageChange(setLowerPage, TIER_IDS.lower, p)}
          />
        </Section>
      )}
    </div>
  );
}

function FilterCell({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 min-w-0">
      <span className="label">{label}</span>
      {children}
    </div>
  );
}

function SelectControl({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="select w-full"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-slate">
        <ChevronIcon />
      </span>
    </div>
  );
}

function Section({
  id,
  title,
  accent,
  meta,
  children,
}: {
  id?: string;
  title: string;
  accent: string;
  meta: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="mb-14 scroll-mt-32">
      <div className="flex items-baseline justify-between mb-5">
        <h2 className={`font-semibold text-[26px] tracking-snug ${accent}`}>
          {title}
        </h2>
        <span className="label">{meta}</span>
      </div>
      {children}
    </section>
  );
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M11 11L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg width="10" height="6" viewBox="0 0 10 6" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
