import type { ReactNode } from "react";
import type { ImageRef } from "@/types/sections";
import { Image } from "./Image";
import { el } from "./marks";

export function Photo({
  image,
  path,
  ratio = "4/3",
  rounded = "2xl",
  sizes = "(max-width: 768px) 100vw, 50vw",
  className = "",
  children,
}: {
  image: ImageRef;
  path?: string;
  ratio?: string;
  rounded?: "none" | "lg" | "xl" | "2xl" | "3xl" | "full";
  sizes?: string;
  className?: string;
  children?: ReactNode;
}) {
  const radius = {
    none: "",
    lg: "rounded-[calc(var(--sec-radius)*0.5)]",
    xl: "rounded-[calc(var(--sec-radius)*0.75)]",
    "2xl": "rounded-[var(--sec-radius)]",
    "3xl": "rounded-[calc(var(--sec-radius)*1.25)]",
    full: "rounded-full",
  }[rounded];

  return (
    <div
      {...(path ? el(path, "Image") : {})}
      style={{ aspectRatio: ratio, boxShadow: "var(--sec-shadow)" }}
      className={`relative w-full overflow-hidden bg-muted ring-1 ring-black/[0.06] ${radius} ${className}`}
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
