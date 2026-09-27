"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Section, Theme } from "@/types/sections";
import type { Readiness } from "@/lib/orchestrator";
import { publishHold, type PublishHold } from "@/lib/builder";
import { DesktopIcon, MobileIcon, TabletIcon } from "./icons";
import { ReviewMenu, flagsFor } from "./ReviewMenu";

function AddressBar({
  pageUrl,
  live,
  isWorking,
  onRename,
}: {
  pageUrl: string | null;
  live: boolean;
  isWorking: boolean;
  onRename: (wanted: string) => void;
}) {
  const [draft, setDraft] = useState(pageUrl ?? "");
  const [applied, setApplied] = useState(pageUrl ?? "");
  if (applied !== (pageUrl ?? "")) {
    setApplied(pageUrl ?? "");
    setDraft(pageUrl ?? "");
  }

  const commit = () => {
    const wanted = draft.trim();
    if (!wanted || wanted === pageUrl) {
      setDraft(pageUrl ?? "");
      return;
    }
    onRename(wanted);
  };

  if (!pageUrl) {
    return (
      <span className="mx-auto rounded-md bg-ui-inset px-3 py-1 text-xs text-ui-faint">
        draft preview
      </span>
    );
  }

  return (
    <div className="flex min-w-[10rem] flex-1 items-center rounded-md bg-ui-inset px-2.5 py-1 transition-shadow focus-within:bg-ui-surface focus-within:ring-2 focus-within:ring-ui-accent/25">
      <span className="shrink-0 text-xs text-ui-faint">{siteHost()}</span>
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
          if (e.key === "Escape") setDraft(pageUrl);
        }}
        disabled={isWorking}
        aria-label="Page address"
        spellCheck={false}
        className="min-w-0 flex-1 bg-transparent text-xs text-ui-text outline-none disabled:opacity-50"
      />
      {live && (
        <a
          href={pageUrl}
          target="_blank"
          rel="noopener noreferrer"
          title="Open the live page"
          className="shrink-0 pl-1 text-xs text-ui-faint transition-colors hover:text-ui-accent"
        >
          ↗
        </a>
      )}
    </div>
  );
}

function EditToggle({
  editing,
  disabled,
  onChange,
}: {
  editing: boolean;
  disabled: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={editing}
      disabled={disabled}
      onClick={() => onChange(!editing)}
      title={editing ? "Editing text on the page" : "Clicking through the page"}
      className={`flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-1 text-[11px] font-medium transition-colors disabled:opacity-40 ${
        editing
          ? "border-ui-accent/30 bg-ui-accent-soft text-ui-accent"
          : "border-ui-border text-ui-muted hover:bg-ui-inset"
      }`}
    >
      <span
        aria-hidden
        className={`h-3 w-5 rounded-full p-0.5 transition-colors ${
          editing ? "bg-ui-accent" : "bg-ui-border-strong"
        }`}
      >
        <span
          className={`block h-2 w-2 rounded-full bg-white transition-transform ${
            editing ? "translate-x-2.5" : ""
          }`}
        />
      </span>
      Edit
    </button>
  );
}

function PageActions({
  published,
  hold,
  isPublishing,
  isWorking,
  unsaved,
  onSave,
  onUndo,
  onPublish,
}: {
  published: boolean;
  hold: PublishHold | null;
  isPublishing: boolean;
  isWorking: boolean;
  unsaved: number;
  onSave: () => void;
  onUndo: () => void;
  onPublish: () => void;
}) {
  const dirty = unsaved > 0;
  const canPublish = !dirty && !hold && !published && !isWorking && !isPublishing;

  return (
    <div className="flex shrink-0 items-center gap-1">
      {dirty && (
        <>
          <button
            type="button"
            onClick={onSave}
            disabled={isWorking}
            title={`Save ${unsaved} change${unsaved === 1 ? "" : "s"}`}
            className="brand-gradient rounded-md px-3 py-1.5 text-xs font-medium text-white transition-all hover:brightness-110 disabled:bg-none disabled:bg-ui-inset disabled:text-ui-faint"
          >
            {isWorking ? "Saving…" : "Save"}
          </button>
          <button
            type="button"
            onClick={onUndo}
            disabled={isWorking}
            title="Discard what has been typed since the last save"
            className="rounded-md border border-ui-border px-3 py-1.5 text-xs font-medium text-ui-muted transition-colors hover:bg-ui-inset hover:text-ui-text disabled:opacity-50"
          >
            Undo
          </button>
        </>
      )}

      <button
        type="button"
        onClick={onPublish}
        disabled={!canPublish}
        title={
          dirty
            ? "Save your changes first"
            : hold === "placeholder"
              ? "Replace the placeholder content first"
              : hold === "review"
                ? "Approve the flagged sections first"
                : undefined
        }
        className={`rounded-md px-3 py-1.5 text-xs font-medium transition-all ${
          canPublish
            ? "brand-gradient text-white hover:brightness-110"
            : "bg-ui-inset text-ui-faint"
        }`}
      >
        {isPublishing
          ? "Publishing…"
          : published && !dirty
            ? "Published"
            : "Publish"}
      </button>
    </div>
  );
}

const DEVICES = [
  { id: "desktop", label: "Desktop", width: null, Icon: DesktopIcon },
  { id: "tablet", label: "Tablet", width: 834, Icon: TabletIcon },
  { id: "mobile", label: "Mobile", width: 390, Icon: MobileIcon },
] as const;

type DeviceId = (typeof DEVICES)[number]["id"];

function siteHost() {
  return (
    process.env.NEXT_PUBLIC_SITE_HOST ??
    (typeof window === "undefined" ? "" : window.location.host)
  );
}

