"use client";

import { useEffect, useState } from "react";
import { fetchJobs, updateStatus, Job } from "@/lib/api";
import { MatchBadge } from "@/components/MatchBadge";

export default function AppliedPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

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
          {loading
            ? "Loading…"
            : jobs.length === 0
            ? "No applications recorded yet."
            : `${jobs.length} ${jobs.length === 1 ? "application" : "applications"} sent — listed in submission order.`}
        </p>
      </header>

      {!loading && jobs.length === 0 && (
        <div className="card p-12 text-center">
          <p className="font-semibold text-[26px] mb-3 text-ink">An empty record.</p>
          <p className="text-[15px] text-slate max-w-md mx-auto">
            Review listings in the queue and mark them as applied after submitting —
            they'll appear here for your records.
          </p>
        </div>
      )}

      {jobs.length > 0 && (
        <div className="card overflow-hidden">
          {jobs.map((j, i) => (
            <article
              key={j.id}
              className="group grid grid-cols-[36px_1fr_auto] sm:grid-cols-[60px_1fr_auto_auto] items-center gap-4 sm:gap-6 px-5 sm:px-7 py-5 border-b border-hairline last:border-b-0 hover:bg-snow-2 transition-colors duration-200 reveal"
              style={{ animationDelay: `${0.04 + Math.min(i, 12) * 0.025}s` }}
            >
              <span className="font-mono text-[12px] tabular-nums text-mute group-hover:text-coral transition-colors duration-200 text-right">
                {String(i + 1).padStart(3, "0")}
              </span>
              <a
                href={j.apply_url}
                target="_blank"
                rel="noreferrer"
                className="min-w-0 block"
              >
                <p className="text-[13px] font-semibold text-coral mb-1 truncate">
                  {j.company}
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
          ))}
        </div>
      )}
    </div>
  );
}
