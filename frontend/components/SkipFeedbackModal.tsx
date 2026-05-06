"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export function SkipFeedbackModal({
  company,
  onCancel,
  onConfirm,
}: {
  company: string;
  onCancel: () => void;
  onConfirm: (reason: string) => Promise<void> | void;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onCancel();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [busy, onCancel]);

  const handleSkip = async () => {
    setBusy(true);
    try {
      await onConfirm(reason.trim());
    } finally {
      setBusy(false);
    }
  };

  if (typeof document === "undefined") return null;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 px-4"
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onCancel();
      }}
    >
      <div className="card bg-paper p-6 w-full max-w-md">
        <h3 className="font-semibold text-[18px] text-ink mb-1">
          Skip {company}?
        </h3>
        <p className="text-[13.5px] text-slate mb-4 leading-relaxed">
          Optional — tell the scorer why so future similar jobs get downranked.
          Leave blank to just skip.
        </p>
        <textarea
          ref={textareaRef}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. wrong stack, comp too low, role too senior…"
          className="field min-h-[88px]"
        />
        <div className="flex gap-2 mt-4 justify-end">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="btn-ghost"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSkip}
            disabled={busy}
            className="btn-primary"
          >
            {busy ? "Skipping…" : "Skip"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
