"use client";

import type { ReactNode } from "react";
import type { Section, SectionOf, SectionType } from "@/types/sections";
import { SECTION_LABELS } from "@/data/build-mock";
import { Panel, inputClass } from "./Panel";

interface FieldSpec<S extends Section> {
  label: string;
  field: string;
  kind: "text" | "area";
  get: (section: S) => string;
  set: (section: S, value: string) => S;
}

function heading<S extends Section & { heading?: string }>(
  label = "Heading",
): FieldSpec<S> {
  return {
    label,
    field: "heading",
    kind: "text",
    get: (section) => section.heading ?? "",
    set: (section, heading) => ({ ...section, heading }),
  };
}

function subhead<S extends Section & { subhead?: string }>(): FieldSpec<S> {
  return {
    label: "Description",
    field: "subhead",
    kind: "area",
    get: (section) => section.subhead ?? "",
    set: (section, subhead) => ({ ...section, subhead }),
  };
}

function buttonLabel<
  S extends Section & { button: { label: string } },
>(): FieldSpec<S> {
  return {
    label: "Button",
    field: "button",
    kind: "text",
    get: (section) => section.button.label,
    set: (section, label) => ({
      ...section,
      button: { ...section.button, label },
    }),
  };
}

export interface FieldChange {
  section: SectionType;
  field: string;
  value: string;
}

export function changedFields(
  saved: Section[],
  current: Section[],
): FieldChange[] {
  const changes: FieldChange[] = [];

  current.forEach((section, i) => {
    const before = saved[i];
    if (!before || before.type !== section.type) return;

    const specs = FIELDS[section.type] as FieldSpec<Section>[];
    for (const spec of specs) {
      const value = spec.get(section);
      if (value !== spec.get(before)) {
        changes.push({ section: section.type, field: spec.field, value });
      }
    }
  });

  return changes;
}

const ROLE_FIELDS: Record<string, string[]> = {
  title: ["headline", "title", "heading", "name"],
  description: ["subhead", "description", "tagline"],
  eyebrow: ["eyebrow"],
  button: ["button"],
};

export function fieldForRole(
  section: Section,
  role: string,
): string | undefined {
  const fields = section as unknown as Record<string, unknown>;
  return (ROLE_FIELDS[role] ?? [role]).find((field) => field in fields);
}

export function editByRole(
  section: Section,
  role: string,
  value: string,
): Section | null {
  const specs = FIELDS[section.type] as FieldSpec<Section>[];
  for (const field of ROLE_FIELDS[role] ?? [role]) {
    const spec = specs.find((candidate) => candidate.field === field);
    if (spec) return spec.set(section, value);
  }
  return null;
}

const FIELDS: { [T in SectionType]: FieldSpec<SectionOf<T>>[] } = {
  header: [
    {
      label: "Name",
      field: "name",
      kind: "text",
      get: (section) => section.name,
      set: (section, name) => ({ ...section, name }),
    },
  ],
  footer: [
    {
      label: "Name",
      field: "name",
      kind: "text",
      get: (section) => section.name,
      set: (section, name) => ({ ...section, name }),
    },
    {
      label: "Tagline",
      field: "tagline",
      kind: "area",
      get: (section) => section.tagline ?? "",
      set: (section, tagline) => ({ ...section, tagline }),
    },
  ],
  hero: [
    {
      label: "Title",
      field: "headline",
      kind: "text",
      get: (section) => section.headline,
      set: (section, headline) => ({ ...section, headline }),
    },
    subhead(),
    buttonLabel(),
  ],
  about: [heading()],
  benefits: [heading(), subhead()],
  services: [heading(), subhead()],
  process: [heading(), subhead()],
  stats: [heading(), subhead()],
  gallery: [heading(), subhead()],
  testimonials: [heading(), subhead()],
  pricing: [heading(), subhead()],
  team: [heading(), subhead()],
  promotion: [
    {
      label: "Title",
      field: "title",
      kind: "text",
      get: (section) => section.title,
      set: (section, title) => ({ ...section, title }),
    },
    {
      label: "Description",
      field: "description",
      kind: "area",
      get: (section) => section.description,
      set: (section, description) => ({ ...section, description }),
    },
    buttonLabel(),
  ],
  faq: [heading(), subhead()],
  contact: [
    heading("Title"),
    {
      label: "Description",
      field: "description",
      kind: "area",
      get: (section) => section.description ?? "",
      set: (section, description) => ({ ...section, description }),
    },
  ],
  cta: [
    {
      label: "Title",
      field: "headline",
      kind: "text",
      get: (section) => section.headline,
      set: (section, headline) => ({ ...section, headline }),
    },
    subhead(),
    buttonLabel(),
  ],
};

export function EditPanel({
  section,
  onUpdate,
}: {
  section: Section;
  onUpdate: (next: Section) => void;
}) {
  const specs = FIELDS[section.type] as FieldSpec<Section>[];

  return (
    <Panel
      title="Section"
      aside={
        <span className="text-xs font-medium text-ui-text">
          {SECTION_LABELS[section.type]}
        </span>
      }
    >
      <div className="flex flex-col divide-y divide-ui-border">
        {specs.map((spec) => (
          <Field key={spec.field} label={spec.label}>
            {spec.kind === "area" ? (
              <TextArea
                value={spec.get(section)}
                onChange={(value) => onUpdate(spec.set(section, value))}
              />
            ) : (
              <TextInput
                value={spec.get(section)}
                onChange={(value) => onUpdate(spec.set(section, value))}
              />
            )}
          </Field>
        ))}
      </div>
    </Panel>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="py-2.5 first:pt-0 last:pb-0">
      <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-[0.06em] text-ui-faint">
        {label}
      </span>
      {children}
    </div>
  );
}

function TextInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={inputClass}
    />
  );
}

function TextArea({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      rows={2}
      className={`${inputClass} resize-none`}
    />
  );
}
