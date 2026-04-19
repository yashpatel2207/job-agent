export function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-[hsl(var(--muted))] rounded-lg px-4 py-3">
      <p className="text-xs text-[hsl(var(--muted-foreground))] mb-1">{label}</p>
      <p className="text-2xl font-medium">{value}</p>
    </div>
  );
}
