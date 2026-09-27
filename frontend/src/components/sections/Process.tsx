import type { ComponentType } from "react";
import type {
  ProcessSection,
  ProcessStep,
  ProcessVariant,
} from "@/types/sections";
import {
  at,
  el,
  Card,
  CONTENT,
  Glyph,
  GlyphTile,
  gridCols,
  Heading,
  Lede,
  Numeral,
  PAD,
  SectionHead,
  SectionShell,
  TEXT,
} from "@/components/ui";
import { rich } from "@/lib/richtext";

function StepBody({
  step,
  path,
  align = "left",
}: {
  step: ProcessStep;
  path: string;
  align?: "left" | "center";
}) {
  return (
    <div
      className={`flex flex-col gap-2 ${
        align === "center" ? "items-center text-center" : ""
      }`}
    >
      <h3 {...at(`${path}.title`, step.title)} className="text-lg font-medium">
        {rich(step.title)}
      </h3>
      <p
        {...at(`${path}.caption`, step.caption)}
        className="text-pretty leading-relaxed text-muted-foreground"
      >
        {rich(step.caption)}
      </p>
    </div>
  );
}

function ProcessNumberedSteps({ heading, subhead, items }: ProcessSection) {
  return (
    <SectionShell type="process">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <ol className={`mt-14 grid gap-10 ${gridCols(items.length)}`}>
          {items.map((step, i) => (
            <li
              key={i}
              {...el(`items.${i}`, `Step ${i + 1}`)}
              className="flex flex-col items-center gap-4"
            >
              <Numeral n={i + 1} tone="solid" />
              <StepBody step={step} path={`items.${i}`} align="center" />
            </li>
          ))}
        </ol>
      </div>
    </SectionShell>
  );
}

function ProcessTimelineVertical({ heading, subhead, items }: ProcessSection) {
  return (
    <SectionShell type="process">
      <div className={`${TEXT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <ol className="mt-12 flex flex-col">
          {items.map((step, i) => (
            <li
              key={i}
              {...el(`items.${i}`, `Step ${i + 1}`)}
              className="grid grid-cols-[auto_1fr] gap-6"
            >
              <div className="flex flex-col items-center">
                <Numeral n={i + 1} />
                {i < items.length - 1 && (
                  <span aria-hidden className="my-1 w-px flex-1 bg-border" />
                )}
              </div>
              <div className={i < items.length - 1 ? "pb-10" : ""}>
                <StepBody step={step} path={`items.${i}`} />
              </div>
            </li>
          ))}
        </ol>
      </div>
    </SectionShell>
  );
}

function ProcessTimelineHorizontal({
  heading,
  subhead,
  items,
}: ProcessSection) {
  return (
    <SectionShell type="process" tone="muted">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className="relative mt-16">
          <span
            aria-hidden
            className="absolute left-0 right-0 top-5 hidden h-px bg-border lg:block"
          />
          <ol className={`relative grid gap-10 ${gridCols(items.length)}`}>
            {items.map((step, i) => (
              <li
                key={i}
                {...el(`items.${i}`, `Step ${i + 1}`)}
                className="flex flex-col gap-4"
              >
                <span
                  aria-hidden
                  className="flex h-10 w-10 items-center justify-center rounded-full border-4 border-muted bg-primary text-sm font-semibold text-primary-foreground"
                >
                  {i + 1}
                </span>
                <StepBody step={step} path={`items.${i}`} />
              </li>
            ))}
          </ol>
        </div>
      </div>
    </SectionShell>
  );
}

function ProcessCards({ heading, subhead, items }: ProcessSection) {
  return (
    <SectionShell type="process">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <ol className={`mt-14 grid gap-6 ${gridCols(items.length)}`}>
          {items.map((step, i) => (
            <li key={i} {...el(`items.${i}`, `Step ${i + 1}`)}>
              <Card tone="muted" className="flex h-full flex-col gap-4 p-7">
                <div className="flex items-center justify-between">
                  <Glyph icon={step.icon} path={`items.${i}.icon`} size={26} />
                  <span
                    aria-hidden
                    className="text-3xl font-semibold tabular-nums text-primary/25"
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <StepBody step={step} path={`items.${i}`} />
              </Card>
            </li>
          ))}
        </ol>
      </div>
    </SectionShell>
  );
}

function ProcessTwoColumnSteps({ heading, subhead, items }: ProcessSection) {
  return (
    <SectionShell type="process">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid gap-12 lg:grid-cols-[minmax(0,22rem)_1fr] lg:gap-20">
          <div className="flex flex-col gap-4 lg:sticky lg:top-16 lg:self-start">
            <Heading role="title" size="lg">
              {heading}
            </Heading>
            {subhead && <Lede role="description">{subhead}</Lede>}
          </div>
          <ol className="flex flex-col divide-y divide-border border-t border-border">
            {items.map((step, i) => (
              <li
                key={i}
                {...el(`items.${i}`, `Step ${i + 1}`)}
                className="flex gap-6 py-7"
              >
                <span
                  aria-hidden
                  className="text-xl font-semibold tabular-nums text-primary"
                >
                  {String(i + 1).padStart(2, "0")}
                </span>
                <StepBody step={step} path={`items.${i}`} />
              </li>
            ))}
          </ol>
        </div>
      </div>
    </SectionShell>
  );
}

function ProcessIconSteps({ heading, subhead, items }: ProcessSection) {
  return (
    <SectionShell type="process">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <ol className={`mt-14 grid gap-10 ${gridCols(items.length)}`}>
          {items.map((step, i) => (
            <li
              key={i}
              {...el(`items.${i}`, `Step ${i + 1}`)}
              className="flex flex-col gap-4"
            >
              <GlyphTile
                icon={step.icon}
                path={`items.${i}.icon`}
                shape="rounded"
              />
              <div className="flex flex-col gap-2">
                <span className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                  Step {i + 1}
                </span>
                <StepBody step={step} path={`items.${i}`} />
              </div>
            </li>
          ))}
        </ol>
      </div>
    </SectionShell>
  );
}

function ProcessCompactNumbers({ heading, subhead, items }: ProcessSection) {
  return (
    <SectionShell type="process" tone="tinted">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead
          heading={heading}
          subhead={subhead}
          align="left"
          size="md"
        />
        <ol className="mt-10 grid gap-8 sm:grid-cols-2">
          {items.map((step, i) => (
            <li
              key={i}
              {...el(`items.${i}`, `Step ${i + 1}`)}
              className="flex items-start gap-5"
            >
              <Numeral n={i + 1} tone="bare" />
              <StepBody step={step} path={`items.${i}`} />
            </li>
          ))}
        </ol>
      </div>
    </SectionShell>
  );
}

export const PROCESS_VARIANTS: Record<
  ProcessVariant,
  ComponentType<ProcessSection>
> = {
  "numbered-steps": ProcessNumberedSteps,
  "timeline-vertical": ProcessTimelineVertical,
  "timeline-horizontal": ProcessTimelineHorizontal,
  cards: ProcessCards,
  "two-column-steps": ProcessTwoColumnSteps,
  "icon-steps": ProcessIconSteps,
  "compact-numbers": ProcessCompactNumbers,
};

export const Process = ProcessNumberedSteps;
