const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Job {
  id: string;
  company: string;
  title: string;
  location: string;
  apply_url: string;
  ats: string;
  score: number | null;
  score_reasons: string[];
  red_flags: string[];
  status: string;
  posted_at: string | null;
  scraped_at: string | null;
  has_resume: boolean;
  jd_text?: string;
  tailored_bullets?: {
    summary: string;
    experience: Array<{
      company: string;
      role: string;
      dates: string;
      bullets: string[];
    }>;
    changes_summary: string;
    skills_emphasized: string[];
  };
  drafted_answers?: Record<string, string>;
  user_notes?: string;
}

export interface Stats {
  total: number;
  new: number;
  ready_to_review: number;
  applied: number;
  avg_score: number;
}

export async function fetchJobs(params?: { status?: string; min_score?: number }): Promise<Job[]> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.min_score !== undefined) qs.set("min_score", String(params.min_score));
  const res = await fetch(`${API_URL}/api/jobs?${qs}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch jobs");
  return res.json();
}

export async function fetchJob(id: string): Promise<Job> {
  const res = await fetch(`${API_URL}/api/jobs/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch job");
  return res.json();
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch(`${API_URL}/api/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
}

export async function updateStatus(id: string, status: string, notes?: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/jobs/${id}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, notes }),
  });
  if (!res.ok) throw new Error("Failed to update status");
}

export async function saveAnswers(id: string, answers: Record<string, string>): Promise<void> {
  const res = await fetch(`${API_URL}/api/jobs/${id}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) throw new Error("Failed to save answers");
}

export async function triggerPrefill(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/jobs/${id}/prefill`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to trigger prefill");
}
