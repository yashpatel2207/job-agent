"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

type Option = { value: string; label: string };

export function FilterSegment({
  label,
  value,
  defaultValue,
  onChange,
  options,
  align = "start",
  variant = "bar",
  searchable = false,
}: {
  label: string;
  value: string;
  defaultValue: string;
  onChange: (v: string) => void;
  options: Option[];
  align?: "start" | "end";
  variant?: "bar" | "pill";
  searchable?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  const [coords, setCoords] = useState<{ top: number; left?: number; right?: number } | null>(null);
  const [search, setSearch] = useState("");
  const buttonRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const active = value !== defaultValue;
  const current = options.find((o) => o.value === value);
  const display = current?.label ?? "";

  const filtered = useMemo<Option[]>(() => {
    if (!searchable) return options;
    const q = search.trim().toLowerCase();
    if (!q) return options;
    return options.filter((o) => o.label.toLowerCase().includes(q));
  }, [options, search, searchable]);

  // Position the portal'd popover under the trigger
  useEffect(() => {
    if (!open) {
      setCoords(null);
      return;
    }
    const r = buttonRef.current?.getBoundingClientRect();
    if (!r) return;
    const top = r.bottom + 6;
    if (align === "end") {
      setCoords({ top, right: window.innerWidth - r.right });
    } else {
      setCoords({ top, left: r.left });
    }
  }, [open, align]);

  // Reset search whenever the popover closes
  useEffect(() => {
    if (!open) setSearch("");
  }, [open]);

  // Auto-focus the search input shortly after opening
  useEffect(() => {
    if (!open || !searchable) return;
    const id = requestAnimationFrame(() => searchRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, [open, searchable]);

  // Click outside, scroll outside, and global keyboard handlers
  useEffect(() => {
    if (!open) return;
    const onPointer = (e: MouseEvent | TouchEvent) => {
      const t = e.target as Node;
      if (buttonRef.current?.contains(t)) return;
      if (popoverRef.current?.contains(t)) return;
      setOpen(false);
    };
    const onScroll = (e: Event) => {
      // Allow scrolling inside the popover (long lists)
      if (popoverRef.current?.contains(e.target as Node)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        if (searchable && search) {
          setSearch("");
          searchRef.current?.focus();
          return;
        }
        setOpen(false);
        buttonRef.current?.focus();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => Math.min(filtered.length - 1, i + 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) => Math.max(0, i - 1));
      } else if (e.key === "Enter" && activeIndex >= 0 && activeIndex < filtered.length) {
        e.preventDefault();
        onChange(filtered[activeIndex].value);
        setOpen(false);
        buttonRef.current?.focus();
      } else if (e.key === "Home") {
        e.preventDefault();
        setActiveIndex(0);
      } else if (e.key === "End") {
        e.preventDefault();
        setActiveIndex(filtered.length - 1);
      }
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("touchstart", onPointer);
    document.addEventListener("keydown", onKey);
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", () => setOpen(false));
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("touchstart", onPointer);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, [open, activeIndex, filtered, onChange, search, searchable]);

  // Initialize active index when opening or when filter narrows the list
  useEffect(() => {
    if (!open) return;
    const idx = filtered.findIndex((o) => o.value === value);
    setActiveIndex(idx >= 0 ? idx : filtered.length > 0 ? 0 : -1);
  }, [open, filtered, value]);

  // Scroll active item into view
  useEffect(() => {
    if (!open || activeIndex < 0 || !listRef.current) return;
    const el = listRef.current.children[activeIndex] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [open, activeIndex]);

  const segmentClass = variant === "pill" ? "filter-segment filter-segment--pill" : "filter-segment";

  const trigger = (
    <button
      ref={buttonRef}
      type="button"
      className={segmentClass}
      onClick={() => setOpen((o) => !o)}
      onKeyDown={(e) => {
        if (!open && (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          setOpen(true);
        }
      }}
      aria-haspopup="listbox"
      aria-expanded={open}
      aria-label={`${label}: ${display}`}
      data-open={open || undefined}
    >
      {active && <span className="filter-segment-dot" aria-hidden="true" />}
      <span className="filter-segment-label">{label}</span>
      <span className="filter-segment-value">{display}</span>
      <span className="filter-segment-chevron" aria-hidden="true">
        <ChevronIcon />
      </span>
    </button>
  );

  const popover = open && coords && typeof document !== "undefined"
    ? createPortal(
        <div
          ref={popoverRef}
          className={`filter-popover${searchable ? "" : " filter-popover--no-search"}`}
          role="dialog"
          aria-label={label}
          style={{
            top: coords.top,
            ...(coords.left !== undefined ? { left: coords.left } : {}),
            ...(coords.right !== undefined ? { right: coords.right } : {}),
          }}
        >
          {searchable && (
            <>
              <div className="filter-popover-search">
                <div className="filter-popover-search-field">
                  <span className="filter-popover-search-icon" aria-hidden="true">
                    <SearchIcon />
                  </span>
                  <input
                    ref={searchRef}
                    type="search"
                    className="filter-popover-search-input"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder={`Search ${label.toLowerCase()}…`}
                    aria-label={`Search ${label.toLowerCase()}`}
                    autoComplete="off"
                    spellCheck={false}
                  />
                </div>
              </div>
              <div className="filter-popover-search-divider" aria-hidden="true" />
            </>
          )}
          <div ref={listRef} className="filter-popover-list" role="listbox" aria-label={label}>
            {filtered.length === 0 ? (
              <div className="filter-popover-empty">
                {searchable && search ? "No matches" : "No options"}
              </div>
            ) : (
              filtered.map((o, i) => (
                <button
                  key={o.value}
                  type="button"
                  role="option"
                  aria-selected={value === o.value}
                  data-active={i === activeIndex || undefined}
                  className="filter-popover-item"
                  onMouseEnter={() => setActiveIndex(i)}
                  onClick={() => {
                    onChange(o.value);
                    setOpen(false);
                    buttonRef.current?.focus();
                  }}
                >
                  <span className="truncate">{o.label}</span>
                  {value === o.value && (
                    <span className="filter-popover-item-check" aria-hidden="true">
                      <CheckIcon />
                    </span>
                  )}
                </button>
              ))
            )}
          </div>
        </div>,
        document.body,
      )
    : null;

  if (variant === "pill") {
    return (
      <>
        {trigger}
        {popover}
      </>
    );
  }

  return (
    <div className="filter-segment-wrap">
      {trigger}
      {popover}
    </div>
  );
}

function ChevronIcon() {
  return (
    <svg width="10" height="6" viewBox="0 0 10 6" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2.5 7.5L5.5 10.5L11.5 3.5" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M11 11L14 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
