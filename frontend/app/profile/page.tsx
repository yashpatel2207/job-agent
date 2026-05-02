export default function ProfilePage() {
  return (
    <div>
      <header className="mb-12">
        <p className="text-[13px] font-semibold text-indigo tracking-snug mb-4 reveal">
          Your dossier
        </p>
        <h1
          className="font-semibold text-[56px] sm:text-[88px] leading-[0.98] tracking-tightest text-ink reveal"
          style={{ animationDelay: "0.05s" }}
        >
          Profile.
        </h1>
        <p
          className="mt-5 text-[18px] text-slate max-w-2xl reveal"
          style={{ animationDelay: "0.1s" }}
        >
          Personal info, work authorization, EEO defaults, and saved answers — the
          source of truth the agent reads from when scoring and drafting.
        </p>
      </header>

      <div
        className="grid md:grid-cols-[1fr_2fr] gap-8 items-start reveal"
        style={{ animationDelay: "0.15s" }}
      >
        <aside>
          <p className="label mb-3">Editor</p>
          <p className="font-semibold text-[24px] tracking-snug leading-snug text-ink">
            For now, the dossier lives on disk.
          </p>
        </aside>

        <article className="card p-8">
          <p className="label mb-3">A note from v1</p>
          <p className="text-[16px] leading-relaxed text-ink/85 mb-5">
            Inline editing is intentionally deferred. The JSON shape is still drifting
            as the agent learns which fields actually move the score — pinning a UI to
            it now would only mean rebuilding it next month.
          </p>
          <p className="text-[15px] leading-relaxed text-slate mb-7">
            For v1, edit{" "}
            <Code>backend/profile.json</Code> and{" "}
            <Code>backend/master_resume.json</Code> directly, then run{" "}
            <Code>python seed.py</Code> to sync them into the database.
          </p>
          <div className="hairline mb-6" />
          <p className="text-[13px] text-slate">
            v2 will move editing in here, once the schema is settled.
          </p>
        </article>
      </div>
    </div>
  );
}

function Code({ children }: { children: React.ReactNode }) {
  return (
    <code className="font-mono text-[13px] text-indigo bg-snow-2 px-2 py-0.5 rounded-md">
      {children}
    </code>
  );
}