export function PageCanvas({
  sections,
  theme,
  pageUrl,
  published,
  live = published,
  readiness = null,
  onApprove,
  isPublishing,
  isWorking,
  unsaved,
  selectedIndex,
  selectedPath,
  reveal,
  onSelect,
  onEdit,
  onMove,
  onRemove,
  onRename,
  onSave,
  onUndo,
  onPublish,
}: {
  sections: Section[];
  theme?: Theme | null;
  pageUrl?: string | null;
  published: boolean;
  live?: boolean;
  readiness?: Readiness | null;
  onApprove?: (section: string) => void;
  isPublishing: boolean;
  isWorking: boolean;
  unsaved: number;
  onEdit: (
    index: number,
    target: { role?: string; path?: string },
    value: string,
  ) => void;
  onMove: (section: string, position: string) => void;
  onRemove: (section: string) => void;
  selectedIndex: number;
  selectedPath?: string;
  reveal?: number;
  onSelect: (
    index: number,
    element?: { path?: string; label?: string },
  ) => void;
  onRename: (wanted: string) => void;
  onSave: () => void;
  onUndo: () => void;
  onPublish: () => void;
}) {
  const [device, setDevice] = useState<DeviceId>("desktop");
  const [editing, setEditing] = useState(true);
  const [ready, setReady] = useState(false);
  const [room, setRoom] = useState({ width: 0, height: 0 });

  const frame = useRef<HTMLIFrameElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const deviceWidth = DEVICES.find((d) => d.id === device)?.width ?? null;

  useEffect(() => {
    const element = stage.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) =>
      setRoom({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      }),
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type === "mlp:ready") setReady(true);
      if (event.data?.type === "mlp:select") {
        onSelect(event.data.index, {
          path: event.data.path,
          label: event.data.label,
        });
      }
      if (event.data?.type === "mlp:remove") {
        onRemove(event.data.section);
      }
      if (event.data?.type === "mlp:move") {
        onMove(event.data.section, event.data.position);
      }
      if (event.data?.type === "mlp:edit") {
        onEdit(
          event.data.index,
          { role: event.data.role, path: event.data.path },
          event.data.value,
        );
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [onSelect, onEdit, onMove, onRemove]);

  const publish = useCallback(() => {
    frame.current?.contentWindow?.postMessage(
      {
        type: "mlp:page",
        sections,
        theme,
        selected: selectedIndex,
        path: selectedPath,
        reveal,
        editable: editing && !isWorking,
        flags: flagsFor(readiness),
      },
      window.location.origin,
    );
  }, [
    sections,
    theme,
    readiness,
    selectedIndex,
    selectedPath,
    reveal,
    isWorking,
    editing,
  ]);

  useEffect(() => {
    if (ready) publish();
  }, [ready, publish]);

  const scale = deviceWidth ? Math.min(1, room.width / deviceWidth) : 1;
  const framed = deviceWidth !== null;

  return (
    <div className="panel flex h-full min-h-0 w-full flex-col overflow-hidden">
      <div className="flex shrink-0 flex-wrap items-center gap-x-2 gap-y-1.5 border-b border-ui-border px-2.5 py-2 sm:px-3">
        <span className="hidden shrink-0 gap-1.5 pl-1 lg:flex" aria-hidden>
          {["#f0625c", "#f6bd4f", "#61c554"].map((color) => (
            <span
              key={color}
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: color }}
            />
          ))}
        </span>

        <AddressBar
          pageUrl={pageUrl ?? null}
          live={live}
          isWorking={isWorking}
          onRename={onRename}
        />

        {pageUrl && (
          <EditToggle
            editing={editing}
            disabled={isWorking}
            onChange={setEditing}
          />
        )}

        {pageUrl && (
          <ReviewMenu
            readiness={readiness}
            disabled={isWorking}
            onJump={(index) => onSelect(index)}
            onApprove={(section) => onApprove?.(section)}
          />
        )}

        {pageUrl && (
          <PageActions
            published={published}
            hold={publishHold(readiness)}
            isPublishing={isPublishing}
            isWorking={isWorking}
            unsaved={unsaved}
            onSave={onSave}
            onUndo={onUndo}
            onPublish={onPublish}
          />
        )}

        <div className="hidden shrink-0 gap-0.5 rounded-lg bg-ui-inset p-0.5 sm:flex">
          {DEVICES.map(({ id, label, Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setDevice(id)}
              aria-pressed={device === id}
              aria-label={`${label} preview`}
              title={`${label} preview`}
              className={`flex h-7 w-8 items-center justify-center rounded-md transition-colors ${
                device === id
                  ? "bg-ui-surface text-ui-text shadow-[0_1px_2px_rgba(16,24,40,0.06)]"
                  : "text-ui-muted hover:text-ui-text"
              }`}
            >
              <Icon className="h-4 w-4" />
            </button>
          ))}
        </div>
      </div>

      <div
        ref={stage}
        className={`min-h-0 flex-1 overflow-hidden bg-ui-inset ${framed ? "p-2 sm:p-4" : ""}`}
      >
        <div
          className="mx-auto origin-top"
          style={
            framed
              ? {
                  width: deviceWidth ?? undefined,
                  height: room.height ? room.height / scale : "100%",
                  transform: `scale(${scale})`,
                }
              : { width: "100%", height: "100%" }
          }
        >
          <iframe
            ref={frame}
            src="/preview"
            title="Page preview"
            className={`h-full w-full border-0 bg-background ${
              framed
                ? "rounded-2xl shadow-[0_8px_30px_rgba(16,24,40,0.14)] ring-1 ring-ui-border-strong"
                : ""
            }`}
          />
        </div>
      </div>
    </div>
  );
}
