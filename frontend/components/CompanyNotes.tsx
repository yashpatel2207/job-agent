"use client";

import { useEffect, useState } from "react";
import {
  CompanyNoteField,
  CompanyNotes as CompanyNotesData,
  fetchCompanyNotes,
  saveCompanyNotes,
} from "@/lib/api";

type Mode = "loading" | "empty" | "read" | "edit";

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

export function CompanyNotes({
  company,
  onCountChange,
}: {
  company: string;
  onCountChange?: (n: number) => void;
}) {
  const [data, setData] = useState<CompanyNotesData | null>(null);
  const [mode, setMode] = useState<Mode>("loading");
  const [draft, setDraft] = useState<CompanyNoteField[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setMode("loading");
    fetchCompanyNotes(company)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setMode(d.fields.length === 0 ? "empty" : "read");
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to load notes");
        setMode("empty");
      });
    return () => {
      cancelled = true;
    };
  }, [company]);

  const startEdit = (seedEmpty = false) => {
    const seed: CompanyNoteField[] =
      seedEmpty || !data?.fields.length
        ? [{ question: "", answer: "" }]
        : data.fields.map((f) => ({ ...f }));
    setDraft(seed);
    setMode("edit");
  };

  const cancelEdit = () => {
    setError(null);
    setMode(data && data.fields.length > 0 ? "read" : "empty");
  };

  const handleSave = async () => {
    const cleaned = draft
      .map((f) => ({ question: f.question.trim(), answer: f.answer.trim() }))
      .filter((f) => f.question || f.answer);
    setSaving(true);
    setError(null);
    try {
      const saved = await saveCompanyNotes(company, cleaned);
      setData(saved);
      onCountChange?.(saved.fields.length);
      setMode(saved.fields.length === 0 ? "empty" : "read");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (mode === "loading") {
    return (
      <div className="px-1 py-3 text-[13px] text-slate">Loading notes…</div>
    );
  }

  if (mode === "empty") {
    return (
      <div className="px-1 py-3">
        <p className="text-[13.5px] text-slate mb-3 leading-relaxed">
          Save reusable notes for any future {company} role — they'll appear
          here automatically next time.
        </p>
        <button
          type="button"
          onClick={() => startEdit(true)}
          className="btn-ghost"
        >
          + Add notes
        </button>
        {error && (
          <p className="text-[12px] text-red mt-3">{error}</p>
        )}
      </div>
    );
  }

  if (mode === "read" && data) {
    return (
      <div className="px-1 py-3">
        <div className="flex items-baseline justify-between gap-3 mb-3">
          <p className="label">Notes for {company}</p>
          <button
            type="button"
            onClick={() => startEdit(false)}
            className="text-[13px] font-medium text-blue hover:underline"
          >
            Edit
          </button>
        </div>
        <dl className="space-y-4">
          {data.fields.map((f, i) => (
            <div key={i}>
              <dt className="text-[13.5px] font-semibold text-ink mb-1">
                {f.question || <span className="text-mute italic">untitled</span>}
              </dt>
              <dd className="text-[14px] leading-relaxed text-ink/85 whitespace-pre-wrap">
                {f.answer || <span className="text-mute italic">empty</span>}
              </dd>
            </div>
          ))}
        </dl>
        {data.updated_at && (
          <p className="label mt-4">Updated {timeAgo(data.updated_at)}</p>
        )}
      </div>
    );
  }

  // edit mode
  return (
    <div className="px-1 py-3">
      <div className="flex items-baseline justify-between gap-3 mb-4">
        <p className="label">Editing notes for {company}</p>
      </div>

      <div className="space-y-5">
        {draft.map((f, i) => (
          <div key={i} className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <input
                type="text"
                value={f.question}
                onChange={(e) =>
                  setDraft(
                    draft.map((row, j) =>
                      j === i ? { ...row, question: e.target.value } : row,
                    ),
                  )
                }
                placeholder="Question or label"
                className="field flex-1 !py-2 !text-[13.5px] font-semibold"
              />
              <button
                type="button"
                onClick={() => setDraft(draft.filter((_, j) => j !== i))}
                className="text-mute hover:text-red transition-colors text-[18px] leading-none px-2"
                aria-label="Remove field"
              >
                ×
              </button>
            </div>
            <textarea
              value={f.answer}
              onChange={(e) =>
                setDraft(
                  draft.map((row, j) =>
                    j === i ? { ...row, answer: e.target.value } : row,
                  ),
                )
              }
              placeholder="Your answer or notes…"
              className="field min-h-[88px]"
            />
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={() =>
          setDraft([...draft, { question: "", answer: "" }])
        }
        className="text-[13px] font-medium text-blue hover:underline mt-4"
      >
        + Add another field
      </button>

      {error && <p className="text-[12px] text-red mt-3">{error}</p>}

      <div className="flex gap-2 mt-5">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="btn-primary"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          type="button"
          onClick={cancelEdit}
          disabled={saving}
          className="btn-ghost"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
