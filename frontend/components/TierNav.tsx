"use client";

import { useEffect, useState } from "react";

export type TierNavItem = {
  id: string;
  label: string;
  count: number;
  accent: "teal" | "amber" | "slate";
};

const DOT_CLASS: Record<TierNavItem["accent"], string> = {
  teal: "tier-dot tier-dot-teal",
  amber: "tier-dot tier-dot-amber",
  slate: "tier-dot tier-dot-slate",
};

export function TierNav({ tiers }: { tiers: TierNavItem[] }) {
  const [active, setActive] = useState<string | null>(tiers[0]?.id ?? null);

  useEffect(() => {
    if (tiers.length === 0) return;
    if (!tiers.some((t) => t.id === active)) {
      setActive(tiers[0].id);
    }
  }, [tiers, active]);

  useEffect(() => {
    if (tiers.length === 0) return;
    const els = tiers
      .map((t) => document.getElementById(t.id))
      .filter((el): el is HTMLElement => el !== null);
    if (els.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible.length > 0) {
          setActive(visible[0].target.id);
        }
      },
      {
        rootMargin: "-140px 0px -55% 0px",
        threshold: 0,
      },
    );

    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [tiers]);

  if (tiers.length < 2) return null;

  const handleJump = (id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    const top = el.getBoundingClientRect().top + window.scrollY - 120;
    window.scrollTo({ top, behavior: "smooth" });
    setActive(id);
  };

  return (
    <div className="tier-bar -mx-6 sm:-mx-10 mb-10">
      <nav
        aria-label="Jump to tier"
        className="max-w-6xl mx-auto px-6 sm:px-10 py-3 flex items-center gap-3 overflow-x-auto"
      >
        <span className="label hidden sm:inline-flex items-center mr-1 shrink-0">
          Jump to
        </span>
        <div className="flex items-center gap-2">
          {tiers.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => handleJump(t.id)}
              className={`tier-chip ${active === t.id ? "tier-chip-active" : ""}`}
              aria-current={active === t.id ? "true" : undefined}
            >
              <span className={DOT_CLASS[t.accent]} aria-hidden />
              <span>{t.label}</span>
              <span className="tier-chip-count">{t.count}</span>
            </button>
          ))}
        </div>
      </nav>
    </div>
  );
}
