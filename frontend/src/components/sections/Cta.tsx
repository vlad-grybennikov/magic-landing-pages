import type { ComponentType } from "react";
import type { CtaSection, CtaVariant } from "@/types/sections";
import { Button } from "@/components/ui";
import {
  CONTENT,
  Heading,
  Lede,
  PAD,
  PAD_TIGHT,
  PhotoFill,
  Scrim,
  SectionShell,
  TEXT,
} from "@/components/ui";

function Actions({
  button,
  secondary,
  onDark = false,
}: Pick<CtaSection, "button" | "secondary"> & { onDark?: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button button={button} variant={onDark ? "inverse" : "accent"} />
      {secondary && (
        <Button button={secondary} variant={onDark ? "ghost" : "secondary"} />
      )}
    </div>
  );
}

function CtaCentered({ headline, subhead, button, secondary }: CtaSection) {
  return (
    <SectionShell type="cta">
      <div className={`${TEXT} ${PAD}`}>
        <div className="flex flex-col items-center gap-5 text-center">
          <Heading role="title" size="lg">
            {headline}
          </Heading>
          {subhead && (
            <Lede role="description" className="max-w-2xl">
              {subhead}
            </Lede>
          )}
          <div className="mt-2">
            <Actions button={button} secondary={secondary} />
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function CtaBandAccent({ headline, subhead, button, secondary }: CtaSection) {
  return (
    <SectionShell type="cta" tone="accent">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="flex flex-col items-center gap-5 text-center">
          <Heading role="title" size="lg">
            {headline}
          </Heading>
          {subhead && (
            <p
              data-role="description"
              className="max-w-2xl text-pretty text-lg leading-relaxed opacity-85"
            >
              {subhead}
            </p>
          )}
          <div className="mt-2">
            <Actions button={button} secondary={secondary} onDark />
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function CtaSplit({ headline, subhead, button, secondary }: CtaSection) {
  return (
    <SectionShell type="cta" tone="muted">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between lg:gap-16">
          <div className="flex flex-col gap-3">
            <Heading role="title" size="lg">
              {headline}
            </Heading>
            {subhead && (
              <Lede role="description" className="max-w-xl">
                {subhead}
              </Lede>
            )}
          </div>
          <div className="shrink-0">
            <Actions button={button} secondary={secondary} />
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function CtaBoxedOutline({ headline, subhead, button, secondary }: CtaSection) {
  return (
    <SectionShell type="cta">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="flex flex-col items-start gap-5 rounded-3xl border-2 border-primary/20 p-8 sm:p-12">
          <Heading role="title" size="lg">
            {headline}
          </Heading>
          {subhead && (
            <Lede role="description" className="max-w-2xl">
              {subhead}
            </Lede>
          )}
          <Actions button={button} secondary={secondary} />
        </div>
      </div>
    </SectionShell>
  );
}

function CtaWithImage(section: CtaSection) {
  const { headline, subhead, button, secondary, image } = section;
  if (!image) return <CtaBandAccent {...section} />;

  return (
    <SectionShell type="cta" className="relative isolate">
      <PhotoFill image={image} path="image" sizes="100vw">
        <Scrim strength="lg" />
      </PhotoFill>
      <div
        className={`${CONTENT} relative flex min-h-[22rem] flex-col items-start justify-center gap-5 ${PAD}`}
      >
        <Heading role="title" size="lg" className="max-w-2xl text-white">
          {headline}
        </Heading>
        {subhead && (
          <p
            data-role="description"
            className="max-w-xl text-pretty text-lg leading-relaxed text-white/85"
          >
            {subhead}
          </p>
        )}
        <Actions button={button} secondary={secondary} onDark />
      </div>
    </SectionShell>
  );
}

function CtaMinimalRule({ headline, subhead, button, secondary }: CtaSection) {
  return (
    <SectionShell type="cta">
      <div className={`${CONTENT} ${PAD_TIGHT}`}>
        <div className="flex flex-col gap-6 border-t border-border pt-10 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex flex-col gap-2">
            <Heading role="title" size="md">
              {headline}
            </Heading>
            {subhead && (
              <Lede role="description" className="max-w-xl text-base">
                {subhead}
              </Lede>
            )}
          </div>
          <Actions button={button} secondary={secondary} />
        </div>
      </div>
    </SectionShell>
  );
}

export const CTA_VARIANTS: Record<CtaVariant, ComponentType<CtaSection>> = {
  centered: CtaCentered,
  "band-accent": CtaBandAccent,
  split: CtaSplit,
  "boxed-outline": CtaBoxedOutline,
  "with-image": CtaWithImage,
  "minimal-rule": CtaMinimalRule,
};

export const Cta = CtaCentered;
