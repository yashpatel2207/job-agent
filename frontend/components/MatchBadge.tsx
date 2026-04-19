export function MatchBadge({ score }: { score: number | null }) {
  if (score === null) {
    return (
      <span className="text-xs px-2 py-0.5 rounded-md bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] font-medium">
        pending
      </span>
    );
  }

  const rounded = score.toFixed(1);
  let classes = "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]";

  if (score >= 8.0) {
    classes = "bg-emerald-50 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200";
  } else if (score >= 7.0) {
    classes = "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200";
  } else {
    classes = "bg-stone-100 text-stone-600 dark:bg-stone-900 dark:text-stone-400";
  }

  return (
    <span className={`text-xs px-2 py-0.5 rounded-md font-medium ${classes}`}>
      {rounded} match
    </span>
  );
}
