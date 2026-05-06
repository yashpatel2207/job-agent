"use client";

import { useEffect, useState } from "react";
import {
  Job,
  fetchCompanyNotes,
  fetchJobFeedback,
  saveJobFeedback,
  updateStatus,
} from "@/lib/api";
import { MatchBadge } from "./MatchBadge";
import { CompanyNotes } from "./CompanyNotes";
import { JobFeedback } from "./JobFeedback";
import { SkipFeedbackModal } from "./SkipFeedbackModal";

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "Just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function JobCard({
  job,
  index,
  onChange,
  companyDisplay,
  companyCareersUrl,
}: {
  job: Job;
  index?: number;
  onChange?: () => void;
  companyDisplay?: string;
  companyCareersUrl?: string | null;
}) {
  const [expanded, setExpanded] = useState(false);
  const [noteCount, setNoteCount] = useState<number | null>(null);
  const [feedbackExpanded, setFeedbackExpanded] = useState(false);
  const [feedbackCount, setFeedbackCount] = useState<number | null>(null);
  const [skipModalOpen, setSkipModalOpen] = useState(false);
  const [marking, setMarking] = useState(false);

  // Prefetch the note count so the chip shows "Notes for Vercel · 2"
  // without forcing the user to expand. One GET per card on mount.
  useEffect(() => {
    let cancelled = false;
    fetchCompanyNotes(job.company)
      .then((d) => {
        if (!cancelled) setNoteCount(d.fields.length);
      })
      .catch(() => {
        if (!cancelled) setNoteCount(0);
      });
    return () => {
      cancelled = true;
    };
  }, [job.company]);

  useEffect(() => {
    let cancelled = false;
    fetchJobFeedback(job.id)
      .then((rows) => {
        if (!cancelled) setFeedbackCount(rows.length);
      })
      .catch(() => {
        if (!cancelled) setFeedbackCount(0);
      });
    return () => {
      cancelled = true;
    };
  }, [job.id]);

  const handleSkip = () => setSkipModalOpen(true);

  const confirmSkip = async (reason: string) => {
    try {
      if (reason) {
        await saveJobFeedback(job.id, reason, "skip");
      }
      await updateStatus(job.id, "skipped");
      setSkipModalOpen(false);
      onChange?.();
    } catch (e) {
      alert(`Failed to skip: ${e instanceof Error ? e.message : e}`);
    }
  };

  const handleApply = async () => {
    setMarking(true);
    try {
      await updateStatus(job.id, "applied");
      onChange?.();
    } catch (e) {
      alert(`Failed to mark as applied: ${e instanceof Error ? e.message : e}`);
    } finally {
      setMarking(false);
    }
  };

  const ago = timeAgo(job.posted_at || job.scraped_at);

  // Subtle tier surface tint
  const score = job.score ?? 0;
  const tierBg =
    score >= 8.0 ? "bg-mint" : score >= 7.0 ? "bg-butter" : "bg-paper";
  const tierAccent =
    score >= 8.0
      ? "before:bg-teal"
      : score >= 7.0
      ? "before:bg-amber"
      : "before:bg-transparent";

  const notesLabel =
    noteCount && noteCount > 0
      ? `Notes for ${job.company} · ${noteCount}`
      : `Notes for ${job.company}`;

  const feedbackLabel =
    feedbackCount && feedbackCount > 0
      ? `Feedback · ${feedbackCount}`
      : "Feedback";

  return (
    <article
      className={`card card-hover ${tierBg} p-6 sm:p-7 mb-4 reveal relative overflow-hidden before:content-[''] before:absolute before:left-0 before:top-0 before:bottom-0 before:w-[3px] ${tierAccent}`}
      style={{ animationDelay: `${0.04 + Math.min(index ?? 0, 12) * 0.03}s` }}
    >
      <div className="flex items-start justify-between gap-6 mb-3">
        <div className="min-w-0 flex-1">
          <p className="text-[14px] font-semibold text-blue tracking-snug mb-1.5 truncate">
            {companyCareersUrl ? (
              <a
                href={companyCareersUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:underline"
              >
                {companyDisplay ?? job.company}
              </a>
            ) : (
              companyDisplay ?? job.company
            )}
          </p>
          <h3 className="font-semibold text-[22px] sm:text-[24px] leading-[1.2] tracking-snug text-ink">
            {job.title}
          </h3>
          <p className="label mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
            <span>{job.location || "Remote"}</span>
            <span className="text-mute">·</span>
            <span>{job.ats}</span>
            <span className="text-mute">·</span>
            <span>{ago}</span>
          </p>
        </div>
        <MatchBadge score={job.score} />
      </div>

      {job.score_reasons.length > 0 && (
        <div className="mt-5 pt-5 border-t border-hairline">
          <p className="label mb-2">Why it matched</p>
          <p className="text-[14.5px] leading-relaxed text-ink/85">
            {job.score_reasons.map((r, i) => (
              <span key={i}>
                {i > 0 && <span className="text-mute mx-1.5">·</span>}
                {r}
              </span>
            ))}
          </p>
        </div>
      )}

      {job.red_flags.length > 0 && (
        <div className="mt-3">
          <p className="label mb-1.5 text-amber">Heads up</p>
          <p className="text-[13.5px] leading-relaxed text-slate">
            {job.red_flags.join(" · ")}
          </p>
        </div>
      )}

      <div className="flex flex-wrap gap-2 mt-6 items-center">
        <a
          href={job.apply_url}
          target="_blank"
          rel="noreferrer"
          className="btn-ghost"
        >
          ↗ Open posting
        </a>
        <button
          type="button"
          onClick={handleApply}
          disabled={marking}
          className="btn-primary"
        >
          {marking ? "Marking…" : "✓ Mark as applied"}
        </button>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="btn-ghost"
          aria-expanded={expanded}
        >
          {notesLabel} {expanded ? "▴" : "▾"}
        </button>
        <button
          type="button"
          onClick={() => setFeedbackExpanded((v) => !v)}
          className="btn-ghost"
          aria-expanded={feedbackExpanded}
        >
          {feedbackLabel} {feedbackExpanded ? "▴" : "▾"}
        </button>
        <span className="flex-1" />
        <button
          type="button"
          onClick={handleSkip}
          className="text-[13px] font-medium text-slate hover:text-ink transition-colors px-3 py-2"
        >
          Skip
        </button>
      </div>

      {/* Expandable notes drawer — grid-rows trick animates between auto and 0 */}
      <div
        className="grid transition-[grid-template-rows] duration-300 ease-out"
        style={{ gridTemplateRows: expanded ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden">
          <div className="mt-5 pt-5 border-t border-hairline">
            {expanded && (
              <CompanyNotes
                company={job.company}
                onCountChange={setNoteCount}
              />
            )}
          </div>
        </div>
      </div>

      <div
        className="grid transition-[grid-template-rows] duration-300 ease-out"
        style={{ gridTemplateRows: feedbackExpanded ? "1fr" : "0fr" }}
      >
        <div className="overflow-hidden">
          <div className="mt-5 pt-5 border-t border-hairline">
            {feedbackExpanded && (
              <JobFeedback
                jobId={job.id}
                onCountChange={setFeedbackCount}
              />
            )}
          </div>
        </div>
      </div>

      {skipModalOpen && (
        <SkipFeedbackModal
          company={companyDisplay ?? job.company}
          onCancel={() => setSkipModalOpen(false)}
          onConfirm={confirmSkip}
        />
      )}
    </article>
  );
}
