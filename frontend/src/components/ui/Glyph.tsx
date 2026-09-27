import type { ImageRef } from "@/types/sections";
import { Image } from "./Image";
import { el } from "./marks";

export function Glyph({
  icon,
  path,
  size = 24,
  className = "text-primary",
}: {
  icon?: ImageRef;
  path?: string;
  size?: number;
  className?: string;
}) {
  if (!icon?.src) return null;
  const mark = path ? el(path, "Icon") : {};

  if (icon.src.toLowerCase().endsWith(".svg")) {
    return (
      <span
        {...mark}
        role="img"
        aria-label={icon.alt || undefined}
        aria-hidden={icon.alt ? undefined : true}
        className={`inline-block shrink-0 ${className}`}
        style={{ width: size, height: size }}
      >
        <span
          className="block h-full w-full bg-current"
          style={{
            maskImage: `url(${icon.src})`,
            WebkitMaskImage: `url(${icon.src})`,
            maskRepeat: "no-repeat",
            WebkitMaskRepeat: "no-repeat",
            maskPosition: "center",
            WebkitMaskPosition: "center",
            maskSize: "contain",
            WebkitMaskSize: "contain",
          }}
        />
      </span>
    );
  }

  return (
    <span
      {...mark}
      className="relative inline-block shrink-0 overflow-hidden rounded-md bg-muted"
      style={{ width: size, height: size }}
    >
      <Image
        src={icon.src}
        alt={icon.alt}
        sizes={`${size}px`}
        className="object-contain"
      />
    </span>
  );
}
