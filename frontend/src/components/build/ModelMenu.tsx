"use client";

import { useEffect, useRef, useState } from "react";
import type { ModelInfo } from "@/lib/orchestrator";
import { ChevronIcon, ModelIcon } from "./icons";

export function ModelMenu({
  models,
  value,
  onChange,
  disabled,
}: {
  models: ModelInfo[];
  value: string | null;
  onChange: (model: string | null) => void;
  disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLDivElement>(null);
  const current =
    models.find((m) => m.id === value) ??
    models.find((m) => m.default) ??
    models[0];

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
        onClick={() => setOpen((was) => !was)}
        disabled={disabled || models.length === 0}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={`flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 ${
          open ? "bg-ui-inset text-ui-text" : "text-ui-muted hover:bg-ui-inset"
        }`}
      >
        <ModelIcon className="h-3.5 w-3.5" />
        {current?.label ?? "Default"}
        <ChevronIcon className="h-3 w-3 text-ui-faint" />
      </button>

      {open && (
        <ul
          role="listbox"
          className="absolute bottom-full left-0 z-30 mb-1.5 w-64 overflow-hidden rounded-xl border border-ui-border bg-ui-surface py-1 shadow-[0_12px_32px_rgba(16,24,40,0.12)]"
        >
          {models.map((model) => {
            const selected = model.id === current?.id;
            return (
              <li key={model.id}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => {
                    onChange(model.default ? null : model.id);
                    setOpen(false);
                  }}
                  className="flex w-full items-start gap-2.5 px-3 py-2 text-left transition-colors hover:bg-ui-inset"
                >
                  <ModelIcon
                    className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${
                      selected ? "text-ui-accent" : "text-ui-faint"
                    }`}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm text-ui-text">
                      {model.label}
                    </span>
                    <span className="block text-[11px] text-ui-faint">
                      {model.hint}
                      {model.default && " · default"}
                    </span>
                  </span>
                  {selected && (
                    <span className="mt-0.5 text-xs text-ui-accent">✓</span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
