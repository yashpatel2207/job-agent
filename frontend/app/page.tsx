"use client";

import { useEffect, useState } from "react";
import { fetchJobs, fetchStats, Job, Stats } from "@/lib/api";
import { JobCard } from "@/components/JobCard";
import { StatCard } from "@/components/StatCard";
import { CronControlPanel } from "@/components/CronControlPanel";

export default function QueuePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [minScore, setMinScore] = useState(7.0);

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
  }, [minScore]);

  const topTier = jobs.filter((j) => (j.score ?? 0) >= 8.0);
  const midTier = jobs.filter((j) => (j.score ?? 0) >= 7.0 && (j.score ?? 0) < 8.0);
  const lowTier = jobs.filter((j) => (j.score ?? 0) < 7.0);

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6">
        <div>
          <h1 className="text-2xl font-medium mb-1">Today's queue</h1>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            {loading
              ? "Loading..."
              : `${jobs.length} ${jobs.length === 1 ? "match" : "matches"} at or above score ${minScore.toFixed(1)}`}
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <label className="text-[hsl(var(--muted-foreground))]">Min score</label>
          <select
            value={minScore}
            onChange={(e) => setMinScore(parseFloat(e.target.value))}
            className="border border-[hsl(var(--border))] rounded-md px-2 py-1 bg-[hsl(var(--card))]"
          >
            <option value={0}>All</option>
            <option value={5}>5.0+</option>
            <option value={7}>7.0+</option>
            <option value={8}>8.0+</option>
          </select>
        </div>
      </div>

      <CronControlPanel />

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          <StatCard label="In queue" value={stats.new} />
          <StatCard label="Ready to review" value={stats.ready_to_review} />
          <StatCard label="Avg score" value={stats.avg_score.toFixed(1)} />
          <StatCard label="Applied (total)" value={stats.applied} />
        </div>
      )}

      {loading && <p className="text-sm text-[hsl(var(--muted-foreground))]">Loading jobs...</p>}

      {!loading && jobs.length === 0 && (
        <div className="bg-[hsl(var(--muted))] rounded-xl p-8 text-center">
          <p className="font-medium mb-1">Nothing in the queue</p>
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            Either today's scrape hasn't run yet, or nothing matched your criteria. Try lowering the minimum score.
          </p>
        </div>
      )}

      {topTier.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-medium text-[hsl(var(--muted-foreground))] mb-3">Strong matches (8.0+)</h2>
          {topTier.map((j) => (
            <JobCard key={j.id} job={j} onChange={load} />
          ))}
        </section>
      )}

      {midTier.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-medium text-[hsl(var(--muted-foreground))] mb-3">Worth reviewing (7.0 - 7.9)</h2>
          {midTier.map((j) => (
            <JobCard key={j.id} job={j} onChange={load} />
          ))}
        </section>
      )}

      {lowTier.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-[hsl(var(--muted-foreground))] mb-3">Lower matches</h2>
          {lowTier.map((j) => (
            <JobCard key={j.id} job={j} onChange={load} />
          ))}
        </section>
      )}
    </div>
  );
}
