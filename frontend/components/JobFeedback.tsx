"use client";

import { useEffect, useState } from "react";
import {
  JobFeedback as JobFeedbackData,
  fetchJobFeedback,
  saveJobFeedback,
  deleteFeedback,
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

export function JobFeedback({
  jobId,
  onCountChange,
}: {
  jobId: string;
  onCountChange?: (n: number) => void;
}) {
  const [items, setItems] = useState<JobFeedbackData[] | null>(null);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchJobFeedback(jobId)
      .then((rows) => {
        if (cancelled) return;
        setItems(rows);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to load feedback");
        setItems([]);
      });
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  const handleSave = async () => {
    const note = draft.trim();
    if (!note) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await saveJobFeedback(jobId, note, "drawer");
      const next = [saved, ...(items ?? [])];
      setItems(next);
      setDraft("");
      onCountChange?.(next.length);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    const prev = items ?? [];
    const next = prev.filter((r) => r.id !== id);
    setItems(next);
    onCountChange?.(next.length);
    try {
      await deleteFeedback(id);
    } catch (e) {
      // rollback
      setItems(prev);
      onCountChange?.(prev.length);
      setError(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  if (items === null) {
    return <div className="px-1 py-3 text-[13px] text-slate">Loading feedback…</div>;
  }

  return (
    <div className="px-1 py-3">
      <p className="text-[13.5px] text-slate mb-3 leading-relaxed">
        Tell the scorer what's wrong with this match (e.g. "score too high — only React,
        I want Vue too"). Notes are distilled into rules every morning and applied to
        future jobs.
      </p>

      {items.length > 0 && (
        <ul className="space-y-3 mb-4">
          {items.map((f) => (
            <li
              key={f.id}
              className="rounded-md border border-hairline bg-paper px-3 py-2.5"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-[14px] leading-relaxed text-ink/85 whitespace-pre-wrap flex-1">
                  {f.note}
                </p>
                <button
                  type="button"
                  onClick={() => handleDelete(f.id)}
                  className="text-mute hover:text-red transition-colors text-[18px] leading-none px-1"
                  aria-label="Delete feedback"
                >
                  ×
                </button>
              </div>
              <p className="label mt-1.5">
                {timeAgo(f.created_at)}
                {f.source === "skip" && " · from skip"}
                {f.score_at_time !== null && ` · score was ${f.score_at_time.toFixed(1)}`}
              </p>
            </li>
          ))}
        </ul>
      )}

      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="What's off about this match?"
        className="field min-h-[80px]"
      />

      {error && <p className="text-[12px] text-red mt-2">{error}</p>}

      <div className="flex gap-2 mt-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !draft.trim()}
          className="btn-primary"
        >
          {saving ? "Saving…" : "Save feedback"}
        </button>
      </div>
    </div>
  );
}
