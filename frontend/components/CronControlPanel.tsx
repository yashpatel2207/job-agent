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
  if (!run) return { text: "no runs yet", className: "text-slate" };
  if (run.conclusion === "success") return { text: "succeeded", className: "text-green" };
  if (run.conclusion === "failure") return { text: "failed", className: "text-red" };
  if (run.conclusion === "cancelled") return { text: "cancelled", className: "text-slate" };
  return { text: run.conclusion || "unknown", className: "text-slate" };
}

function StatusPill({
  tone,
  label,
  pulsing = false,
}: {
  tone: "blue" | "amber" | "green";
  label: string;
  pulsing?: boolean;
}) {
  const map = {
    blue: "bg-blue/10 text-blue",
    amber: "bg-amber/10 text-amber",
    green: "bg-green/10 text-green",
  } as const;
  return (
    <span
      className={`inline-flex items-center gap-2 text-[12px] font-medium px-2.5 py-1 rounded-pill ${map[tone]} ${
        pulsing ? "animate-pulse-soft" : ""
      }`}
    >
      <span className={`block w-1.5 h-1.5 rounded-full bg-current`} />
      {label}
    </span>
  );
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
      <div className="card p-5 mb-8 text-[13px] text-slate">
        Loading pipeline status…
      </div>
    );
  }

  if (error || !status) {
    return (
      <div className="card p-5 mb-8">
        <p className="text-[13px] font-semibold text-amber mb-1">Pipeline status unavailable</p>
        <p className="text-[13px] text-slate">
          {error || "Backend not reachable. Is uvicorn running on :8000?"}
        </p>
      </div>
    );
  }

  if (status.gh_error) {
    return (
      <div className="card p-5 mb-8">
        <p className="text-[13px] font-semibold text-amber mb-1">GitHub connection issue</p>
        <p className="text-[13px] text-slate break-all">{status.gh_error}</p>
        <p className="text-[12px] text-mute mt-2">
          Check GITHUB_TOKEN and GITHUB_REPO in backend/.env, then restart the backend.
        </p>
      </div>
    );
  }

  const last = conclusionLabel(status.last_run);
  const inProgress = status.in_progress;

  return (
    <section
      className="card p-5 sm:p-6 mb-12 reveal"
      style={{ animationDelay: "0.08s" }}
    >
      <div className="flex items-center justify-between gap-6 flex-wrap">
        <div className="flex items-center gap-4 flex-wrap">
          <h2 className="text-[15px] font-semibold text-ink tracking-snug">
            Nightly pipeline
          </h2>

          {status.paused && <StatusPill tone="amber" label="Paused" />}
          {inProgress && <StatusPill tone="blue" label="Running" pulsing />}
          {!status.paused && !inProgress && <StatusPill tone="green" label="Armed" />}

          <p className="text-[13px] text-slate">
            {inProgress ? (
              <>
                Started {timeAgo(inProgress.created_at)} via {inProgress.event} ·{" "}
                <a
                  href={inProgress.html_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue hover:underline"
                >
                  view on GitHub
                </a>
              </>
            ) : status.last_run ? (
              <>
                Last run <span className={`font-medium ${last.className}`}>{last.text}</span>{" "}
                {timeAgo(status.last_run.updated_at)} ·{" "}
                <a
                  href={status.last_run.html_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue hover:underline"
                >
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
            className="btn-primary"
          >
            {inProgress ? "Already running" : acting ? "Working…" : "Run now"}
          </button>
          <button
            onClick={handleTogglePause}
            disabled={acting}
            className="btn-ghost"
          >
            {status.paused ? "Resume" : "Pause"}
          </button>
        </div>
      </div>
    </section>
  );
}
