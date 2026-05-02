export function MatchBadge({
  score,
  size = "md",
}: {
  score: number | null;
  size?: "sm" | "md" | "lg";
}) {
  if (score === null) {
    return <span className="text-[12px] text-mute font-medium">Pending</span>;
  }

  let tone = "text-slate";
  let labelText = "Match";
  if (score >= 8.0) {
    tone = "text-teal";
    labelText = "Strong match";
  } else if (score >= 7.0) {
    tone = "text-amber";
    labelText = "Worth a look";
  }

  const sizeClass =
    size === "lg"
      ? "text-[72px] leading-none"
      : size === "sm"
      ? "text-[24px] leading-none"
      : "text-[40px] leading-none";

  return (
    <div className="flex items-baseline gap-2.5 shrink-0">
      <span className={`font-semibold tabular-nums tracking-tightest ${sizeClass} ${tone}`}>
        {score.toFixed(1)}
      </span>
      <span className={`text-[12px] font-medium ${tone === "text-slate" ? "text-slate" : tone}`}>
        {labelText}
      </span>
    </div>
  );
}
