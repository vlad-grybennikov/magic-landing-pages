"use client";

import NextImage from "next/image";
import type { Section } from "@/types/sections";
import { LIST_FIELDS, SECTION_LABELS } from "@/lib/sections";

export function fieldsOf(section: Section): Record<string, unknown> {
  return section as unknown as Record<string, unknown>;
}

const NOT_A_PART = new Set(["type", "variant", "anchor", "provenance", "reviewed"]);

const PART_LABELS: Record<string, string> = {
  headline: "Heading",
  heading: "Heading",
  title: "Heading",
  subhead: "Description",
  description: "Description",
  eyebrow: "Eyebrow",
  button: "Primary button",
  secondary: "Secondary button",
  image: "Image",
  icon: "Icon",
  name: "Name",
  tagline: "Tagline",
  href: "Links to",
  links_label: "Links label",
  contacts_label: "Contacts label",
};

export function partLabel(field: string) {
  return PART_LABELS[field] ?? field[0].toUpperCase() + field.slice(1);
}

export type NodeKind =
  "text" | "number" | "button" | "picture" | "list" | "entry";

export function kindOf(value: unknown): NodeKind | undefined {
  if (typeof value === "string") return "text";
  if (typeof value === "number") return "number";
  if (!value || typeof value !== "object") return undefined;
  if (Array.isArray(value)) return "list";
  const object = value as Record<string, unknown>;
  if ("src" in object) return "picture";
  const keys = Object.keys(object).filter((key) => object[key] != null);
  if (
    "label" in object &&
    keys.every((key) => key === "label" || key === "href")
  )
    return "button";
  return "entry";
}

export function childrenOf(value: unknown): string[] {
  if (!value || typeof value !== "object" || Array.isArray(value)) return [];
  return Object.entries(value as Record<string, unknown>)
    .filter(([field, child]) => !NOT_A_PART.has(field) && kindOf(child))
    .map(([field]) => field);
}

export function nodeFor(section: Section, path: string): string {
  const steps = path.split(".");
  if (steps.length > 1) {
    const parent = steps.slice(0, -1).join(".");
    if (kindOf(valueAt(section, parent)) === "button") return parent;
  }
  return path;
}

export function valueAt(section: Section, path: string): unknown {
  return path.split(".").reduce<unknown>((node, step) => {
    if (Array.isArray(node)) return node[Number(step)];
    if (node && typeof node === "object") {
      return (node as Record<string, unknown>)[step];
    }
    return undefined;
  }, fieldsOf(section));
}

export function entryLabel(entry: unknown, fallback: string): string {
  if (typeof entry === "string") return entry;
  if (entry && typeof entry === "object") {
    for (const key of ["title", "name", "question", "label", "value", "alt"]) {
      const value = (entry as Record<string, unknown>)[key];
      if (typeof value === "string" && value.trim()) return value;
    }
  }
  return fallback;
}

