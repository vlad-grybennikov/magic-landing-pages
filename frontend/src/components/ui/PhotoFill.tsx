import type { ReactNode } from "react";
import type { ImageRef } from "@/types/sections";
import { Image } from "./Image";
import { el } from "./marks";

export function PhotoFill({
  image,
  path,
  sizes = "100vw",
  children,
}: {
  image: ImageRef;
  path?: string;
  sizes?: string;
  children?: ReactNode;
}) {
  return (
    <div
      {...(path ? el(path, "Image") : {})}
      className="absolute inset-0 overflow-hidden bg-muted"
    >
      <Image
        src={image.src}
        alt={image.alt}
        sizes={sizes}
        className="object-cover"
      />
      {children}
    </div>
  );
}
