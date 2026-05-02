"use client";

import { useEffect, useState } from "react";
import { fetchJobs, updateStatus, Job } from "@/lib/api";
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

  const handleUndo = async (id: string) => {
    if (!confirm("Move back to queue?")) return;
    await updateStatus(id, "new");
    setJobs((prev) => prev.filter((j) => j.id !== id));
  };

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
          <div
            key={j.id}
            className="flex items-center gap-3 bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-lg px-4 py-3"
          >
            <Link href={`/job/${j.id}`} className="flex-1 min-w-0 hover:opacity-80">
              <p className="font-medium text-sm truncate">{j.title}</p>
              <p className="text-xs text-[hsl(var(--muted-foreground))]">
                {j.company} · {j.location || "—"}
              </p>
            </Link>
            <MatchBadge score={j.score} />
            <button
              onClick={() => handleUndo(j.id)}
              className="text-xs px-2.5 py-1 rounded-md border border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))]"
            >
              Undo
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
