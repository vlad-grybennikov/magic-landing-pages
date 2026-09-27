import type { ComponentType } from "react";
import type { AboutSection, AboutVariant } from "@/types/sections";
import { Button } from "@/components/ui";
import {
  at,
  el,
  CONTENT,
  Eyebrow,
  Heading,
  PAD,
  Photo,
  PhotoCredit,
  SectionShell,
  TEXT,
  WIDE,
} from "@/components/ui";
import { rich } from "@/lib/richtext";

const HALF = "(max-width: 1024px) 100vw, 50vw";
const FULL = "100vw";

function Prose({
  body,
  lead = false,
  from = 0,
  className = "",
}: {
  body: string[];
  lead?: boolean;
  from?: number;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      {body.map((paragraph, offset) => {
        const i = from + offset;
        return (
          <p
            key={i}
            {...at(`body.${i}`, paragraph)}
            {...el(`body.${i}`, `Paragraph ${i + 1}`)}
            className={`text-pretty leading-relaxed ${
              lead && offset === 0
                ? "text-xl text-foreground"
                : "text-muted-foreground"
            }`}
          >
            {rich(paragraph)}
          </p>
        );
      })}
    </div>
  );
}

function AboutImageLeft({
  heading,
  eyebrow,
  body,
  image,
  button,
}: AboutSection) {
  return (
    <SectionShell type="about">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
          <div>
            <Photo
              image={image}
              path="image"
              ratio="4/3"
              rounded="3xl"
              sizes={HALF}
            />
            <PhotoCredit image={image} />
          </div>
          <div className="flex flex-col items-start gap-5">
            {eyebrow && <Eyebrow role="eyebrow">{eyebrow}</Eyebrow>}
            <Heading role="title" size="lg">
              {heading}
            </Heading>
            <Prose body={body} />
            {button && <Button button={button} variant="secondary" />}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function AboutImageRight({
  heading,
  eyebrow,
  body,
  image,
  button,
}: AboutSection) {
  return (
    <SectionShell type="about">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid items-center gap-10 lg:grid-cols-2 lg:gap-16">
          <div className="flex flex-col items-start gap-5">
            {eyebrow && <Eyebrow role="eyebrow">{eyebrow}</Eyebrow>}
            <Heading role="title" size="lg">
              {heading}
            </Heading>
            <Prose body={body} />
            {button && <Button button={button} variant="secondary" />}
          </div>
          <div>
            <Photo
              image={image}
              path="image"
              ratio="4/3"
              rounded="3xl"
              sizes={HALF}
            />
            <PhotoCredit image={image} />
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function AboutImageOffset({
  heading,
  eyebrow,
  body,
  image,
  button,
}: AboutSection) {
  return (
    <SectionShell type="about">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid gap-8 lg:grid-cols-12 lg:items-center lg:gap-0">
          <div className="lg:col-span-5 lg:z-10">
            <Photo
              image={image}
              path="image"
              ratio="3/4"
              rounded="3xl"
              sizes={HALF}
              className="shadow-sm ring-1 ring-black/5"
            />
          </div>
          <div className="relative flex flex-col items-start gap-5 rounded-[calc(var(--sec-radius)*1.25)] bg-muted p-8 sm:p-12 lg:col-span-7 lg:-ml-16 lg:py-20 lg:pl-28">
            {eyebrow && <Eyebrow role="eyebrow">{eyebrow}</Eyebrow>}
            <Heading role="title" size="lg">
              {heading}
            </Heading>
            <Prose body={body} />
            {button && <Button button={button} variant="secondary" />}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function AboutTextCentered({
  heading,
  eyebrow,
  body,
  image,
  button,
}: AboutSection) {
  return (
    <SectionShell type="about" tone="muted">
      <div className={`${TEXT} ${PAD}`}>
        <div className="flex flex-col items-center gap-6 text-center">
          <div className="w-28">
            <Photo
              image={image}
              path="image"
              ratio="1/1"
              rounded="full"
              sizes="112px"
            />
          </div>
          {eyebrow && <Eyebrow role="eyebrow">{eyebrow}</Eyebrow>}
          <Heading role="title" size="lg">
            {heading}
          </Heading>
          <Prose body={body} className="text-center" />
          {button && <Button button={button} variant="secondary" />}
        </div>
      </div>
    </SectionShell>
  );
}

function AboutTwoColumnText({
  heading,
  eyebrow,
  body,
  image,
  button,
}: AboutSection) {
  return (
    <SectionShell type="about">
      <div className={`${CONTENT} ${PAD}`}>
        <div className="grid gap-10 lg:grid-cols-[minmax(0,24rem)_1fr] lg:gap-20">
          <div className="flex flex-col gap-4">
            {eyebrow && <Eyebrow role="eyebrow">{eyebrow}</Eyebrow>}
            <Heading role="title" size="lg">
              {heading}
            </Heading>
            {button && (
              <div className="mt-2">
                <Button button={button} variant="secondary" />
              </div>
            )}
          </div>
          <Prose body={body} lead />
        </div>
        <div className="mt-14">
          <Photo
            image={image}
            path="image"
            ratio="21/9"
            rounded="3xl"
            sizes={FULL}
          />
          <PhotoCredit image={image} />
        </div>
      </div>
    </SectionShell>
  );
}

function AboutLeadParagraph({
  heading,
  eyebrow,
  body,
  image,
  button,
}: AboutSection) {
  const [lead, ...rest] = body;
  return (
    <SectionShell type="about">
      <div className={`${CONTENT} ${PAD}`}>
        {eyebrow && (
          <Eyebrow role="eyebrow" className="mb-3">
            {eyebrow}
          </Eyebrow>
        )}
        <Heading role="title" size="lg" className="max-w-3xl">
          {heading}
        </Heading>
        <p
          {...at("body.0", lead)}
          {...el("body.0", "Paragraph 1")}
          className="mt-6 max-w-3xl text-pretty text-xl leading-relaxed text-muted-foreground"
        >
          {rich(lead)}
        </p>
        <div className="mt-12 grid items-start gap-10 lg:grid-cols-2 lg:gap-16">
          <div>
            <Photo
              image={image}
              path="image"
              ratio="16/10"
              rounded="2xl"
              sizes={HALF}
            />
            <PhotoCredit image={image} />
          </div>
          <div className="flex flex-col items-start gap-5">
            {rest.length > 0 && <Prose body={rest} from={1} />}
            {button && <Button button={button} variant="secondary" />}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function AboutPhotoBand({
  heading,
  eyebrow,
  body,
  image,
  button,
}: AboutSection) {
  return (
    <SectionShell type="about">
      <Photo
        image={image}
        path="image"
        ratio="21/9"
        rounded="none"
        sizes={FULL}
        className="max-h-[26rem]"
      />
      <div className={`${WIDE} ${PAD}`}>
        <div className="grid gap-8 lg:grid-cols-[minmax(0,26rem)_1fr] lg:gap-20">
          <div className="flex flex-col gap-3">
            {eyebrow && <Eyebrow role="eyebrow">{eyebrow}</Eyebrow>}
            <Heading role="title" size="lg">
              {heading}
            </Heading>
          </div>
          <div className="flex flex-col items-start gap-5">
            <Prose body={body} />
            {button && <Button button={button} variant="secondary" />}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

export const ABOUT_VARIANTS: Record<
  AboutVariant,
  ComponentType<AboutSection>
> = {
  "image-left": AboutImageLeft,
  "image-right": AboutImageRight,
  "image-offset": AboutImageOffset,
  "text-centered": AboutTextCentered,
  "two-column-text": AboutTwoColumnText,
  "lead-paragraph": AboutLeadParagraph,
  "photo-band": AboutPhotoBand,
};

export const About = AboutImageRight;
