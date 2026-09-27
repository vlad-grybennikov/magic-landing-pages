import type { ComponentType } from "react";
import type { GallerySection, GalleryVariant } from "@/types/sections";
import {
  el,
  CONTENT,
  PAD,
  Photo,
  Rail,
  SectionHead,
  SectionShell,
  WIDE,
} from "@/components/ui";

const THIRD = "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw";
const QUARTER = "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw";
const HALF = "(max-width: 768px) 100vw, 50vw";

function GalleryGridThree({ heading, subhead, images }: GallerySection) {
  return (
    <SectionShell type="gallery">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div
          className={`grid gap-5 sm:grid-cols-2 lg:grid-cols-3 ${
            heading || subhead ? "mt-14" : ""
          }`}
        >
          {images.map((image, i) => (
            <Photo
              key={i}
              image={image}
              path={`images.${i}`}
              ratio="4/3"
              sizes={THIRD}
            />
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function GalleryGridFour({ heading, subhead, images }: GallerySection) {
  return (
    <SectionShell type="gallery">
      <div className={`${WIDE} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div
          className={`grid gap-4 sm:grid-cols-2 lg:grid-cols-4 ${
            heading || subhead ? "mt-14" : ""
          }`}
        >
          {images.map((image, i) => (
            <Photo
              key={i}
              image={image}
              path={`images.${i}`}
              ratio="1/1"
              rounded="xl"
              sizes={QUARTER}
            />
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function GalleryMasonry({ heading, subhead, images }: GallerySection) {
  return (
    <SectionShell type="gallery">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div
          className={`gap-5 sm:columns-2 lg:columns-3 ${
            heading || subhead ? "mt-14" : ""
          }`}
        >
          {images.map((image, i) => (
            <div
              key={i}
              {...el(`images.${i}`, `Photo ${i + 1}`)}
              className="mb-5 break-inside-avoid"
            >
              <Photo
                image={image}
                ratio={i % 3 === 0 ? "3/4" : i % 3 === 1 ? "1/1" : "4/3"}
                sizes={THIRD}
              />
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function GalleryMosaic({ heading, subhead, images }: GallerySection) {
  const [lead, ...rest] = images;
  return (
    <SectionShell type="gallery">
      <div className={`${WIDE} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div
          className={`grid gap-4 sm:grid-cols-2 lg:grid-cols-4 ${
            heading || subhead ? "mt-14" : ""
          }`}
        >
          <div className="sm:col-span-2 sm:row-span-2">
            <Photo
              image={lead}
              path="images.0"
              ratio="1/1"
              sizes={HALF}
              className="h-full"
            />
          </div>
          {rest.map((image, i) => (
            <Photo
              key={i}
              image={image}
              path={`images.${i}`}
              ratio="1/1"
              rounded="xl"
              sizes={QUARTER}
            />
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function GalleryFilmstrip({ heading, subhead, images }: GallerySection) {
  return (
    <SectionShell type="gallery" tone="muted">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} align="left" />
        <Rail className={heading || subhead ? "mt-12" : ""}>
          {images.map((image, i) => (
            <div
              key={i}
              {...el(`images.${i}`, `Photo ${i + 1}`)}
              className="w-[18rem] shrink-0 snap-start sm:w-[24rem]"
            >
              <Photo image={image} ratio="4/3" sizes="384px" />
            </div>
          ))}
        </Rail>
      </div>
    </SectionShell>
  );
}

function GalleryTwoUp({ heading, subhead, images }: GallerySection) {
  return (
    <SectionShell type="gallery">
      <div className={`${CONTENT} ${PAD}`}>
        <SectionHead heading={heading} subhead={subhead} />
        <div
          className={`grid gap-6 sm:grid-cols-2 ${
            heading || subhead ? "mt-14" : ""
          }`}
        >
          {images.map((image, i) => (
            <Photo
              key={i}
              image={image}
              path={`images.${i}`}
              ratio="3/2"
              rounded="3xl"
              sizes={HALF}
              className={i % 3 === 0 ? "sm:mt-0" : "sm:mt-8"}
            />
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

function GalleryFullBleed({ heading, subhead, images }: GallerySection) {
  return (
    <SectionShell type="gallery">
      {(heading || subhead) && (
        <div className={`${CONTENT} pt-16 sm:pt-20`}>
          <SectionHead heading={heading} subhead={subhead} />
        </div>
      )}
      <div className="mt-12 grid grid-cols-2 lg:grid-cols-4">
        {images.map((image, i) => (
          <Photo
            key={i}
            image={image}
            path={`images.${i}`}
            ratio="1/1"
            rounded="none"
            sizes={QUARTER}
          />
        ))}
      </div>
    </SectionShell>
  );
}

export const GALLERY_VARIANTS: Record<
  GalleryVariant,
  ComponentType<GallerySection>
> = {
  "grid-three": GalleryGridThree,
  "grid-four": GalleryGridFour,
  masonry: GalleryMasonry,
  mosaic: GalleryMosaic,
  filmstrip: GalleryFilmstrip,
  "two-up": GalleryTwoUp,
  "full-bleed": GalleryFullBleed,
};

export const Gallery = GalleryGridThree;
