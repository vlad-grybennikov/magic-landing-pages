"use client";

import { useEffect, useRef, useState } from "react";
import type { Readiness, ReadinessIssue } from "@/lib/orchestrator";
import { SECTION_LABELS } from "@/lib/sections";
import type { SectionType } from "@/types/sections";
import { ChevronIcon } from "./icons";

export type Flag = "placeholder" | "review";

export interface SectionIssue {
  issue: ReadinessIssue;
  flag: Flag;
}

export function flagsFor(readiness: Readiness | null): Record<number, Flag> {
  const flags: Record<number, Flag> = {};
  for (const issue of readiness?.warnings ?? []) flags[issue.index] = "review";
  for (const issue of readiness?.blocking ?? []) flags[issue.index] = "placeholder";
  return flags;
}

export function issueFor(
  readiness: Readiness | null,
  index: number,
): SectionIssue | null {
  const blocking = readiness?.blocking.find((issue) => issue.index === index);
  if (blocking) return { issue: blocking, flag: "placeholder" };
  const warning = readiness?.warnings.find((issue) => issue.index === index);
  return warning ? { issue: warning, flag: "review" } : null;
}

export function label(kind: string) {
  return SECTION_LABELS[kind as SectionType] ?? kind;
}

export function describe(issue: ReadinessIssue): string {
  return `${label(issue.section)} (${issue.reason.toLowerCase()})`;
}

export function ApproveButton({
  onClick,
  disabled,
  className = "",
}: {
  onClick: () => void;
  disabled: boolean;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={(event) => {
        event.stopPropagation();
        onClick();
      }}
      disabled={disabled}
      title="Keep it as it is and stop flagging it"
      className={`shrink-0 rounded-md px-2 py-1 text-xs font-medium text-ui-accent transition-colors hover:bg-ui-accent-soft disabled:opacity-50 ${className}`}
    >
      Approve
    </button>
  );
}

export function ReviewMenu({
  readiness,
  disabled,
  onJump,
  onApprove,
}: {
  readiness: Readiness | null;
  disabled: boolean;
  onJump: (index: number) => void;
  onApprove: (section: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLDivElement>(null);
  const blocking = readiness?.blocking ?? [];
  const warnings = readiness?.warnings ?? [];
  const count = blocking.length + warnings.length;

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!menu.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  if (count === 0) return null;
  const blocked = blocking.length > 0;

  return (
    <div ref={menu} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((was) => !was)}
        disabled={disabled}
        aria-haspopup="menu"
        aria-expanded={open}
        title={
          blocked
            ? "Some sections need real content"
            : "Approve these sections before publishing"
        }
        className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 ${
          blocked
            ? "bg-ui-danger-soft text-ui-danger hover:brightness-95"
            : "bg-ui-inset text-ui-muted hover:text-ui-text"
        }`}
      >
        <span
          aria-hidden
          className={`h-1.5 w-1.5 rounded-full ${
            blocked ? "bg-ui-danger" : "bg-ui-border-strong"
          }`}
        />
        {count} to {blocked ? "fix" : "review"}
        <ChevronIcon className="h-3 w-3 opacity-60" />
      </button>

      {open && (
        <div className="absolute right-0 z-30 mt-1.5 w-[min(20rem,calc(100vw-1.5rem))] overflow-hidden rounded-xl border border-ui-border bg-ui-surface shadow-[0_12px_32px_rgba(16,24,40,0.12)]">
          <Group
            title="Fix before publishing"
            issues={blocking}
            tone="placeholder"
            disabled={disabled}
            onJump={(index) => {
              setOpen(false);
              onJump(index);
            }}
          />
          <Group
            title="Approve before publishing"
            issues={warnings}
            tone="review"
            disabled={disabled}
            onJump={(index) => {
              setOpen(false);
              onJump(index);
            }}
            onApprove={onApprove}
          />
        </div>
      )}
    </div>
  );
}

function Group({
  title,
  issues,
  tone,
  disabled,
  onJump,
  onApprove,
}: {
  title: string;
  issues: ReadinessIssue[];
  tone: Flag;
  disabled: boolean;
  onJump: (index: number) => void;
  onApprove?: (section: string) => void;
}) {
  if (issues.length === 0) return null;
  return (
    <div className="border-b border-ui-border last:border-b-0">
      <p className="px-3 pb-1 pt-2.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-ui-faint">
        {title}
      </p>
      <ul className="pb-1.5">
        {issues.map((issue) => (
          <li
            key={`${issue.section}-${issue.index}`}
            className="flex items-start gap-1 pr-2 transition-colors hover:bg-ui-inset"
          >
            <button
              type="button"
              onClick={() => onJump(issue.index)}
              className="flex min-w-0 flex-1 items-start gap-2.5 px-3 py-2 text-left"
            >
              <span
                aria-hidden
                className={`mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full ${
                  tone === "placeholder" ? "bg-ui-danger" : "bg-ui-border-strong"
                }`}
              />
              <span className="min-w-0">
                <span className="block text-sm font-medium text-ui-text">
                  {label(issue.section)}
                </span>
                <span className="block text-xs leading-5 text-ui-muted">
                  {issue.reason}
                </span>
              </span>
            </button>
            {onApprove && (
              <ApproveButton
                className="mt-2"
                disabled={disabled}
                onClick={() => onApprove(issue.section)}
              />
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
