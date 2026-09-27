import type { ComponentType } from "react";
import type { StatItem, StatsSection, StatsVariant } from "@/types/sections";
import {
  at,
  el,
  Card,
  CONTENT,
  gridCols,
  Heading,
  Lede,
  PAD,
  PAD_TIGHT,
  SectionHead,
  SectionShell,
} from "@/components/ui";

function Stat({
  item,
  path,
  size = "lg",
  align = "center",
  tone = "primary",
}: {
  item: StatItem;
  path: string;
  size?: "md" | "lg" | "xl";
  align?: "left" | "center";
  tone?: "primary" | "inherit";
}) {
  const sizes = {
    md: "text-3xl sm:text-4xl",
    lg: "text-4xl sm:text-5xl",
    xl: "text-5xl sm:text-6xl",
  }[size];

  return (
    <div
      className={`flex flex-col gap-1.5 ${
        align === "center"
          ? "items-center text-center"
          : "items-start text-left"
      }`}
    >
      <span
        className={`font-semibold tabular-nums tracking-tight ${sizes} ${
          tone === "primary" ? "text-primary" : ""
        }`}
        {...at(`${path}.value`, item.value)}
      >
        {item.value}
      </span>
      <span {...at(`${path}.label`, item.label)} className="font-medium">
        {item.label}
      </span>
      {item.caption && (
        <span
          {...at(`${path}.caption`, item.caption)}
          className={`text-sm leading-relaxed ${
            tone === "primary" ? "text-muted-foreground" : "opacity-80"
          }`}
        >
          {item.caption}
        </span>
      )}
    </div>
  );
}

function StatsBandPlain({ heading, subhead, items }: StatsSection) {
  return (
    <SectionShell type="stats">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div
          className={`grid gap-10 ${heading || subhead ? "mt-14" : ""} ${gridCols(
            items.length,
          )}`}
        >
          {items.map((item, i) => (
            <Stat key={i} item={item} path={`items.${i}`} />
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function StatsBandTinted({ heading, subhead, items }: StatsSection) {
  return (
    <SectionShell type="stats" tone="accent">
      <div className={`${CONTENT} ${PAD}`}>
        {(heading || subhead) && (
          <div className="flex flex-col items-center gap-3 text-center">
            {heading && (
              <Heading role="title" size="lg">
                {heading}
              </Heading>
            )}
            {subhead && (
              <p
                data-role="description"
                className="max-w-2xl text-pretty text-lg opacity-85"
              >
                {subhead}
              </p>
            )}
          </div>
        )}
        <div
          className={`grid gap-10 ${heading || subhead ? "mt-14" : ""} ${gridCols(
            items.length,
          )}`}
        >
          {items.map((item, i) => (
            <Stat key={i} item={item} path={`items.${i}`} tone="inherit" />
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function StatsCards({ heading, subhead, items }: StatsSection) {
  return (
    <SectionShell type="stats" tone="muted">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div
          className={`grid gap-6 ${heading || subhead ? "mt-14" : ""} ${gridCols(
            items.length,
          )}`}
        >
          {items.map((item, i) => (
            <Card
              key={i}
              {...el(`items.${i}`, `Figure ${i + 1}`)}
              className="p-8"
            >
              <Stat item={item} path={`items.${i}`} align="left" size="md" />
            </Card>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function StatsDividedRow({ heading, subhead, items }: StatsSection) {
  return (
    <SectionShell type="stats">
      <div className={`${CONTENT} ${PAD_TIGHT}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div
          className={`grid divide-y divide-border border-y border-border sm:divide-x sm:divide-y-0 ${
            heading || subhead ? "mt-10" : ""
          } ${gridCols(items.length)}`}
        >
          {items.map((item, i) => (
            <div
              key={i}
              {...el(`items.${i}`, `Figure ${i + 1}`)}
              className="px-6 py-8 first:pl-0 last:pr-0"
            >
              <Stat item={item} path={`items.${i}`} size="md" />
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function StatsHeadingLeft({ heading, subhead, items }: StatsSection) {
  return (
    <SectionShell type="stats">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid gap-10 lg:grid-cols-[minmax(0,22rem)_1fr] lg:gap-20">
          <div className="flex flex-col gap-4">
            {heading && (
              <Heading role="title" size="lg">
                {heading}
              </Heading>
            )}
            {subhead && <Lede role="description">{subhead}</Lede>}
          </div>
          <div className="grid gap-10 sm:grid-cols-2">
            {items.map((item, i) => (
              <Stat
                key={i}
                item={item}
                path={`items.${i}`}
                align="left"
                size="md"
              />
            ))}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function StatsLargeNumerals({ heading, subhead, items }: StatsSection) {
  return (
    <SectionShell type="stats">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <div
          className={`flex flex-col divide-y divide-border border-y border-border ${
            heading || subhead ? "mt-12" : ""
          }`}
        >
          {items.map((item, i) => (
            <div
              key={i}
              {...el(`items.${i}`, `Figure ${i + 1}`)}
              className="grid items-baseline gap-2 py-8 sm:grid-cols-[minmax(0,14rem)_1fr] sm:gap-10"
            >
              <span
                {...at(`items.${i}.value`, item.value)}
                className="text-5xl font-semibold tabular-nums tracking-tight text-primary sm:text-6xl"
              >
                {item.value}
              </span>
              <div className="flex flex-col gap-1">
                <span
                  {...at(`items.${i}.label`, item.label)}
                  className="text-lg font-medium"
                >
                  {item.label}
                </span>
                {item.caption && (
                  <span
                    {...at(`items.${i}.caption`, item.caption)}
                    className="text-pretty leading-relaxed text-muted-foreground"
                  >
                    {item.caption}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

export const STATS_VARIANTS: Record<
  StatsVariant,
  ComponentType<StatsSection>
> = {
  "band-plain": StatsBandPlain,
  "band-tinted": StatsBandTinted,
  cards: StatsCards,
  "divided-row": StatsDividedRow,
  "heading-left": StatsHeadingLeft,
  "large-numerals": StatsLargeNumerals,
};

export const Stats = StatsBandPlain;
