"use client";

import { useEffect, useRef, useState } from "react";
import type { BuildSummary } from "@/lib/builds";
import { ChevronIcon, PlusIcon, SparklesIcon } from "./icons";

export function BuildMenu({
  builds,
  currentId,
  title,
  onOpen,
  onCreate,
  onOpenMenu,
  disabled,
}: {
  builds: BuildSummary[];
  currentId: string | null;
  title: string;
  onOpen: (id: string) => void;
  onCreate: () => void;
  onOpenMenu: () => void;
  disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!menu.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  return (
    <div ref={menu} className="relative">
      <button
        type="button"
        onClick={() => {
          if (!open) onOpenMenu();
          setOpen((was) => !was);
        }}
        disabled={disabled}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex max-w-[8.5rem] items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-medium transition-colors hover:bg-ui-inset disabled:opacity-50 sm:max-w-[15rem] sm:px-2.5"
      >
        <span className="truncate">{title}</span>
        <ChevronIcon className="h-3.5 w-3.5 shrink-0 text-ui-faint" />
      </button>

      {open && (
        <div className="absolute left-0 z-30 mt-1.5 w-[min(20rem,calc(100vw-1.5rem))] overflow-hidden rounded-xl border border-ui-border bg-ui-surface shadow-[0_12px_32px_rgba(16,24,40,0.12)]">
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              onCreate();
            }}
            className="flex w-full items-center gap-2.5 border-b border-ui-border px-3 py-2.5 text-left text-sm font-medium transition-colors hover:bg-ui-inset"
          >
            <span className="brand-gradient flex h-6 w-6 items-center justify-center rounded-md text-white">
              <PlusIcon className="h-3.5 w-3.5" />
            </span>
            New page
          </button>

          <ul className="max-h-80 overflow-y-auto py-1">
            {builds.length === 0 && (
              <li className="px-3 py-2.5 text-sm text-ui-muted">
                Nothing saved yet.
              </li>
            )}
            {builds.map((build) => {
              const current = build.id === currentId;
              return (
                <li key={build.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setOpen(false);
                      if (!current) onOpen(build.id);
                    }}
                    className={`flex w-full items-center gap-2.5 px-3 py-2 text-left transition-colors hover:bg-ui-inset ${
                      current ? "bg-ui-accent-soft/60" : ""
                    }`}
                  >
                    <SparklesIcon
                      className={`h-3.5 w-3.5 shrink-0 ${
                        current ? "text-ui-accent" : "text-ui-faint"
                      }`}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm">
                        {build.title}
                      </span>
                      <span className="block truncate text-[11px] text-ui-faint">
                        {build.pageUrl ?? "not started"} · {when(build.updated ?? null)}
                      </span>
                    </span>
                    {current && (
                      <span className="shrink-0 text-[11px] font-medium text-ui-accent">
                        open
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

function when(iso: string | null) {
  if (!iso) return "just now";
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return iso;

  const minutes = Math.round((Date.now() - at.getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 60 * 24) return `${Math.round(minutes / 60)}h ago`;
  return at.toLocaleDateString([], { day: "numeric", month: "short" });
}
