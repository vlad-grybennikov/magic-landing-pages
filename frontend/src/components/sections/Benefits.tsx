import type { ComponentType } from "react";
import type {
  BenefitItem,
  BenefitsSection,
  BenefitsVariant,
} from "@/types/sections";
import {
  at,
  Card,
  el,
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
  Tick,
} from "@/components/ui";
import { rich } from "@/lib/richtext";

function ItemText({
  item,
  path,
  align = "left",
}: {
  item: BenefitItem;
  path: string;
  align?: "left" | "center";
}) {
  return (
    <>
      <h3
        {...at(`${path}.title`, item.title)}
        className={`text-lg font-medium ${align === "center" ? "text-center" : ""}`}
      >
        {rich(item.title)}
      </h3>
      <p
        {...at(`${path}.caption`, item.caption)}
        className={`text-pretty leading-relaxed text-muted-foreground ${
          align === "center" ? "text-center" : ""
        }`}
      >
        {rich(item.caption)}
      </p>
    </>
  );
}

function BenefitsGridPlain({ heading, subhead, items }: BenefitsSection) {
  return (
    <SectionShell type="benefits">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className={`mt-14 grid gap-10 ${gridCols(items.length)}`}>
          {items.map((item, i) => (
            <div
              key={i}
              {...el(`items.${i}`, `Benefit ${i + 1}`)}
              className="flex flex-col items-center gap-3"
            >
              <GlyphTile
                icon={item.icon}
                path={`items.${i}.icon`}
                shape="rounded"
              />
              <ItemText item={item} path={`items.${i}`} align="center" />
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function BenefitsGridCards({ heading, subhead, items }: BenefitsSection) {
  return (
    <SectionShell type="benefits" tone="muted">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className={`mt-14 grid gap-6 ${gridCols(items.length)}`}>
          {items.map((item, i) => (
            <Card
              key={i}
              {...el(`items.${i}`, `Benefit ${i + 1}`)}
              className="flex flex-col gap-4 p-7"
            >
              <GlyphTile
                icon={item.icon}
                path={`items.${i}.icon`}
                shape="rounded"
              />
              <div className="flex flex-col gap-2">
                <ItemText item={item} path={`items.${i}`} />
              </div>
            </Card>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function BenefitsAlternatingRows({ heading, subhead, items }: BenefitsSection) {
  return (
    <SectionShell type="benefits">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <div className="mt-12 flex flex-col divide-y divide-border border-t border-border">
          {items.map((item, i) => (
            <div
              key={i}
              className="grid gap-4 py-8 sm:grid-cols-[auto_1fr] sm:gap-8"
            >
              <GlyphTile
                icon={item.icon}
                path={`items.${i}.icon`}
                shape="circle"
              />
              <div className="flex flex-col gap-2">
                <ItemText item={item} path={`items.${i}`} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function BenefitsNumbered({ heading, subhead, items }: BenefitsSection) {
  return (
    <SectionShell type="benefits">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className={`mt-14 grid gap-10 ${gridCols(items.length)}`}>
          {items.map((item, i) => (
            <div
              key={i}
              {...el(`items.${i}`, `Benefit ${i + 1}`)}
              className="flex flex-col gap-3"
            >
              <Numeral n={i + 1} tone="bare" />
              <div className="flex flex-col gap-2 border-t border-border pt-4">
                <ItemText item={item} path={`items.${i}`} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function BenefitsTwoColumnList({ heading, subhead, items }: BenefitsSection) {
  return (
    <SectionShell type="benefits">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid gap-12 lg:grid-cols-[minmax(0,22rem)_1fr] lg:gap-20">
          <div className="lg:sticky lg:top-16 lg:self-start">
            <SectionHead heading={heading} subhead={subhead} align="left" />
          </div>
          <div className="flex flex-col gap-10">
            {items.map((item, i) => (
              <div
                key={i}
                {...el(`items.${i}`, `Benefit ${i + 1}`)}
                className="flex gap-5"
              >
                <Glyph icon={item.icon} path={`items.${i}.icon`} size={28} />
                <div className="flex flex-col gap-2">
                  <ItemText item={item} path={`items.${i}`} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function BenefitsBorderedSplit({ heading, subhead, items }: BenefitsSection) {
  return (
    <SectionShell type="benefits">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <div
          className={`mt-12 grid divide-y divide-border overflow-hidden rounded-3xl border border-border sm:grid-cols-2 sm:divide-x lg:grid-cols-3 ${
            items.length > 3 ? "[&>*:nth-child(n+4)]:sm:border-t" : ""
          }`}
        >
          {items.map((item, i) => (
            <div
              key={i}
              {...el(`items.${i}`, `Benefit ${i + 1}`)}
              className="flex flex-col gap-3 p-8"
            >
              <Glyph icon={item.icon} path={`items.${i}.icon`} size={28} />
              <ItemText item={item} path={`items.${i}`} />
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function BenefitsIconInline({ heading, subhead, items }: BenefitsSection) {
  return (
    <SectionShell type="benefits" tone="tinted">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className={`mt-14 grid gap-8 ${gridCols(items.length)}`}>
          {items.map((item, i) => (
            <div
              key={i}
              {...el(`items.${i}`, `Benefit ${i + 1}`)}
              className="flex flex-col gap-3"
            >
              <div className="flex items-center gap-3">
                <Glyph icon={item.icon} path={`items.${i}.icon`} size={22} />
                <h3
                  {...at(`items.${i}.title`, item.title)}
                  className="text-lg font-medium"
                >
                  {rich(item.title)}
                </h3>
              </div>
              <p
                {...at(`items.${i}.caption`, item.caption)}
                className="text-pretty leading-relaxed text-muted-foreground"
              >
                {rich(item.caption)}
              </p>
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function BenefitsTintedCards({ heading, subhead, items }: BenefitsSection) {
  return (
    <SectionShell type="benefits">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div className={`mt-14 grid gap-6 ${gridCols(items.length)}`}>
          {items.map((item, i) => (
            <Card
              key={i}
              {...el(`items.${i}`, `Benefit ${i + 1}`)}
              tone="tinted"
              className="flex flex-col gap-4 p-7"
            >
              <GlyphTile
                icon={item.icon}
                path={`items.${i}.icon`}
                shape="circle"
                tone="solid"
              />
              <div className="flex flex-col gap-2">
                <ItemText item={item} path={`items.${i}`} />
              </div>
            </Card>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function BenefitsCompactList({ heading, subhead, items }: BenefitsSection) {
  return (
    <SectionShell type="benefits" tone="muted">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid gap-10 lg:grid-cols-[minmax(0,20rem)_1fr] lg:gap-16">
          <div className="flex flex-col gap-3">
            <Heading size="md" role="title">
              {heading}
            </Heading>
            {subhead && <Lede role="description">{subhead}</Lede>}
          </div>
          <ul className="grid gap-6 sm:grid-cols-2">
            {items.map((item, i) => (
              <li
                key={i}
                {...el(`items.${i}`, `Benefit ${i + 1}`)}
                className="flex gap-3"
              >
                <Tick />
                <div>
                  <h3
                    {...at(`items.${i}.title`, item.title)}
                    className="font-medium"
                  >
                    {rich(item.title)}
                  </h3>
                  <p
                    {...at(`items.${i}.caption`, item.caption)}
                    className="mt-1 text-sm leading-relaxed text-muted-foreground"
                  >
                    {rich(item.caption)}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </SectionShell>
  );
}

export const BENEFITS_VARIANTS: Record<
  BenefitsVariant,
  ComponentType<BenefitsSection>
> = {
  "grid-plain": BenefitsGridPlain,
  "grid-cards": BenefitsGridCards,
  "alternating-rows": BenefitsAlternatingRows,
  numbered: BenefitsNumbered,
  "two-column-list": BenefitsTwoColumnList,
  "bordered-split": BenefitsBorderedSplit,
  "icon-inline": BenefitsIconInline,
  "tinted-cards": BenefitsTintedCards,
  "compact-list": BenefitsCompactList,
};

export const Benefits = BenefitsGridPlain;
