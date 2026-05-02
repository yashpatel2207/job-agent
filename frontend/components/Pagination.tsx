"use client";

export function Pagination({
  page,
  pageCount,
  total,
  pageSize,
  onPageChange,
}: {
  page: number;
  pageCount: number;
  total: number;
  pageSize: number;
  onPageChange: (next: number) => void;
}) {
  if (pageCount <= 1) return null;

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  const items = buildPageList(page, pageCount);

  return (
    <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 mt-2 mb-2 pt-4 border-t border-hairline/70">
      <p className="label tabular-nums">
        {start}—{end} of {total}
      </p>
      <div className="flex items-center gap-1" role="navigation" aria-label="Pagination">
        <button
          type="button"
          className="page-btn"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          aria-label="Previous page"
        >
          <ArrowIcon direction="left" />
        </button>
        {items.map((it, i) =>
          it === "ellipsis" ? (
            <span key={`e${i}`} className="px-2 text-mute select-none" aria-hidden>
              …
            </span>
          ) : (
            <button
              key={it}
              type="button"
              onClick={() => onPageChange(it)}
              className={`page-btn ${it === page ? "page-btn-active" : ""}`}
              aria-current={it === page ? "page" : undefined}
              aria-label={`Page ${it}`}
            >
              {it}
            </button>
          ),
        )}
        <button
          type="button"
          className="page-btn"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pageCount}
          aria-label="Next page"
        >
          <ArrowIcon direction="right" />
        </button>
      </div>
    </div>
  );
}

function buildPageList(
  page: number,
  pageCount: number,
): (number | "ellipsis")[] {
  const window = 1;
  const out: (number | "ellipsis")[] = [];
  for (let i = 1; i <= pageCount; i++) {
    const inWindow = i === 1 || i === pageCount || (i >= page - window && i <= page + window);
    if (inWindow) {
      out.push(i);
    } else if (out[out.length - 1] !== "ellipsis") {
      out.push("ellipsis");
    }
  }
  return out;
}

function ArrowIcon({ direction }: { direction: "left" | "right" }) {
  const rotate = direction === "left" ? 180 : 0;
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ transform: `rotate(${rotate}deg)` }}
      aria-hidden
    >
      <path
        d="M4 2L8 6L4 10"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
