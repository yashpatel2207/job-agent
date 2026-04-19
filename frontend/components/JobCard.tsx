"use client";

import Link from "next/link";
import { useState } from "react";
import { Job, triggerPrefill, updateStatus } from "@/lib/api";
import { MatchBadge } from "./MatchBadge";

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function JobCard({ job, onChange }: { job: Job; onChange?: () => void }) {
  const [busy, setBusy] = useState(false);

  const handlePrefill = async () => {
    setBusy(true);
    try {
      await triggerPrefill(job.id);
      alert("Chromium is opening on your laptop. Review the form, tweak anything, and submit.");
    } catch (e) {
      alert("Prefill failed. Is the local server running? (python -m uvicorn server:app)");
    } finally {
      setBusy(false);
    }
  };

  const handleSkip = async () => {
    if (!confirm(`Skip ${job.company}?`)) return;
    await updateStatus(job.id, "skipped");
    onChange?.();
  };

  return (
    <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-5 mb-3">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <Link href={`/job/${job.id}`} className="font-medium text-[15px] hover:underline">
              {job.title}
            </Link>
            <MatchBadge score={job.score} />
            {job.has_resume && (
              <span className="text-xs text-[hsl(var(--muted-foreground))]">· resume ready</span>
            )}
          </div>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {job.company} · {job.location || "location not specified"} · {job.ats}
          </p>
        </div>
        <span className="text-xs text-[hsl(var(--muted-foreground))] whitespace-nowrap">
          {timeAgo(job.posted_at || job.scraped_at)}
        </span>
      </div>

      {job.score_reasons.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] mb-1">Why it matched</p>
          <p className="text-sm">{job.score_reasons.join(" · ")}</p>
        </div>
      )}

      {job.red_flags.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-amber-700 dark:text-amber-400 mb-1">Heads up</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">{job.red_flags.join(" · ")}</p>
        </div>
      )}

      <div className="flex gap-2 pt-1">
        <button
          onClick={handlePrefill}
          disabled={busy || !job.has_resume}
          className="flex-1 text-sm font-medium bg-[hsl(var(--foreground))] text-[hsl(var(--background))] px-3 py-1.5 rounded-md hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {busy ? "Opening..." : "Approve and prefill"}
        </button>
        <Link
          href={`/job/${job.id}`}
          className="text-sm px-3 py-1.5 rounded-md border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))]"
        >
          View details
        </Link>
        <button
          onClick={handleSkip}
          className="text-sm px-3 py-1.5 rounded-md border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]"
        >
          Skip
        </button>
      </div>
    </div>
  );
}
