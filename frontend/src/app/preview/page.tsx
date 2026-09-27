"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Section, Theme } from "@/types/sections";
import { PageRenderer } from "@/components/PageRenderer";
import { SECTION_LABELS } from "@/lib/sections";
import { FormatBar } from "@/components/build/FormatBar";
import {
  useInlineEditing,
  type EditTarget,
} from "@/components/build/useInlineEditing";
import { fieldForRole } from "@/components/build/EditPanel";
import { nodeFor } from "@/components/build/ComponentTree";

interface PreviewState {
  sections: Section[];
  theme: Theme | null;
  selected: number;
  editable: boolean;
  path?: string;
  reveal?: number;
  flags: Record<number, "placeholder" | "review">;
}

const FLAG_LABEL = { placeholder: "Placeholder", review: "Review" } as const;

export default function PreviewPage() {
  const [state, setState] = useState<PreviewState>({
    sections: [],
    theme: null,
    selected: -1,
    editable: false,
    flags: {},
  });
  const root = useRef<HTMLDivElement | null>(null);
  const [drag, setDrag] = useState<number | null>(null);
  const [over, setOver] = useState<{
    index: number;
    half: "top" | "bottom";
  } | null>(null);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== "mlp:page") return;
      setState((prev) => {
        const same = (before: unknown, after: unknown) =>
          JSON.stringify(before) === JSON.stringify(after);
        const sections = event.data.sections ?? [];
        const theme = event.data.theme ?? null;
        return {
          sections: same(prev.sections, sections) ? prev.sections : sections,
          theme: same(prev.theme, theme) ? prev.theme : theme,
          selected: event.data.selected ?? -1,
          editable: event.data.editable ?? false,
          path: event.data.path,
          reveal: event.data.reveal,
          flags: event.data.flags ?? {},
        };
      });
    };

    window.addEventListener("message", onMessage);
    window.parent?.postMessage({ type: "mlp:ready" }, window.location.origin);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  const edit = useCallback(
    (index: number, target: EditTarget, value: string) => {
      window.parent?.postMessage(
        { type: "mlp:edit", index, ...target, value },
        window.location.origin,
      );
    },
    [],
  );

  useEffect(() => {
    const host = root.current;
    if (!host) return;
    host
      .querySelectorAll("[data-chosen]")
      .forEach((node) => node.removeAttribute("data-chosen"));
    const section = host.querySelector(
      `[data-section-index="${state.selected}"]`,
    );
    const chosen = state.path ? CSS.escape(state.path) : null;
    const current = state.sections[state.selected];
    let element: Element | null | undefined = section;
    if (chosen && section) {
      element = section.querySelector(
        `[data-el="${chosen}"], [data-path="${chosen}"]`,
      );
      if (!element && current) {
        element =
          Array.from(section.querySelectorAll<HTMLElement>("[data-role]")).find(
            (node) =>
              fieldForRole(current, node.dataset.role ?? "") === state.path,
          ) ?? null;
      }
      element?.setAttribute("data-chosen", "");
    }

    if (element) {
      const box = element.getBoundingClientRect();
      const visible = box.bottom > 0 && box.top < window.innerHeight;
      if (!visible)
        element.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [state.path, state.selected, state.sections, state.reveal]);

  const latest = useRef(state);
  useEffect(() => {
    latest.current = state;
  }, [state]);

  const focus = useCallback((index: number, target: EditTarget) => {
    const { sections, selected, path: current } = latest.current;
    const section = sections[index];
    let path: string | undefined;
    if (target.path && section) {
      path = nodeFor(section, target.path);
    } else if (target.role && section) {
      path = fieldForRole(section, target.role);
    }
    if (index === selected && path === current) return;
    window.parent?.postMessage(
      { type: "mlp:select", index, path },
      window.location.origin,
    );
  }, []);

  useInlineEditing({
    root,
    enabled: state.editable,
    onEdit: edit,
    onFocus: focus,
    deps: [state.sections, state.theme],
  });

  const pinned = (index: number) =>
    state.sections[index]?.type === "header" ||
    state.sections[index]?.type === "footer";

  const drop = (over: number, half: "top" | "bottom") => {
    if (drag === null || drag === over || pinned(drag)) return;
    const neighbour = state.sections[over]?.type;
    if (!neighbour) return;
    window.parent?.postMessage(
      {
        type: "mlp:move",
        section: state.sections[drag].type,
        position: `${half === "top" ? "before" : "after"} ${neighbour}`,
      },
      window.location.origin,
    );
    setDrag(null);
    setOver(null);
  };

  const select = (index: number, event?: { target: EventTarget | null }) => {
    const element =
      event?.target instanceof Element
        ? event.target.closest<HTMLElement>("[data-el]")
        : null;
    window.parent?.postMessage(
      {
        type: "mlp:select",
        index,
        path: element?.dataset.el,
        label: element?.dataset.elLabel,
      },
      window.location.origin,
    );
  };

  return (
    <div ref={root} className="relative min-h-dvh bg-background">
      <FormatBar enabled={state.editable} />
      {state.sections.map((section, i) => {
        const selected = i === state.selected;
        return (
          <div
            key={i}
            data-section-index={i}
            data-section-type={section.type}
            role="button"
            tabIndex={0}
            aria-pressed={selected}
            onClick={(event) => {
              if (
                event.target instanceof Element &&
                event.target.closest("a")
              ) {
                event.preventDefault();
              }
              select(i, event);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                select(i);
              }
            }}
            onDragOver={(event) => {
              if (drag === null || pinned(i)) return;
              event.preventDefault();
              const box = event.currentTarget.getBoundingClientRect();
              const half =
                event.clientY - box.top < box.height / 2 ? "top" : "bottom";
              setOver({ index: i, half });
            }}
            onDragLeave={() => setOver((o) => (o?.index === i ? null : o))}
            onDrop={(event) => {
              event.preventDefault();
              if (over?.index === i) drop(i, over.half);
            }}
            data-selecting={selected ? "" : undefined}
            className="group relative cursor-pointer outline-none"
          >
            {over?.index === i && drag !== null && (
              <span
                aria-hidden
                className={`pointer-events-none absolute inset-x-0 z-20 h-0.5 bg-ui-accent ${
                  over.half === "top" ? "top-0" : "bottom-0"
                }`}
              />
            )}
            <div className="pointer-events-none [&_[data-editable]]:pointer-events-auto [&_[data-el]]:pointer-events-auto [&_summary]:pointer-events-auto">
              <PageRenderer
                sections={[section]}
                theme={state.theme}
                context={state.sections}
              />
            </div>

            <span
              aria-hidden
              className={`pointer-events-none absolute inset-0 ring-inset transition-all ${
                selected
                  ? "ring-2 ring-ui-accent"
                  : "ring-0 ring-ui-accent/40 group-hover:ring-2"
              }`}
            />

            {state.flags[i] && (
              <span
                className={`pointer-events-none absolute right-3 top-3 flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-medium ${
                  state.flags[i] === "placeholder"
                    ? "bg-ui-danger-soft text-ui-danger"
                    : "bg-ui-surface/90 text-ui-muted ring-1 ring-ui-border"
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    state.flags[i] === "placeholder"
                      ? "bg-ui-danger"
                      : "bg-ui-border-strong"
                  }`}
                />
                {FLAG_LABEL[state.flags[i]]}
              </span>
            )}

            <span
              draggable={!pinned(i)}
              onDragStart={(event) => {
                setDrag(i);
                event.dataTransfer.effectAllowed = "move";
                event.dataTransfer.setData("text/plain", String(i));
              }}
              onDragEnd={() => {
                setDrag(null);
                setOver(null);
              }}
              onKeyDown={(event) => {
                if (!event.altKey || pinned(i)) return;
                if (event.key !== "ArrowUp" && event.key !== "ArrowDown")
                  return;
                event.preventDefault();
                window.parent?.postMessage(
                  {
                    type: "mlp:move",
                    section: state.sections[i].type,
                    position: event.key === "ArrowUp" ? "up" : "down",
                  },
                  window.location.origin,
                );
              }}
              tabIndex={pinned(i) ? -1 : 0}
              title={pinned(i) ? undefined : "Drag to reorder (or Alt + ↑/↓)"}
              className={`absolute left-3 top-3 rounded-md px-2 py-1 text-[11px] font-medium text-white transition-opacity ${
                pinned(i)
                  ? "pointer-events-none"
                  : "cursor-grab active:cursor-grabbing"
              } ${
                selected
                  ? "bg-ui-accent opacity-100"
                  : "bg-ui-text/75 opacity-0 group-hover:opacity-100"
              }`}
            >
              {SECTION_LABELS[section.type]}
              {!pinned(i) && (
                <button
                  type="button"
                  aria-label={`Remove ${SECTION_LABELS[section.type]} section`}
                  title="Remove section"
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={(event) => {
                    event.stopPropagation();
                    window.parent?.postMessage(
                      { type: "mlp:remove", section: section.type },
                      window.location.origin,
                    );
                  }}
                  className="-mr-1 ml-1.5 rounded px-1 text-white/70 hover:bg-white/20 hover:text-white"
                >
                  ×
                </button>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}