export function ComponentTree({
  section,
  selected,
  disabled,
  onSelect,
  onAddItem,
  onRemoveItem,
  onMoveItem,
}: {
  section: Section;
  selected?: string;
  disabled: boolean;
  onSelect: (path?: string) => void;
  onAddItem?: (path?: string) => void;
  onRemoveItem?: (path: string) => void;
  onMoveItem?: (path: string, to: number) => void;
}) {
  const primary = LIST_FIELDS[section.type]?.[0];
  const data = fieldsOf(section);

  const rowClass = (active: boolean, depth: number) =>
    `flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 text-left transition-colors ${
      depth > 1 ? "py-1 text-[11px]" : "py-1.5 text-xs"
    } ${
      active
        ? "bg-ui-accent-soft font-medium text-ui-accent"
        : depth > 1
          ? "text-ui-faint hover:bg-ui-inset"
          : "text-ui-muted hover:bg-ui-inset"
    }`;

  const nounFor = (listField: string) =>
    listField === primary
      ? (LIST_FIELDS[section.type]?.[1] ?? "Item")
      : partLabel(listField).replace(/s$/, "");

  const controls = (
    listPath: string,
    i: number,
    count: number,
    noun: string,
  ) => (
    <span className="flex shrink-0 opacity-0 transition-opacity group-hover:opacity-100">
      {onMoveItem && count > 1 && (
        <>
          <button
            type="button"
            disabled={disabled || i === 0}
            onClick={() => onMoveItem(`${listPath}.${i}`, i - 1)}
            aria-label={`Move ${noun.toLowerCase()} ${i + 1} up`}
            title="Move up"
            className="rounded px-1 text-ui-faint hover:text-ui-text disabled:opacity-30"
          >
            ↑
          </button>
          <button
            type="button"
            disabled={disabled || i === count - 1}
            onClick={() => onMoveItem(`${listPath}.${i}`, i + 1)}
            aria-label={`Move ${noun.toLowerCase()} ${i + 1} down`}
            title="Move down"
            className="rounded px-1 text-ui-faint hover:text-ui-text disabled:opacity-30"
          >
            ↓
          </button>
        </>
      )}
      {onRemoveItem && (
        <button
          type="button"
          disabled={disabled}
          onClick={() => onRemoveItem(`${listPath}.${i}`)}
          aria-label={`Remove ${noun.toLowerCase()} ${i + 1}`}
          title={`Remove ${noun.toLowerCase()}`}
          className="rounded px-1 text-ui-faint hover:text-ui-danger disabled:opacity-30"
        >
          ×
        </button>
      )}
    </span>
  );

  const adder = (listPath: string | undefined, noun: string, depth: number) =>
    onAddItem && (
      <button
        type="button"
        disabled={disabled}
        onClick={() => onAddItem(listPath)}
        style={{ paddingLeft: depth * 16 + 8 }}
        className="rounded-md py-1.5 text-left text-xs text-ui-accent hover:bg-ui-inset disabled:opacity-40"
      >
        + Add {noun.toLowerCase()}
      </button>
    );

  const node = (
    path: string,
    label: string,
    value: unknown,
    depth: number,
    trailing?: React.ReactNode,
  ): React.ReactNode => {
    const kind = kindOf(value);
    const children =
      kind === "entry"
        ? childrenOf(value)
        : kind === "list"
          ? (value as unknown[]).map((_, i) => String(i))
          : [];
    return (
      <div key={path} className="flex flex-col">
        <div
          className="group flex items-center gap-1"
          style={{ paddingLeft: depth * 16 }}
        >
          <button
            type="button"
            onClick={() => onSelect(path)}
            className={rowClass(selected === path, depth)}
          >
            <span aria-hidden className="shrink-0 text-ui-faint">
              ·
            </span>
            <span className="truncate">{label}</span>
          </button>
          {trailing}
        </div>
        {children.map((child) => {
          const childValue = (value as Record<string, unknown> | unknown[])[
            child as keyof typeof value
          ];
          const childLabel = /^\d+$/.test(child)
            ? entryLabel(
                childValue,
                `${partLabel(path.split(".").pop() ?? "")} ${Number(child) + 1}`,
              )
            : partLabel(child);
          return node(`${path}.${child}`, childLabel, childValue, depth + 1);
        })}
      </div>
    );
  };

  const entries = (listPath: string, list: unknown[], depth: number) => {
    const noun = nounFor(listPath);
    return (
      <>
        {list.map((entry, i) =>
          node(
            `${listPath}.${i}`,
            entryLabel(entry, `${noun} ${i + 1}`),
            entry,
            depth,
            controls(listPath, i, list.length, noun),
          ),
        )}
        {adder(listPath === primary ? undefined : listPath, noun, depth)}
        {list.length === 0 && (
          <p
            className="text-xs text-ui-faint"
            style={{ paddingLeft: depth * 16 + 8 }}
          >
            No {noun.toLowerCase()}s yet.
          </p>
        )}
      </>
    );
  };

  const group = (listField: string, list: unknown[]) => {
    const labelField = `${listField}_label`;
    const heading = data[labelField];
    return (
      <div key={listField} className="flex flex-col">
        <div
          className="group flex items-center gap-1"
          style={{ paddingLeft: 16 }}
        >
          <button
            type="button"
            onClick={() => onSelect(listField)}
            className={rowClass(selected === listField, 1)}
          >
            <span aria-hidden className="shrink-0 text-ui-faint">
              ·
            </span>
            <span className="truncate">{partLabel(listField)}</span>
          </button>
        </div>
        {typeof heading === "string" && node(labelField, "Label", heading, 2)}
        {entries(listField, list, 2)}
      </div>
    );
  };

  const parts = childrenOf(section).filter(
    (part) =>
      part !== primary &&
      !(part.endsWith("_label") && Array.isArray(data[part.slice(0, -6)])),
  );

  return (
    <div className="flex flex-col gap-0.5">
      <button
        type="button"
        onClick={() => onSelect(undefined)}
        className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors ${
          selected
            ? "text-ui-muted hover:bg-ui-inset"
            : "bg-ui-accent-soft font-medium text-ui-accent"
        }`}
      >
        <span aria-hidden className="text-ui-faint">
          ▾
        </span>
        {SECTION_LABELS[section.type]}
      </button>

      {parts.map((part) =>
        Array.isArray(data[part])
          ? group(part, data[part] as unknown[])
          : node(part, partLabel(part), data[part], 1),
      )}

      {primary && entries(primary, (data[primary] as unknown[]) ?? [], 1)}
    </div>
  );
}

export function crumbsFor(
  section: Section,
  path?: string,
): Array<{ path: string; label: string }> {
  if (!path) return [];
  const steps = path.split(".");
  const trail: Array<{ path: string; label: string }> = [];
  for (let i = 0; i < steps.length; i++) {
    const step = steps[i];
    const at = steps.slice(0, i + 1).join(".");
    const next = steps[i + 1];
    if (Array.isArray(valueAt(section, at)) && /^\d+$/.test(next ?? ""))
      continue;
    if (/^\d+$/.test(step)) {
      const owner = steps[i - 1];
      trail.push({
        path: at,
        label: entryLabel(
          valueAt(section, at),
          `${partLabel(owner)} ${Number(step) + 1}`,
        ),
      });
    } else {
      trail.push({ path: at, label: partLabel(step) });
    }
  }
  return trail;
}

export function pathLabel(section: Section, path?: string): string | undefined {
  return crumbsFor(section, path).at(-1)?.label;
}

export function isPicture(section: Section, path: string): boolean {
  const value = valueAt(section, path);
  return !!value && typeof value === "object" && "src" in value;
}

export function ElementFields({
  section,
  path,
  disabled,
  onEdit,
  onPick,
}: {
  section: Section;
  path: string;
  disabled: boolean;
  onEdit: (path: string, value: string) => void;
  onPick?: (path: string, kind: "image" | "icon") => void;
}) {
  const value = valueAt(section, path);

  if (value && typeof value === "object" && "src" in value) {
    const picture = value as { src: string; alt?: string; id?: string };
    const icon = picture.src.endsWith(".svg");
    return (
      <div className="flex flex-col gap-3 py-2">
        <div
          className={`relative overflow-hidden rounded-lg border border-ui-border bg-ui-inset ${
            icon ? "flex h-20 items-center justify-center" : "aspect-[16/9]"
          }`}
        >
          {icon ? (
            <span
              role="img"
              aria-label={picture.id ?? ""}
              className="h-8 w-8 bg-ui-text"
              style={{
                maskImage: `url(${picture.src})`,
                WebkitMaskImage: `url(${picture.src})`,
                maskRepeat: "no-repeat",
                WebkitMaskRepeat: "no-repeat",
                maskPosition: "center",
                WebkitMaskPosition: "center",
                maskSize: "contain",
                WebkitMaskSize: "contain",
              }}
            />
          ) : (
            <NextImage
              src={picture.src}
              alt={picture.alt ?? ""}
              fill
              sizes="320px"
              className="object-cover"
            />
          )}
        </div>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onPick?.(path, icon ? "icon" : "image")}
          className="self-start rounded-md border border-ui-border px-2.5 py-1 text-xs text-ui-text hover:bg-ui-inset disabled:opacity-40"
        >
          Replace {icon ? "icon" : "picture"}
        </button>
        {(icon ? picture.id : picture.alt) && (
          <p className="text-[11px] leading-snug text-ui-faint">
            {icon ? picture.id : picture.alt}
          </p>
        )}
      </div>
    );
  }

  if (typeof value === "number") {
    const name = path.split(".").pop() ?? "";
    if (name === "rating") {
      return (
        <div className="flex flex-col gap-1 py-2.5">
          <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-ui-faint">
            Rating
          </span>
          <div className="flex gap-1" role="radiogroup" aria-label="Rating">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                role="radio"
                aria-checked={n === value}
                aria-label={`${n} out of 5`}
                disabled={disabled}
                onClick={() => n !== value && onEdit(path, String(n))}
                className={`text-xl leading-none transition-colors disabled:opacity-40 ${
                  n <= value
                    ? "text-amber-500"
                    : "text-ui-border hover:text-amber-300"
                }`}
              >
                ★
              </button>
            ))}
          </div>
        </div>
      );
    }
    return (
      <label className="flex flex-col gap-1 py-2.5">
        <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-ui-faint">
          {partLabel(name)}
        </span>
        <input
          type="number"
          defaultValue={value}
          disabled={disabled}
          onBlur={(e) => {
            if (e.target.value !== "" && Number(e.target.value) !== value) {
              onEdit(path, e.target.value);
            }
          }}
          className="w-24 rounded-md border border-ui-border bg-ui-surface px-2 py-1 text-sm text-ui-text disabled:opacity-50"
        />
      </label>
    );
  }

  if (typeof value === "string") {
    return (
      <Row
        label={partLabel(path.split(".").pop() ?? "Text")}
        value={value}
        disabled={disabled}
        onCommit={(next) => onEdit(path, next)}
      />
    );
  }

  if (!value || typeof value !== "object") return null;

  const kind = kindOf(value);
  if (kind === "entry" || kind === "list") return null;

  const object = value as Record<string, unknown>;
  const fields = Object.keys(object).filter(
    (name) => typeof object[name] === "string" && !NOT_A_PART.has(name),
  );
  if ("label" in object && !fields.includes("href")) fields.push("href");

  if (fields.length === 0) {
    return (
      <p className="py-2 text-xs text-ui-faint">
        Nothing to type here -- this part is edited on the page.
      </p>
    );
  }

  return (
    <div className="flex flex-col">
      {fields.map((name) => (
        <Row
          key={name}
          label={partLabel(name)}
          value={
            typeof object[name] === "string" ? (object[name] as string) : ""
          }
          placeholder={name === "href" ? "https://… or #contact" : undefined}
          disabled={disabled}
          onCommit={(next) => onEdit(`${path}.${name}`, next)}
        />
      ))}
    </div>
  );
}

function Row({
  label,
  value,
  placeholder,
  disabled,
  onCommit,
}: {
  label: string;
  value: string;
  placeholder?: string;
  disabled: boolean;
  onCommit: (value: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 border-b border-ui-border py-2.5 last:border-b-0">
      <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-ui-faint">
        {label}
      </span>
      <textarea
        defaultValue={value}
        placeholder={placeholder}
        disabled={disabled}
        rows={value.length > 60 ? 3 : 1}
        onBlur={(e) => {
          if (e.target.value.trim() !== value.trim()) {
            onCommit(e.target.value.trim());
          }
        }}
        className="w-full resize-none rounded-md bg-transparent text-sm leading-6 text-ui-text focus:outline-none focus:ring-2 focus:ring-ui-accent/20 disabled:opacity-50"
      />
    </label>
  );
}
