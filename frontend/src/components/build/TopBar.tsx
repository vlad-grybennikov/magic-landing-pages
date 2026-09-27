"use client";

import { useEffect, useRef, useState } from "react";
import type { AuthUser } from "@/lib/auth";
import type { BuildSummary } from "@/lib/builds";
import { BuildMenu } from "./BuildMenu";
import { LogOutIcon, PanelsIcon, SparklesIcon } from "./icons";

export function TopBar({
  builds,
  buildId,
  buildTitle,
  pageUrl,
  pageName,
  published,
  busy,
  user,
  canSignOut,
  showPanelsToggle = false,
  panelsOpen = false,
  panelsMarked = false,
  onTogglePanels,
  onOpenBuild,
  onNewBuild,
  onOpenMenu,
  onSignOut,
}: {
  builds: BuildSummary[];
  buildId: string | null;
  buildTitle: string;
  pageUrl: string | null;
  pageName: string | null;
  published: boolean;
  busy: boolean;
  user: AuthUser | null;
  canSignOut: boolean;
  showPanelsToggle?: boolean;
  panelsOpen?: boolean;
  panelsMarked?: boolean;
  onTogglePanels?: () => void;
  onOpenBuild: (id: string) => void;
  onNewBuild: () => void;
  onOpenMenu: () => void;
  onSignOut: () => void;
}) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-1.5 border-b border-ui-border bg-ui-surface px-2.5 sm:gap-2 sm:px-3 lg:px-4">
      <div className="flex shrink-0 items-center gap-2.5 pr-1">
        <span className="brand-gradient flex h-7 w-7 items-center justify-center rounded-lg text-white">
          <SparklesIcon className="h-4 w-4" />
        </span>
        <span className="hidden text-sm font-semibold tracking-tight lg:inline">
          Magic Landing Pages
        </span>
      </div>

      <span className="hidden h-4 w-px shrink-0 bg-ui-border sm:block" aria-hidden />

      <BuildMenu
        builds={builds}
        currentId={buildId}
        title={buildTitle}
        onOpen={onOpenBuild}
        onCreate={onNewBuild}
        onOpenMenu={onOpenMenu}
        disabled={busy}
      />

      {pageUrl && (
        <div className="mx-auto hidden min-w-0 items-center gap-2 rounded-lg bg-ui-inset px-3 py-1.5 md:flex">
          <span
            className={`h-1.5 w-1.5 shrink-0 rounded-full ${
              published ? "bg-emerald-500" : "bg-ui-border-strong"
            }`}
            title={published ? "Live" : "Draft"}
          />
          {pageName && (
            <span className="truncate text-sm font-medium">{pageName}</span>
          )}
          <span className="truncate text-xs text-ui-faint">{pageUrl}</span>
        </div>
      )}

      <div className="ml-auto flex shrink-0 items-center gap-1.5">
        {showPanelsToggle && (
          <button
            type="button"
            onClick={onTogglePanels}
            aria-expanded={panelsOpen}
            aria-label={panelsOpen ? "Hide the editing panels" : "Show the editing panels"}
            title={panelsOpen ? "Hide the editing panels" : "Show the editing panels"}
            className={`relative hidden h-8 w-8 items-center justify-center rounded-lg transition-colors sm:flex lg:hidden ${
              panelsOpen
                ? "bg-ui-accent-soft text-ui-accent"
                : "text-ui-muted hover:bg-ui-inset hover:text-ui-text"
            }`}
          >
            <PanelsIcon className="h-4 w-4" />
            {panelsMarked && !panelsOpen && (
              <span
                aria-hidden
                className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-ui-accent"
              />
            )}
          </button>
        )}

        {user && (
          <AccountMenu
            user={user}
            canSignOut={canSignOut}
            onSignOut={onSignOut}
          />
        )}
      </div>
    </header>
  );
}

function AccountMenu({
  user,
  canSignOut,
  onSignOut,
}: {
  user: AuthUser;
  canSignOut: boolean;
  onSignOut: () => void;
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

  const initial = (user.name ?? user.email ?? "?")
    .trim()
    .charAt(0)
    .toUpperCase();

  return (
    <div ref={menu} className="relative ml-1">
      <button
        type="button"
        onClick={() => setOpen((was) => !was)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account"
        className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full bg-ui-inset text-xs font-semibold text-ui-muted ring-1 ring-ui-border transition-shadow hover:ring-ui-border-strong"
      >
        {user.picture ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={user.picture}
            alt=""
            className="h-full w-full object-cover"
          />
        ) : (
          initial
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-30 mt-1.5 w-56 overflow-hidden rounded-xl border border-ui-border bg-ui-surface shadow-[0_12px_32px_rgba(16,24,40,0.12)]">
          <div className="border-b border-ui-border px-3 py-2.5">
            {user.name && (
              <p className="truncate text-sm font-medium">{user.name}</p>
            )}
            <p className="truncate text-xs text-ui-faint">{user.email}</p>
          </div>
          {canSignOut ? (
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                onSignOut();
              }}
              className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm transition-colors hover:bg-ui-inset"
            >
              <LogOutIcon className="h-3.5 w-3.5 text-ui-faint" />
              Sign out
            </button>
          ) : (
            <p className="px-3 py-2.5 text-xs text-ui-faint">
              Sign-in is off -- running as a local user.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
