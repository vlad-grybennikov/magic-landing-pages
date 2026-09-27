"use client";

import type { Section } from "@/types/sections";
import { variantNames } from "@/components/sections/registry";

const slug = (text: string) =>
  text
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

export function SectionControls({
  section,
  disabled,
  onVariant,
  onAnchor,
}: {
  section: Section;
  disabled: boolean;
  onVariant: (variant: string) => void;
  onAnchor?: (anchor: string) => void;
}) {
  const variants = variantNames(section.type) as string[];
  const anchor = section.anchor ?? section.type;

  const commit = (input: HTMLInputElement) => {
    const next = slug(input.value);
    if (!next || next === anchor) {
      input.value = anchor;
      return;
    }
    onAnchor?.(next);
  };

  return (
    <div className="flex flex-col gap-3 border-b border-ui-border pb-4">
      {variants.length > 1 && (
        <label className="flex flex-col gap-1.5">
          <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-ui-faint">
            Layout
          </span>
          <select
            value={section.variant ?? ""}
            disabled={disabled}
            onChange={(e) => onVariant(e.target.value)}
            className="w-full rounded-lg border border-ui-border bg-ui-surface px-2.5 py-1.5 text-sm text-ui-text disabled:opacity-50"
          >
            {!section.variant && <option value="">Default</option>}
            {variants.map((variant) => (
              <option key={variant} value={variant}>
                {variant}
              </option>
            ))}
          </select>
        </label>
      )}

      {onAnchor && (
        <label className="flex flex-col gap-1.5">
          <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-ui-faint">
            Anchor
          </span>
          <span className="flex items-center rounded-lg border border-ui-border bg-ui-surface text-sm text-ui-text focus-within:border-ui-accent">
            <span className="pl-2.5 text-ui-faint">#</span>
            <input
              key={anchor}
              type="text"
              defaultValue={anchor}
              disabled={disabled}
              onBlur={(e) => commit(e.currentTarget)}
              onKeyDown={(e) => {
                if (e.key === "Enter") e.currentTarget.blur();
                if (e.key === "Escape") {
                  e.currentTarget.value = anchor;
                  e.currentTarget.blur();
                }
              }}
              spellCheck={false}
              className="min-w-0 flex-1 bg-transparent px-1.5 py-1.5 outline-none disabled:opacity-50"
            />
          </span>
        </label>
      )}
    </div>
  );
}
