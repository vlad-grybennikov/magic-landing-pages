import type { ComponentType } from "react";
import type { HeroSection, HeroVariant } from "@/types/sections";
import { Button } from "@/components/ui";
import {
  CONTENT,
  Heading,
  Lede,
  PAD,
  Photo,
  PhotoFill,
  Scrim,
  SectionShell,
  TEXT,
  WIDE,
} from "@/components/ui";

const FULL = "100vw";
const HALF = "(max-width: 1024px) 100vw, 50vw";

function HeroCopy({
  headline,
  subhead,
  button,
  align = "left",
  size = "xl",
  onDark = false,
}: Pick<HeroSection, "headline" | "subhead" | "button"> & {
  align?: "left" | "center";
  size?: "lg" | "xl";
  onDark?: boolean;
}) {
  const centered = align === "center";
  return (
    <div
      className={`flex flex-col gap-5 ${
        centered ? "items-center text-center" : "items-start text-left"
      }`}
    >
      <Heading
        level={1}
        size={size}
        role="title"
        className={onDark ? "text-white" : ""}
      >
        {headline}
      </Heading>
      {subhead && (
        <Lede
          role="description"
          className={`${centered ? "max-w-2xl" : "max-w-xl"} ${onDark ? "text-white/85" : ""}`}
        >
          {subhead}
        </Lede>
      )}
      <div className="mt-1">
        <Button button={button} variant="accent" />
      </div>
    </div>
  );
}

function HeroStacked({ headline, subhead, button, image }: HeroSection) {
  return (
    <SectionShell type="hero">
      <div className={`${CONTENT} ${PAD}`}>
        <HeroCopy headline={headline} subhead={subhead} button={button} />
        <Photo
          image={image}
          path="image"
          ratio="16/7"
          className="mt-12"
          sizes={FULL}
        />
      </div>
    </SectionShell>
  );
}

function HeroSplitLeft({ headline, subhead, button, image }: HeroSection) {
  return (
    <SectionShell type="hero">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
          <HeroCopy headline={headline} subhead={subhead} button={button} />
          <Photo
            image={image}
            path="image"
            ratio="4/3"
            rounded="3xl"
            sizes={HALF}
          />
        </div>
      </div>
    </SectionShell>
  );
}

function HeroSplitRight({ headline, subhead, button, image }: HeroSection) {
  return (
    <SectionShell type="hero">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
          <Photo
            image={image}
            path="image"
            ratio="4/3"
            rounded="3xl"
            className="lg:order-1"
            sizes={HALF}
          />
          <div className="lg:order-2">
            <HeroCopy headline={headline} subhead={subhead} button={button} />
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function HeroCentered({ headline, subhead, button, image }: HeroSection) {
  return (
    <SectionShell type="hero">
      <div className={`${PAD}`}>
        <div className={TEXT}>
          <HeroCopy
            headline={headline}
            subhead={subhead}
            button={button}
            align="center"
          />
        </div>
        <div className={`${WIDE} mt-14`}>
          <Photo
            image={image}
            path="image"
            ratio="21/9"
            rounded="3xl"
            sizes={FULL}
          />
        </div>
      </div>
    </SectionShell>
  );
}

function HeroFullBleed({ headline, subhead, button, image }: HeroSection) {
  return (
    <SectionShell type="hero" className="relative isolate">
      <PhotoFill image={image} path="image" sizes={FULL}>
        <Scrim strength="lg" />
      </PhotoFill>
      <div
        className={`${CONTENT} relative flex min-h-[32rem] items-end py-16 sm:py-24`}
      >
        <HeroCopy
          headline={headline}
          subhead={subhead}
          button={button}
          onDark
        />
      </div>
    </SectionShell>
  );
}

function HeroOverlayCard({ headline, subhead, button, image }: HeroSection) {
  return (
    <SectionShell type="hero">
      <Photo
        image={image}
        path="image"
        ratio="16/9"
        rounded="none"
        sizes={FULL}
        className="max-h-[30rem]"
      />
      <div className={`${CONTENT} pb-16 sm:pb-20`}>
        <div className="relative -mt-16 rounded-[calc(var(--sec-radius)*1.25)] border border-border bg-background p-8 shadow-sm sm:-mt-24 sm:p-12">
          <HeroCopy
            headline={headline}
            subhead={subhead}
            button={button}
            size="lg"
          />
        </div>
      </div>
    </SectionShell>
  );
}

function HeroMinimal({ headline, subhead, button }: HeroSection) {
  return (
    <SectionShell type="hero">
      <div className={`${CONTENT} py-20 sm:py-28 lg:py-32`}>
        <div className="max-w-3xl">
          <Heading level={1} size="xl" role="title">
            {headline}
          </Heading>
        </div>
        <div className="mt-10 flex flex-col gap-6 border-t border-border pt-8 sm:flex-row sm:items-end sm:justify-between">
          {subhead && (
            <Lede role="description" className="max-w-xl">
              {subhead}
            </Lede>
          )}
          <Button button={button} variant="accent" />
        </div>
      </div>
    </SectionShell>
  );
}

function HeroCollage({ headline, subhead, button, image }: HeroSection) {
  return (
    <SectionShell type="hero">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="relative grid gap-8 lg:grid-cols-12 lg:gap-6">
          <div className="rounded-3xl bg-primary/5 p-8 sm:p-12 lg:col-span-7 lg:py-20">
            <HeroCopy headline={headline} subhead={subhead} button={button} />
          </div>
          <div className="lg:col-span-5 lg:-ml-12 lg:mt-16">
            <Photo
              image={image}
              path="image"
              ratio="3/4"
              rounded="3xl"
              sizes={HALF}
              className="shadow-sm ring-1 ring-black/5"
            />
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function HeroBanner({ headline, subhead, button, image }: HeroSection) {
  return (
    <SectionShell type="hero" tone="muted">
      <div className="mx-auto grid w-full max-w-7xl items-stretch gap-10 lg:grid-cols-[1fr_minmax(0,45%)] lg:gap-0">
        <div className="flex items-center px-6 py-16 sm:py-20 lg:pl-[max(1.5rem,calc((100vw-72rem)/2))] lg:pr-16">
          <HeroCopy
            headline={headline}
            subhead={subhead}
            button={button}
            size="lg"
          />
        </div>
        <Photo
          image={image}
          path="image"
          ratio="4/3"
          rounded="none"
          sizes={HALF}
          className="h-full lg:rounded-l-3xl"
        />
      </div>
    </SectionShell>
  );
}

export const HERO_VARIANTS: Record<HeroVariant, ComponentType<HeroSection>> = {
  stacked: HeroStacked,
  "split-left": HeroSplitLeft,
  "split-right": HeroSplitRight,
  centered: HeroCentered,
  "full-bleed": HeroFullBleed,
  "overlay-card": HeroOverlayCard,
  minimal: HeroMinimal,
  collage: HeroCollage,
  banner: HeroBanner,
};

export const Hero = HeroStacked;
