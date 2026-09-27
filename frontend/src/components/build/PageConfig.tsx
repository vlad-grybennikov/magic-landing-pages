"use client";

import { useState } from "react";
import type { Theme } from "@/types/sections";
import type { Brief, PageVersion } from "@/data/build-mock";
import { UnderstoodPanel } from "./UnderstoodPanel";
import { ThemePanel } from "./ThemePanel";
import { VersionHistory } from "./VersionHistory";

type Tab = "brief" | "palette" | "history";

const TABS: { id: Tab; label: string }[] = [
  { id: "brief", label: "Brief" },
  { id: "palette", label: "Theme" },
  { id: "history", label: "History" },
];

export function PageConfig({
  brief,
  onBriefChange,
  theme,
  versions,
  isWorking,
  onPreviewTheme,
  onCommitTheme,
  onRestore,
  previewing,
  onPreviewVersion,
}: {
  brief: Brief;
  onBriefChange: (brief: Brief) => void;
  theme: Theme | null;
  versions?: PageVersion[];
  isWorking: boolean;
  onPreviewTheme: (theme: Theme) => void;
  onCommitTheme: (colors: Record<string, string>) => void;
  onRestore: (version: number) => void;
  previewing?: number;
  onPreviewVersion?: (version?: number) => void;
}) {
  const [tab, setTab] = useState<Tab>("brief");

  return (
    <section className="panel flex shrink-0 flex-col overflow-hidden lg:h-[19rem]">
      <div className="flex shrink-0 gap-1 border-b border-ui-border p-1.5">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            aria-pressed={tab === id}
            className={`flex-1 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === id
                ? "bg-ui-accent-soft text-ui-accent"
                : "text-ui-muted hover:bg-ui-inset hover:text-ui-text"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 p-3 lg:overflow-y-auto">
        {tab === "brief" && (
          <UnderstoodPanel
            brief={brief}
            isWorking={isWorking}
            onChange={onBriefChange}
          />
        )}
        {tab === "palette" && (
          <ThemePanel
            theme={theme}
            isWorking={isWorking}
            onPreview={onPreviewTheme}
            onCommit={onCommitTheme}
          />
        )}
        {tab === "history" && (
          <VersionHistory
            versions={versions}
            previewing={previewing}
            onPreview={onPreviewVersion}
            onRestore={onRestore}
            isWorking={isWorking}
          />
        )}
      </div>
    </section>
  );
}
