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
  role_type?: "frontend" | "fullstack" | "other" | null;
  status: string;
  posted_at: string | null;
  scraped_at: string | null;
  jd_text?: string;
  user_notes?: string;
}

export interface Company {
  name: string;
  careers_url: string | null;
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

export async function fetchCompanies(): Promise<Company[]> {
  const res = await fetch(`${API_URL}/api/companies`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch companies");
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

export interface CronRun {
  id: number;
  status: string;
  conclusion: string | null;
  event: string;
  created_at: string;
  updated_at: string;
  html_url: string;
}

export interface CronStatus {
  paused: boolean;
  in_progress: CronRun | null;
  last_run: CronRun | null;
  recent_runs: CronRun[];
  gh_error: string | null;
}

export async function fetchCronStatus(): Promise<CronStatus> {
  const res = await fetch(`${API_URL}/api/cron/status`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch cron status");
  return res.json();
}

export async function triggerCronRun(): Promise<void> {
  const res = await fetch(`${API_URL}/api/cron/trigger`, { method: "POST" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Failed to trigger run");
  }
}

export async function setCronPaused(paused: boolean): Promise<void> {
  const res = await fetch(`${API_URL}/api/cron/pause`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paused }),
  });
  if (!res.ok) throw new Error("Failed to update pause state");
}

export interface CompanyNoteField {
  question: string;
  answer: string;
}

export interface CompanyNotes {
  company: string;
  fields: CompanyNoteField[];
  updated_at: string | null;
}

export async function fetchCompanyNotes(company: string): Promise<CompanyNotes> {
  const res = await fetch(
    `${API_URL}/api/company-notes/${encodeURIComponent(company)}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error("Failed to fetch company notes");
  return res.json();
}

export async function saveCompanyNotes(
  company: string,
  fields: CompanyNoteField[],
): Promise<CompanyNotes> {
  const res = await fetch(
    `${API_URL}/api/company-notes/${encodeURIComponent(company)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fields }),
    },
  );
  if (!res.ok) throw new Error("Failed to save company notes");
  return res.json();
}

export interface JobFeedback {
  id: number;
  job_id: string;
  company: string;
  note: string;
  source: "drawer" | "skip";
  score_at_time: number | null;
  red_flags_at_time: string[];
  created_at: string | null;
}

export async function fetchJobFeedback(jobId: string): Promise<JobFeedback[]> {
  const res = await fetch(`${API_URL}/api/jobs/${jobId}/feedback`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch feedback");
  return res.json();
}

export async function saveJobFeedback(
  jobId: string,
  note: string,
  source: "drawer" | "skip" = "drawer",
): Promise<JobFeedback> {
  const res = await fetch(`${API_URL}/api/jobs/${jobId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note, source }),
  });
  if (!res.ok) throw new Error("Failed to save feedback");
  return res.json();
}

export async function deleteFeedback(feedbackId: number): Promise<void> {
  const res = await fetch(`${API_URL}/api/feedback/${feedbackId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete feedback");
}
