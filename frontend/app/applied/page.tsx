"use client";

import { useEffect, useState } from "react";
import { fetchJobs, Job } from "@/lib/api";
import { MatchBadge } from "@/components/MatchBadge";
import Link from "next/link";

export default function AppliedPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchJobs({ status: "applied" })
      .then(setJobs)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-medium mb-1">Applied</h1>
      <p className="text-sm text-[hsl(var(--muted-foreground))] mb-6">
        {loading ? "Loading..." : `${jobs.length} applications sent`}
      </p>

      {!loading && jobs.length === 0 && (
        <div className="bg-[hsl(var(--muted))] rounded-xl p-8 text-center text-sm text-[hsl(var(--muted-foreground))]">
          Nothing yet. Review some jobs and mark them as applied after submitting.
        </div>
      )}

      <div className="space-y-2">
        {jobs.map((j) => (
          <Link
            key={j.id}
            href={`/job/${j.id}`}
            className="block bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg px-4 py-3 hover:bg-[hsl(var(--muted))]"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="font-medium text-sm truncate">{j.title}</p>
                <p className="text-xs text-[hsl(var(--muted-foreground))]">
                  {j.company} · {j.location || "—"}
                </p>
              </div>
              <MatchBadge score={j.score} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
