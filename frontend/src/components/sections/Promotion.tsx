import type { ComponentType } from "react";
import type { PromotionSection, PromotionVariant } from "@/types/sections";
import { Button } from "@/components/ui";
import {
  CONTENT,
  Heading,
  Lede,
  PAD,
  PAD_TIGHT,
  SectionShell,
  TEXT,
} from "@/components/ui";

function PromotionCenteredBand({
  title,
  description,
  button,
}: PromotionSection) {
  return (
    <SectionShell type="promotion">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="flex flex-col items-center gap-5 rounded-3xl bg-muted px-6 py-16 text-center sm:px-12">
          <Heading role="title" size="lg" className="text-primary">
            {title}
          </Heading>
          <Lede role="description" className="max-w-2xl">
            {description}
          </Lede>
          <div className="mt-2">
            <Button button={button} variant="accent" />
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function PromotionTintedBand({ title, description, button }: PromotionSection) {
  return (
    <SectionShell type="promotion" tone="tinted">
      <div className={`${TEXT} ${PAD}`}>
        <div className="flex flex-col items-center gap-5 text-center">
          <Heading role="title" size="lg" className="text-primary">
            {title}
          </Heading>
          <Lede role="description" className="max-w-2xl">
            {description}
          </Lede>
          <div className="mt-2">
            <Button button={button} variant="accent" />
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function PromotionSplitRule({ title, description, button }: PromotionSection) {
  return (
    <SectionShell type="promotion">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid gap-8 border-y border-border py-12 lg:grid-cols-2 lg:gap-16">
          <Heading role="title" size="lg" className="text-primary">
            {title}
          </Heading>
          <div className="flex flex-col items-start gap-5">
            <Lede role="description">{description}</Lede>
            <Button button={button} variant="accent" />
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function PromotionBoxedAccent({
  title,
  description,
  button,
}: PromotionSection) {
  return (
    <SectionShell type="promotion">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="flex flex-col items-start gap-6 rounded-3xl bg-accent px-8 py-14 text-accent-foreground sm:px-14">
          <Heading role="title" size="lg">
            {title}
          </Heading>
          <p
            data-role="description"
            className="max-w-2xl text-pretty text-lg leading-relaxed opacity-90"
          >
            {description}
          </p>
          <Button button={button} variant="inverse" />
        </div>
      </div>
    </SectionShell>
  );
}

function PromotionInlineRow({ title, description, button }: PromotionSection) {
  return (
    <SectionShell type="promotion" tone="muted">
      <div className={`${CONTENT} ${PAD_TIGHT}`}>
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between sm:gap-10">
          <div className="flex flex-col gap-1.5">
            <Heading role="title" size="sm" className="text-primary">
              {title}
            </Heading>
            <p
              data-role="description"
              className="text-pretty text-muted-foreground"
            >
              {description}
            </p>
          </div>
          <div className="shrink-0">
            <Button button={button} variant="accent" />
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function PromotionTicket({ title, description, button }: PromotionSection) {
  return (
    <SectionShell type="promotion">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid overflow-hidden rounded-3xl border-2 border-dashed border-primary/40 bg-primary/5 sm:grid-cols-[1fr_auto]">
          <div className="flex flex-col gap-3 p-8 sm:p-12">
            <span className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
              Limited offer
            </span>
            <Heading role="title" size="md" className="text-primary">
              {title}
            </Heading>
            <Lede role="description" className="max-w-xl">
              {description}
            </Lede>
          </div>
          <div className="flex items-center justify-center border-t-2 border-dashed border-primary/40 p-8 sm:border-l-2 sm:border-t-0 sm:p-12">
            <Button button={button} variant="accent" />
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function PromotionFullBleedAccent({
  title,
  description,
  button,
}: PromotionSection) {
  return (
    <SectionShell type="promotion" className="bg-accent text-accent-foreground">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="flex flex-col items-center gap-5 text-center">
          <Heading role="title" size="lg">
            {title}
          </Heading>
          <p
            data-role="description"
            className="max-w-2xl text-pretty text-lg leading-relaxed opacity-90"
          >
            {description}
          </p>
          <div className="mt-2">
            <Button button={button} variant="inverse" />
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

export const PROMOTION_VARIANTS: Record<
  PromotionVariant,
  ComponentType<PromotionSection>
> = {
  "centered-band": PromotionCenteredBand,
  "tinted-band": PromotionTintedBand,
  "split-rule": PromotionSplitRule,
  "boxed-accent": PromotionBoxedAccent,
  "inline-row": PromotionInlineRow,
  ticket: PromotionTicket,
  "full-bleed-accent": PromotionFullBleedAccent,
};

export const Promotion = PromotionCenteredBand;
