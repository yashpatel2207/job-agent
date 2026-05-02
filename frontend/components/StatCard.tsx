export function StatCard({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string | number;
  accent?: boolean;
}) {
  return (
    <div
      className={`px-7 py-7 border-r border-hairline last:border-r-0 flex flex-col gap-2 ${
        accent ? "bg-mint" : ""
      }`}
    >
      <p className="label">{label}</p>
      <p
        className={`font-semibold text-[40px] leading-none tracking-tightest tabular-nums ${
          accent ? "text-teal" : "text-ink"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
