"use client";

import type { PageVersion } from "@/data/build-mock";

function clockTime(when: string) {
  const at = new Date(when);
  return Number.isNaN(at.getTime())
    ? when
    : at.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function dayLabel(when: string) {
  const at = new Date(when);
  if (Number.isNaN(at.getTime())) return "";
  const today = new Date();
  const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const apart = Math.round(
    (day(today).getTime() - day(at).getTime()) / 86_400_000,
  );
  if (apart === 0) return "Today";
  if (apart === 1) return "Yesterday";
  return at.toLocaleDateString([], {
    day: "numeric",
    month: "short",
    ...(at.getFullYear() !== today.getFullYear() ? { year: "numeric" } : {}),
  });
}

export function VersionHistory({
  versions,
  previewing,
  onPreview,
  onRestore,
  isWorking = false,
}: {
  versions?: PageVersion[];
  previewing?: number;
  onPreview?: (version?: number) => void;
  onRestore?: (version: number) => void;
  isWorking?: boolean;
}) {
  const history = versions ?? [];
  const head = history[0]?.id;
  const number = (id: string) => Number(id.replace(/^v/, ""));
  const shownLabel = history.find(
    (version) => previewing !== undefined && number(version.id) === previewing,
  )?.label;

  return (
    <div className="flex flex-col gap-3">
      {previewing !== undefined && (
        <div className="flex items-center gap-2 rounded-lg border border-ui-accent/30 bg-ui-accent-soft px-3 py-2 text-xs text-ui-text">
          <span className="min-w-0 flex-1 truncate">
            Preview: {shownLabel ?? `v${previewing}`}
          </span>
          <button
            type="button"
            disabled={isWorking}
            onClick={() => onRestore?.(previewing)}
            className="shrink-0 rounded-md bg-ui-accent px-2 py-1 font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            Restore
          </button>
          <button
            type="button"
            disabled={isWorking}
            onClick={() => onPreview?.(undefined)}
            className="shrink-0 rounded-md px-2 py-1 text-ui-muted hover:bg-ui-inset disabled:opacity-50"
          >
            Back
          </button>
        </div>
      )}

      <ol className="flex flex-col">
        {history.map((version, i) => {
          const current = version.id === head;
          const shown = previewing === number(version.id);
          const day = dayLabel(version.when);
          const newDay = i === 0 || day !== dayLabel(history[i - 1].when);
          const threads =
            i < history.length - 1 && dayLabel(history[i + 1].when) === day;
          return (
            <li key={version.id} className="relative flex flex-col">
              {newDay && day && (
                <div
                  className={`flex items-center gap-2 text-[11px] font-medium text-ui-muted ${
                    i === 0 ? "pb-2" : "pb-2 pt-4"
                  }`}
                >
                  <span className="h-px flex-1 bg-ui-border" />
                  {day}
                  <span className="h-px flex-1 bg-ui-border" />
                </div>
              )}
              <div className="relative flex gap-3">
                {threads && (
                  <span className="absolute left-[5px] top-5 h-full w-px bg-ui-border" />
                )}
                <span
                  className={`relative z-10 mt-[7px] h-2.5 w-2.5 shrink-0 rounded-full ring-4 ring-ui-surface ${
                    current || shown ? "bg-ui-accent" : "bg-ui-border-strong"
                  }`}
                />
                <button
                  type="button"
                  disabled={isWorking}
                  onClick={() =>
                    onPreview?.(current ? undefined : number(version.id))
                  }
                  aria-pressed={shown}
                  title={new Date(version.when).toLocaleString()}
                  className={`group flex min-w-0 flex-1 items-baseline gap-2 rounded-md px-2 py-1 text-left transition-colors enabled:hover:bg-ui-inset ${
                    shown ? "bg-ui-accent-soft" : ""
                  }`}
                >
                  <span className="min-w-0 flex-1 truncate text-sm text-ui-text">
                    {version.label}
                  </span>
                  <span className="shrink-0 text-[11px] tabular-nums text-ui-faint">
                    {clockTime(version.when)}
                  </span>
                  {current ? (
                    <span className="shrink-0 text-[11px] font-medium text-ui-accent">
                      current
                    </span>
                  ) : (
                    <span className="shrink-0 text-[11px] text-ui-faint group-hover:text-ui-accent">
                      {shown ? "showing" : "view"}
                    </span>
                  )}
                </button>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
