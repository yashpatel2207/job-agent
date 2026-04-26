"use client";

import { useEffect, useState } from "react";
import {
  CronStatus,
  fetchCronStatus,
  setCronPaused,
  triggerCronRun,
} from "@/lib/api";

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function conclusionLabel(run: CronStatus["last_run"]): { text: string; className: string } {
  if (!run) return { text: "No runs yet", className: "text-[hsl(var(--muted-foreground))]" };
  if (run.conclusion === "success") return { text: "succeeded", className: "text-emerald-600 dark:text-emerald-400" };
  if (run.conclusion === "failure") return { text: "failed", className: "text-red-600 dark:text-red-400" };
  if (run.conclusion === "cancelled") return { text: "cancelled", className: "text-[hsl(var(--muted-foreground))]" };
  return { text: run.conclusion || "unknown", className: "text-[hsl(var(--muted-foreground))]" };
}

export function CronControlPanel() {
  const [status, setStatus] = useState<CronStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [acting, setActing] = useState(false);

  const load = async () => {
    try {
      setError(null);
      const s = await fetchCronStatus();
      setStatus(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load cron status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  const handleTrigger = async () => {
    if (!confirm("Start the pipeline now? It usually takes ~1.5 hours.")) return;
    setActing(true);
    try {
      await triggerCronRun();
      setTimeout(load, 3000);
    } catch (e) {
      alert(`Failed to trigger run: ${e instanceof Error ? e.message : e}`);
    } finally {
      setActing(false);
    }
  };

  const handleTogglePause = async () => {
    if (!status) return;
    setActing(true);
    try {
      await setCronPaused(!status.paused);
      await load();
    } catch (e) {
      alert(`Failed to update pause: ${e instanceof Error ? e.message : e}`);
    } finally {
      setActing(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-4 mb-6 text-sm text-[hsl(var(--muted-foreground))]">
        Loading pipeline status...
      </div>
    );
  }

  if (error || !status) {
    return (
      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-4 mb-6 text-sm">
        <p className="text-amber-700 dark:text-amber-400">Pipeline status unavailable</p>
        <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1">
          {error || "Backend not reachable. Is uvicorn running on :8000?"}
        </p>
      </div>
    );
  }

  if (status.gh_error) {
    return (
      <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-4 mb-6 text-sm">
        <p className="text-amber-700 dark:text-amber-400">GitHub connection issue</p>
        <p className="text-xs text-[hsl(var(--muted-foreground))] mt-1 break-all">{status.gh_error}</p>
        <p className="text-xs text-[hsl(var(--muted-foreground))] mt-2">
          Check GITHUB_TOKEN and GITHUB_REPO in backend/.env, then restart the backend.
        </p>
      </div>
    );
  }

  const last = conclusionLabel(status.last_run);
  const inProgress = status.in_progress;

  return (
    <div className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-4 mb-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-sm font-medium">Nightly pipeline</h2>
            {status.paused && (
              <span className="text-xs px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300">
                paused
              </span>
            )}
            {inProgress && (
              <span className="text-xs px-2 py-0.5 rounded-md bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300">
                running now
              </span>
            )}
          </div>
          <p className="text-xs text-[hsl(var(--muted-foreground))]">
            {inProgress ? (
              <>
                Started {timeAgo(inProgress.created_at)} via {inProgress.event} —{" "}
                <a href={inProgress.html_url} target="_blank" rel="noreferrer" className="underline">
                  view on GitHub
                </a>
              </>
            ) : status.last_run ? (
              <>
                Last run <span className={last.className}>{last.text}</span> {timeAgo(status.last_run.updated_at)}
                {" · "}
                <a href={status.last_run.html_url} target="_blank" rel="noreferrer" className="underline">
                  view on GitHub
                </a>
              </>
            ) : (
              "No recent runs found"
            )}
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleTrigger}
            disabled={acting || !!inProgress}
            className="text-sm font-medium bg-[hsl(var(--foreground))] text-[hsl(var(--background))] px-3 py-1.5 rounded-md hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {inProgress ? "Already running" : acting ? "Working..." : "Run now"}
          </button>
          <button
            onClick={handleTogglePause}
            disabled={acting}
            className="text-sm px-3 py-1.5 rounded-md border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))] disabled:opacity-40"
          >
            {status.paused ? "Resume nightly" : "Pause nightly"}
          </button>
        </div>
      </div>
    </div>
  );
}
