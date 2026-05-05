"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchJobs, updateStatus, Job } from "@/lib/api";
import { MatchBadge } from "@/components/MatchBadge";
import { Pagination } from "@/components/Pagination";
import { FilterSegment } from "@/components/FilterSegment";
import { lookupCompany, useCompanyMap } from "@/lib/companyDisplay";

const PAGE_SIZE = 10;

export default function AppliedPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [company, setCompany] = useState<string>("all");
  const [page, setPage] = useState(1);
  const companyMap = useCompanyMap();

  useEffect(() => {
    fetchJobs({ status: "applied" })
      .then(setJobs)
      .finally(() => setLoading(false));
  }, []);

  const handleUndo = async (id: string) => {
    if (!confirm("Move back to queue?")) return;
    await updateStatus(id, "new");
    setJobs((prev) => prev.filter((j) => j.id !== id));
  };

  const companyOptions = useMemo(() => {
    const counts = new Map<string, number>();
    for (const j of jobs) counts.set(j.company, (counts.get(j.company) ?? 0) + 1);
    return Array.from(counts.entries())
      .map(([name, count]) => ({
        name,
        display: lookupCompany(companyMap, name).display,
        count,
      }))
      .sort((a, b) => a.display.localeCompare(b.display));
  }, [jobs, companyMap]);

  const visible = useMemo(
    () => (company === "all" ? jobs : jobs.filter((j) => j.company === company)),
    [jobs, company],
  );

  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const paged = useMemo(
    () => visible.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [visible, page],
  );

  useEffect(() => {
    setPage(1);
  }, [company]);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [pageCount, page]);

  useEffect(() => {
    if (company !== "all" && !companyOptions.some((c) => c.name === company)) {
      setCompany("all");
    }
  }, [companyOptions, company]);

  const companyDisplay =
    company === "all" ? null : lookupCompany(companyMap, company).display;

  const subtitle = loading
    ? "Loading…"
    : jobs.length === 0
    ? "No applications recorded yet."
    : company === "all"
    ? `${jobs.length} ${jobs.length === 1 ? "application" : "applications"} sent — listed in submission order.`
    : `${visible.length} of ${jobs.length} ${
        jobs.length === 1 ? "application" : "applications"
      } at ${companyDisplay}.`;

  return (
    <div>
      <header className="mb-12">
        <p className="text-[13px] font-semibold text-coral tracking-snug mb-4 reveal">
          Your record
        </p>
        <h1
          className="font-semibold text-[56px] sm:text-[88px] leading-[0.98] tracking-tightest text-ink reveal"
          style={{ animationDelay: "0.05s" }}
        >
          Applied.
        </h1>
        <p
          className="mt-5 text-[18px] text-slate reveal"
          style={{ animationDelay: "0.1s" }}
        >
          {subtitle}
        </p>
      </header>

      {jobs.length > 0 && (
        <section className="mb-10 reveal" style={{ animationDelay: "0.15s" }}>
          <div className="flex items-center justify-end gap-4">
            {company !== "all" && (
              <button onClick={() => setCompany("all")} className="filter-reset">
                Reset filter
              </button>
            )}
            <FilterSegment
              label="Company"
              value={company}
              defaultValue="all"
              align="end"
              variant="pill"
              searchable
              onChange={setCompany}
              options={[
                { value: "all", label: `All companies (${jobs.length})` },
                ...companyOptions.map((c) => ({
                  value: c.name,
                  label: `${c.display} (${c.count})`,
                })),
              ]}
            />
          </div>
        </section>
      )}

      {!loading && jobs.length === 0 && (
        <div className="card p-12 text-center">
          <p className="font-semibold text-[26px] mb-3 text-ink">An empty record.</p>
          <p className="text-[15px] text-slate max-w-md mx-auto">
            Review listings in the queue and mark them as applied after submitting —
            they'll appear here for your records.
          </p>
        </div>
      )}

      {!loading && jobs.length > 0 && visible.length === 0 && (
        <div className="card p-12 text-center">
          <p className="font-semibold text-[26px] tracking-snug mb-3 text-ink">
            Nothing matches the filter.
          </p>
          <p className="text-[15px] text-slate max-w-md mx-auto">
            {jobs.length} {jobs.length === 1 ? "application is" : "applications are"} hidden by the current filter.
          </p>
          <button onClick={() => setCompany("all")} className="btn-primary mt-6">
            Reset filter
          </button>
        </div>
      )}

      {visible.length > 0 && (
        <>
          <div className="card overflow-hidden">
            {paged.map((j, i) => {
              const seq = (page - 1) * PAGE_SIZE + i + 1;
              return (
                <article
                  key={j.id}
                  className="group grid grid-cols-[36px_1fr_auto] sm:grid-cols-[60px_1fr_auto_auto] items-center gap-4 sm:gap-6 px-5 sm:px-7 py-5 border-b border-hairline last:border-b-0 hover:bg-snow-2 transition-colors duration-200 reveal"
                  style={{ animationDelay: `${0.04 + Math.min(i, 12) * 0.025}s` }}
                >
                  <span className="font-mono text-[12px] tabular-nums text-mute group-hover:text-coral transition-colors duration-200 text-right">
                    {String(seq).padStart(3, "0")}
                  </span>
                  <a
                    href={j.apply_url}
                    target="_blank"
                    rel="noreferrer"
                    className="min-w-0 block"
                  >
                    <p className="text-[13px] font-semibold text-coral mb-1 truncate">
                      {lookupCompany(companyMap, j.company).display}
                    </p>
                    <p className="font-semibold text-[17px] leading-tight tracking-snug truncate text-ink group-hover:text-coral transition-colors duration-200">
                      {j.title}
                    </p>
                    <p className="label mt-1.5">
                      {j.location || "—"}
                    </p>
                  </a>
                  <div className="hidden sm:block">
                    <MatchBadge score={j.score} size="sm" />
                  </div>
                  <button
                    onClick={() => handleUndo(j.id)}
                    className="text-[13px] text-slate hover:text-coral transition-colors px-2 font-medium"
                  >
                    Undo
                  </button>
                </article>
              );
            })}
          </div>
          <Pagination
            page={page}
            pageCount={pageCount}
            total={visible.length}
            pageSize={PAGE_SIZE}
            onPageChange={(p) => {
              setPage(p);
              requestAnimationFrame(() =>
                window.scrollTo({ top: 0, behavior: "smooth" }),
              );
            }}
          />
        </>
      )}
    </div>
  );
}
