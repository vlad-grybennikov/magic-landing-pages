import type { ImageRef } from "@/types/sections";

export function PhotoCredit({ image }: { image: ImageRef }) {
  if (!image.photographer) return null;
  return (
    <p className="mt-2 text-xs text-muted-foreground">
      Photo:{" "}
      {image.photographer_url ? (
        <a
          href={image.photographer_url}
          className="underline decoration-border hover:text-foreground"
        >
          {image.photographer}
        </a>
      ) : (
        image.photographer
      )}
    </p>
  );
}
