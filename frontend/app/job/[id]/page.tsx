"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { fetchJob, saveAnswers, triggerPrefill, updateStatus, Job } from "@/lib/api";
import { MatchBadge } from "@/components/MatchBadge";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchJob(id).then((j) => {
      setJob(j);
      setAnswers(j.drafted_answers || {});
    });
  }, [id]);

  if (!job) return <p className="text-sm text-[hsl(var(--muted-foreground))]">Loading...</p>;

  const handleSaveAnswers = async () => {
    setSaving(true);
    await saveAnswers(job.id, answers);
    setSaving(false);
  };

  const handlePrefill = async () => {
    setBusy(true);
    try {
      await saveAnswers(job.id, answers);
      await triggerPrefill(job.id);
      alert("Chromium is opening on your laptop. Review, edit, submit.");
    } catch {
      alert("Prefill failed. Is the local API running?");
    } finally {
      setBusy(false);
    }
  };

  const handleMarkApplied = async () => {
    await updateStatus(job.id, "applied");
    router.push("/");
  };

  return (
    <div>
      <Link href="/" className="text-sm text-[hsl(var(--muted-foreground))] hover:underline mb-4 inline-block">
        ← Back to queue
      </Link>

      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2 flex-wrap">
          <h1 className="text-2xl font-medium">{job.title}</h1>
          <MatchBadge score={job.score} />
        </div>
        <p className="text-[hsl(var(--muted-foreground))]">
          {job.company} · {job.location || "location not specified"} · {job.ats}
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          {job.score_reasons.length > 0 && (
            <section className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-5">
              <h2 className="text-sm font-medium mb-2">Why it matched</h2>
              <ul className="space-y-1 text-sm">
                {job.score_reasons.map((r, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-emerald-600 dark:text-emerald-400">+</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
              {job.red_flags.length > 0 && (
                <>
                  <h3 className="text-sm font-medium mt-4 mb-2 text-amber-700 dark:text-amber-400">Heads up</h3>
                  <ul className="space-y-1 text-sm text-[hsl(var(--muted-foreground))]">
                    {job.red_flags.map((r, i) => (
                      <li key={i} className="flex gap-2">
                        <span>−</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>
          )}

          {job.tailored_bullets && (
            <section className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-5">
              <div className="flex items-baseline justify-between mb-3">
                <h2 className="text-sm font-medium">Tailored resume preview</h2>
                <span className="text-xs text-[hsl(var(--muted-foreground))]">
                  {job.has_resume ? "DOCX generated" : "not generated"}
                </span>
              </div>
              <p className="text-sm italic text-[hsl(var(--muted-foreground))] mb-4">
                {job.tailored_bullets.changes_summary}
              </p>
              <div className="space-y-4">
                <div>
                  <p className="text-xs text-[hsl(var(--muted-foreground))] uppercase tracking-wide mb-1">Summary</p>
                  <p className="text-sm">{job.tailored_bullets.summary}</p>
                </div>
                {job.tailored_bullets.experience.map((exp, i) => (
                  <div key={i}>
                    <p className="text-sm font-medium">
                      {exp.role} · {exp.company}
                      <span className="font-normal text-[hsl(var(--muted-foreground))]"> · {exp.dates}</span>
                    </p>
                    <ul className="mt-1 space-y-1">
                      {exp.bullets.map((b, j) => (
                        <li key={j} className="text-sm pl-4 relative">
                          <span className="absolute left-0">·</span>
                          {b}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-5">
            <h2 className="text-sm font-medium mb-3">Custom answers</h2>
            <p className="text-xs text-[hsl(var(--muted-foreground))] mb-4">
              Draft your answers here. They'll be prefilled when you open the form. This is the part you should write in your own voice.
            </p>

            {[
              { key: "why_this_company", label: `Why ${job.company}?`, placeholder: "What specifically draws you to this company?" },
              { key: "proudest_project", label: "Proudest frontend project", placeholder: "Your evergreen answer, optionally tailored." },
              { key: "why_interested", label: "Why interested in this role?", placeholder: "Connect the role to what you want to do next." },
            ].map((q) => (
              <div key={q.key} className="mb-4">
                <label className="text-sm font-medium mb-1 block">{q.label}</label>
                <textarea
                  value={answers[q.key] || ""}
                  onChange={(e) => setAnswers({ ...answers, [q.key]: e.target.value })}
                  placeholder={q.placeholder}
                  className="w-full border border-[hsl(var(--border))] rounded-md px-3 py-2 text-sm bg-[hsl(var(--background))] min-h-[100px]"
                />
              </div>
            ))}

            <button
              onClick={handleSaveAnswers}
              disabled={saving}
              className="text-sm px-3 py-1.5 rounded-md border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))]"
            >
              {saving ? "Saving..." : "Save answers"}
            </button>
          </section>

          <section className="bg-[hsl(var(--card))] border border-[hsl(var(--border))] rounded-xl p-5">
            <h2 className="text-sm font-medium mb-3">Job description</h2>
            <div className="text-sm whitespace-pre-wrap text-[hsl(var(--muted-foreground))] max-h-96 overflow-y-auto">
              {job.jd_text}
            </div>
          </section>
        </div>

        <aside className="space-y-3">
          <button
            onClick={handlePrefill}
            disabled={busy || !job.has_resume}
            className="w-full text-sm font-medium bg-[hsl(var(--foreground))] text-[hsl(var(--background))] px-3 py-2 rounded-md hover:opacity-90 disabled:opacity-40"
          >
            {busy ? "Opening browser..." : "Approve and prefill"}
          </button>
          <a
            href={job.apply_url}
            target="_blank"
            rel="noreferrer"
            className="block w-full text-center text-sm px-3 py-2 rounded-md border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))]"
          >
            Open original posting
          </a>
          <button
            onClick={handleMarkApplied}
            className="w-full text-sm px-3 py-2 rounded-md border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))]"
          >
            Mark as applied
          </button>
        </aside>
      </div>
    </div>
  );
}
