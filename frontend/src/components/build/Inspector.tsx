"use client";

import type { Section } from "@/types/sections";
import { SectionControls } from "./SectionControls";
import { ComponentTree, ElementFields, crumbsFor } from "./ComponentTree";
import { SECTION_LABELS } from "@/lib/sections";
import { ApproveButton, type SectionIssue } from "./ReviewMenu";

export function Inspector({
  section,
  issue = null,
  onApprove,
  isWorking = false,
  onSetVariant,
  onAddItem,
  onRemoveItem,
  onMoveItem,
  selectedPath,
  onSelectElement,
  onEditPath,
  onPick,
}: {
  section?: Section;
  issue?: SectionIssue | null;
  onApprove?: (section: string) => void;
  isWorking?: boolean;
  onSetVariant?: (variant: string) => void;
  onAddItem?: (path?: string) => void;
  onRemoveItem?: (path: string) => void;
  onMoveItem?: (path: string, to: number) => void;
  selectedPath?: string;
  onSelectElement?: (path?: string) => void;
  onEditPath?: (path: string, value: string) => void;
  onPick?: (path: string, kind: "image" | "icon") => void;
}) {
  return (
    <section className="panel flex min-h-0 shrink-0 flex-col overflow-hidden lg:flex-1 lg:shrink">
      <div className="min-h-0 flex-1 lg:overflow-y-auto">
        {section ? (
          <>
            <div className="flex flex-wrap items-center gap-1 border-b border-ui-border px-4 py-2.5 text-[11px] text-ui-faint">
              <button
                type="button"
                onClick={() => onSelectElement?.(undefined)}
                className="hover:text-ui-text"
              >
                Page
              </button>
              <span aria-hidden>›</span>
              <button
                type="button"
                onClick={() => onSelectElement?.(undefined)}
                className={
                  selectedPath
                    ? "hover:text-ui-text"
                    : "font-medium text-ui-text"
                }
              >
                {SECTION_LABELS[section.type]}
              </button>
              {crumbsFor(section, selectedPath).map((crumb, i, trail) => (
                <span key={crumb.path} className="contents">
                  <span aria-hidden>›</span>
                  {i < trail.length - 1 ? (
                    <button
                      type="button"
                      onClick={() => onSelectElement?.(crumb.path)}
                      className="hover:text-ui-text"
                    >
                      {crumb.label}
                    </button>
                  ) : (
                    <span className="font-medium text-ui-text">
                      {crumb.label}
                    </span>
                  )}
                </span>
              ))}
            </div>

            {issue && (
              <div
                className={`flex items-center gap-2 border-b border-ui-border py-1.5 pl-4 pr-2 text-xs leading-5 ${
                  issue.flag === "placeholder" ? "text-ui-danger" : "text-ui-muted"
                }`}
              >
                <span
                  aria-hidden
                  className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                    issue.flag === "placeholder" ? "bg-ui-danger" : "bg-ui-border-strong"
                  }`}
                />
                <span className="min-w-0 flex-1 truncate">
                  {issue.flag === "placeholder"
                    ? `${issue.issue.reason}. Write yours or remove the section.`
                    : issue.issue.reason}
                </span>
                {issue.flag === "review" && onApprove && (
                  <ApproveButton
                    disabled={isWorking}
                    onClick={() => onApprove(section.type)}
                  />
                )}
              </div>
            )}

            {onSelectElement && (
              <div className="border-b border-ui-border px-2 py-2">
                <ComponentTree
                  section={section}
                  selected={selectedPath}
                  disabled={isWorking}
                  onSelect={onSelectElement}
                  onAddItem={onAddItem}
                  onRemoveItem={onRemoveItem}
                  onMoveItem={onMoveItem}
                />
              </div>
            )}

            {selectedPath && onEditPath ? (
              <div className="px-4 py-2">
                <ElementFields
                  key={`${section.type}:${selectedPath}`}
                  section={section}
                  path={selectedPath}
                  disabled={isWorking}
                  onEdit={onEditPath}
                  onPick={onPick}
                />
              </div>
            ) : (
              <>
                {onSetVariant && (
                  <div className="px-4 pt-4">
                    <SectionControls
                      section={section}
                      disabled={isWorking}
                      onVariant={onSetVariant}
                      onAnchor={
                        onEditPath && ((anchor) => onEditPath("anchor", anchor))
                      }
                    />
                  </div>
                )}
              </>
            )}
          </>
        ) : (
          <p className="p-4 text-sm text-ui-muted">
            Select a section in the preview to edit it.
          </p>
        )}
      </div>
    </section>
  );
}
