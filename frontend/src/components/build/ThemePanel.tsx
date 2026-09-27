"use client";

import { useState } from "react";
import type { Theme } from "@/types/sections";
import { HexColorInput, HexColorPicker } from "react-colorful";
import { BRAND_COLORS, HEX } from "@/lib/theme";
import { FONT_PAIRS, FONT_PAIR_NAMES } from "@/lib/fonts";

export function ThemePanel({
  theme,
  isWorking,
  onPreview,
  onCommit,
}: {
  theme: Theme | null;
  isWorking: boolean;
  onPreview: (theme: Theme) => void;
  onCommit: (colors: Record<string, string>) => void;
}) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  return (
    <div>
      {theme ? (
        <>
          <FontRow
            value={theme.font ?? null}
            disabled={isWorking}
            onPreview={(font) => onPreview({ ...theme, font })}
            onCommit={(font) => onCommit({ font })}
          />

          <div className="mt-4 flex flex-col gap-3">
            {BRAND_COLORS.map(({ key, label, hint }) => (
              <ColorRow
                key={key}
                label={label}
                hint={hint}
                value={theme[key]}
                disabled={isWorking}
                open={openKey === key}
                onOpen={() => setOpenKey(openKey === key ? null : key)}
                onPreview={(value) => onPreview({ ...theme, [key]: value })}
                onCommit={(value) => onCommit({ [key]: value })}
              />
            ))}
          </div>
        </>
      ) : (
        <p className="text-sm text-ui-muted">
          No palette yet -- this page renders in the default colours.
        </p>
      )}
    </div>
  );
}

function FontRow({
  value,
  disabled,
  onPreview,
  onCommit,
}: {
  value: string | null;
  disabled: boolean;
  onPreview: (font: string) => void;
  onCommit: (font: string) => void;
}) {
  return (
    <label className="mt-4 flex flex-col gap-1.5">
      <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-ui-faint">
        Typeface
      </span>
      <select
        value={value ?? ""}
        disabled={disabled}
        onChange={(e) => {
          onPreview(e.target.value);
          onCommit(e.target.value);
        }}
        className="w-full rounded-lg border border-ui-border bg-ui-surface px-2.5 py-1.5 text-sm text-ui-text disabled:opacity-50"
      >
        {value === null && <option value="">Default</option>}
        {FONT_PAIR_NAMES.map((name) => (
          <option key={name} value={name}>
            {FONT_PAIRS[name].label}
          </option>
        ))}
      </select>
    </label>
  );
}

function ColorRow({
  label,
  hint,
  value,
  disabled,
  open,
  onOpen,
  onPreview,
  onCommit,
}: {
  label: string;
  hint: string;
  value: string;
  disabled: boolean;
  open: boolean;
  onOpen: () => void;
  onPreview: (value: string) => void;
  onCommit: (value: string) => void;
}) {
  const [draft, setDraft] = useState(value);
  const [applied, setApplied] = useState(value);
  if (applied !== value) {
    setApplied(value);
    setDraft(value);
  }

  const commit = (next: string) => {
    if (!HEX.test(next)) {
      setDraft(value);
      return;
    }
    if (next.toLowerCase() !== value.toLowerCase()) onCommit(next);
  };

  const drag = (next: string) => {
    setDraft(next);
    onPreview(next);
  };

  return (
    <div className={open ? "rounded-xl bg-ui-inset p-2" : ""}>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => {
            if (open) commit(draft);
            onOpen();
          }}
          disabled={disabled}
          aria-expanded={open}
          aria-label={`Choose the ${label.toLowerCase()} colour`}
          className={`h-9 w-9 shrink-0 rounded-lg border transition-shadow disabled:opacity-50 ${
            open
              ? "border-ui-accent ring-2 ring-ui-accent/20"
              : "border-ui-border hover:border-ui-border-strong"
          }`}
          style={{ backgroundColor: HEX.test(draft) ? draft : value }}
        />

        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-ui-text">{label}</p>
          <p className="truncate text-xs text-ui-muted">{hint}</p>
        </div>

        <div className="flex shrink-0 items-center rounded-md border border-ui-border bg-ui-surface pl-1.5 focus-within:border-ui-accent focus-within:ring-2 focus-within:ring-ui-accent/15">
          <span className="text-xs text-ui-faint">#</span>
          <HexColorInput
            color={HEX.test(draft) ? draft : value}
            onChange={setDraft}
            onBlur={() => commit(draft)}
            disabled={disabled}
            className="w-14 bg-transparent px-1 py-1 text-xs uppercase text-ui-text outline-none"
          />
        </div>
      </div>

      {open && (
        <div className="mt-2.5 flex flex-col gap-2">
          <div onPointerUp={() => commit(draft)}>
            <HexColorPicker
              color={HEX.test(draft) ? draft : value}
              onChange={drag}
              className="mlp-picker"
            />
          </div>
          <div className="flex gap-1.5">
            {shades(HEX.test(draft) ? draft : value).map((shade) => (
              <button
                key={shade}
                type="button"
                onClick={() => {
                  drag(shade);
                  commit(shade);
                }}
                title={shade}
                aria-label={shade}
                className="h-5 flex-1 rounded border border-black/5 transition-transform hover:scale-105"
                style={{ backgroundColor: shade }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function shades(hex: string): string[] {
  const [r, g, b] = [1, 3, 5].map((i) =>
    parseInt(expand(hex).slice(i, i + 2), 16),
  );
  return [-0.45, -0.25, 0, 0.25, 0.45].map((amount) => {
    const towards = amount < 0 ? 0 : 255;
    const weight = Math.abs(amount);
    const mix = (channel: number) =>
      Math.round(channel + (towards - channel) * weight);
    return (
      "#" +
      [mix(r), mix(g), mix(b)]
        .map((c) => c.toString(16).padStart(2, "0"))
        .join("")
    );
  });
}

function expand(hex: string) {
  if (hex.length !== 4) return hex;
  return "#" + [...hex.slice(1)].map((c) => c + c).join("");
}
