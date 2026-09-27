"use client";

import { CanvasIcon, ChatIcon, PanelsIcon } from "./icons";

export type BuilderView = "canvas" | "chat" | "panels";

const VIEWS = [
  { id: "canvas", label: "Preview", Icon: CanvasIcon },
  { id: "chat", label: "Chat", Icon: ChatIcon },
  { id: "panels", label: "Edit", Icon: PanelsIcon },
] as const;

export function ViewTabs({
  view,
  marked,
  onChange,
}: {
  view: BuilderView;
  marked?: BuilderView | null;
  onChange: (view: BuilderView) => void;
}) {
  return (
    <nav
      aria-label="Builder views"
      className="flex shrink-0 gap-1 border-t border-ui-border bg-ui-surface px-2 pb-[env(safe-area-inset-bottom)] pt-1.5 sm:hidden"
    >
      {VIEWS.map(({ id, label, Icon }) => {
        const active = view === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => onChange(id)}
            aria-current={active ? "page" : undefined}
            className={`flex flex-1 flex-col items-center gap-0.5 rounded-lg px-2 pb-1.5 pt-1 text-[11px] font-medium transition-colors ${
              active
                ? "bg-ui-accent-soft text-ui-accent"
                : "text-ui-muted hover:bg-ui-inset"
            }`}
          >
            <span className="relative">
              <Icon className="h-[18px] w-[18px]" />
              {marked === id && !active && (
                <span
                  aria-hidden
                  className="absolute -right-1 -top-0.5 h-1.5 w-1.5 rounded-full bg-ui-accent"
                />
              )}
            </span>
            {label}
          </button>
        );
      })}
    </nav>
  );
}
