import NextImage from "next/image";

export function Image({
  src,
  alt,
  sizes,
  className,
}: {
  src: string;
  alt: string;
  sizes?: string;
  className?: string;
}) {
  return (
    <NextImage src={src} alt={alt} fill sizes={sizes} className={className} />
  );
}
