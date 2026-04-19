export default function ProfilePage() {
  return (
    <div>
      <h1 className="text-2xl font-medium mb-1">Profile</h1>
      <p className="text-sm text-[hsl(var(--muted-foreground))] mb-6">
        Personal info, work auth, EEO defaults, saved answers.
      </p>

      <div className="bg-[hsl(var(--muted))] rounded-xl p-6 text-sm">
        <p className="font-medium mb-2">Edit profile.json directly for v1</p>
        <p className="text-[hsl(var(--muted-foreground))] mb-4">
          For speed of shipping, this page is read-only in v1. Edit <code className="bg-[hsl(var(--card))] px-1.5 py-0.5 rounded">backend/profile.json</code> and <code className="bg-[hsl(var(--card))] px-1.5 py-0.5 rounded">backend/master_resume.json</code> directly, then run <code className="bg-[hsl(var(--card))] px-1.5 py-0.5 rounded">python seed.py</code> to sync.
        </p>
        <p className="text-[hsl(var(--muted-foreground))]">
          v2 will add inline editing here. It's intentionally deferred because the JSON structure is likely to shift as you use the system and notice what fields are missing.
        </p>
      </div>
    </div>
  );
}
