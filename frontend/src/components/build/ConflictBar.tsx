"use client";

import type { Conflict } from "@/lib/builder";

export function ConflictBar({
  conflict,
  busy,
  onRefresh,
}: {
  conflict: Conflict | null;
  busy: boolean;
  onRefresh: () => void;
}) {
  if (!conflict) return null;
  return (
    <div className="flex shrink-0 items-center gap-3 rounded-lg border border-ui-border bg-ui-accent-soft px-3 py-2 text-xs text-ui-text">
      <span className="min-w-0 flex-1 leading-5">
        This page changed elsewhere (you have v{conflict.expected}, it is at v
        {conflict.current}). Your unsaved edits are kept -- refresh, then save
        again.
      </span>
      <button
        type="button"
        disabled={busy}
        onClick={onRefresh}
        className="shrink-0 rounded-md bg-ui-accent px-2.5 py-1 font-medium text-white transition-colors hover:bg-ui-accent-hover disabled:opacity-50"
      >
        Refresh
      </button>
    </div>
  );
}
